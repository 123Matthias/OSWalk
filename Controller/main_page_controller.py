import os
import threading
import random
import time
from tkinter import filedialog
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count, Manager
import math

from Service.explorer_service import ExplorerService
from Service.reader_service import ReaderService

#####################################################################################################################
# Statische Hilfsfunktionen für Multiprocessing in Python                                                           #
# Threads haben GIL (Global Interpreter Lock, darum sind CPU lastige Aufgaben mit Threads nicht parallel            #
# Threads sind nur bei I/O lastigen Dingen echte Beschleunigung da sie an der gleichen Interpreter Instanz laufen   #
# Multiprocessing erstellt eigene Interpreter Instance für jeden Process                                            #
#####################################################################################################################
def process_chunk_static(dateien_chunk, keywords, threads_per_process, chunk_id, basis_pfad, progress_queue):
    """OPTIMIERT: Mit besseren Werten für Threads"""
    try:
        from Service.reader_service import ReaderService
        reader = ReaderService()
        keyword_list = [k.strip().lower() for k in keywords.replace(',', ' ').split()]
        treffer = []
        chunk_size = len(dateien_chunk)

        # Thread Executor
        with ThreadPoolExecutor(max_workers=threads_per_process) as executor:
            futures = {} # dictionary
            for dateipfad in dateien_chunk:
                future = executor.submit(
                    process_single_file_static,
                    dateipfad,
                    keyword_list,
                    reader,
                    basis_pfad
                )
                futures[future] = dateipfad

            verarbeitet_im_chunk = 0
            for future in as_completed(futures):
                result = future.result()
                if result:
                    treffer.append(result)

                verarbeitet_im_chunk += 1
                # 🔥 Progress nur alle 5 Dateien (reduziert Queue-Last)
                if verarbeitet_im_chunk % 5 == 0 or verarbeitet_im_chunk == chunk_size:
                    progress_queue.put(('progress', chunk_id, verarbeitet_im_chunk, chunk_size))

        return treffer

    except Exception as e:
        print(f"❌ KRITISCHER FEHLER in Prozess {chunk_id}: {e}")
        return []


def process_single_file_static(dateipfad, keyword_list, reader, basis_pfad):
    """Schnellere Textsuche"""
    try:
        # 🔥 max_chars erhöht für bessere Trefferquote
        text = reader.extract_text(dateipfad, max_chars=5000)
        if not text:
            return None

        # 🔥 Einmal lower() für alle Keywords
        text_lower = text.lower()

        # 🔥 Keyword-Check in einem Durchgang
        for keyword in keyword_list:
            if keyword in text_lower:
                # Nur Kontext erstellen wenn nötig
                kontext = make_body_text_static(text, keyword, ctx=150)
                dateiname = os.path.basename(dateipfad)
                rel_pfad = os.path.relpath(dateipfad, basis_pfad)
                return ("content", dateiname, rel_pfad, keyword, kontext)

    except Exception as e:
        print(f"❌ FEHLER in main_page_controller in Method process_single_file_static {e}")
    return None


def make_body_text_static(text, keyword, ctx=100):
    """Keine Instance Methoden für Multiprocessing in Python (Ansonsten Pickling fehler) """
    if not text or not keyword:
        return None

    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return None

    start = max(0, idx - ctx)
    end = min(len(text), idx + len(keyword) + ctx)

    kontext = text[start:end].replace("\n", " ").replace("\r", " ")
    kontext = ' '.join(kontext.split())
    return kontext

######################################   CLASS   ###########################################################################################
class MainPageController:
    def __init__(self):
        self.view = None
        self.reader_service = ReaderService()
        self.explorer_service = ExplorerService()
        self.cancel_thread_event = threading.Event()
        self.search_thread = None
        self.search_recursive = True

        self.all_files_cache = []

        # Queue für UI-Updates
        # Problem ist tkinter Gui Updates dürfen nicht aus Thread stammen (zumindest am Mac kommt sonst Fork fehler)
        # Weiters ist das Beenden des threads mit threading.Event() also cancel_thread_event.set() nicht möglich
        # tkinter immer am gui thread mit alles elementen separat behandeln!!!
        self.ui_update_queue = deque()

        # Multiprocessing berechnen der Process Counts
        cpu_cores = cpu_count()
        self.num_processes = max(1, cpu_cores - 2)  # Min 1 Kern für UI frei lassen
        self.threads_per_process = 4  # Mehr Threads für I/O TODO User könnte das selbst steuern
        print(f"Performance: {self.num_processes} Prozesse mit je {self.threads_per_process} Threads")

    def _collect_files(self):
        """Hilfsmethode zum Sammeln der Dateien aus explorer_service.collect_file_info"""
        all_files, total = self.explorer_service.collect_file_info(
            self.view.basis_pfad,
            self.search_recursive,
            self.cancel_thread_event
        )
        return all_files

    def set_view(self, view):
        self.view = view
        self.view.root.after(50, self._schedule_ui_updates) # alle 50ms UI Update


################################ GUI Thread Scheduler ########################################################################
    # alle 50ms UI Update
    # aus der Methode process_ui_queue kommen max 200 updates bis Pause das entlastet den UI Thread
    def _schedule_ui_updates(self):
        """Time Based and max update Value Scheduling for GUI Thread"""
        if not self.view or not hasattr(self.view, 'root'):
            return
        try:
            self._process_ui_queue()
            self.view.root.after(50, self._schedule_ui_updates)
        except Exception as e:
            print(f"Fehler im Scheduler Method _schedule_ui_updates in controller: {e}")

    def _process_ui_queue(self):
        processed = 0
        while self.ui_update_queue and processed < 200:
            update_func = self.ui_update_queue.popleft()
            try:
                update_func()
                processed += 1
            except Exception as e:
                print(f"Fehler bei UI-Update: {e}")
                import traceback
                traceback.print_exc()
#########################################################################################################

    def _queue_ui_update(self, update_func):
        self.ui_update_queue.append(update_func)

    def choose_path(self):
        pfad = filedialog.askdirectory(initialdir=os.path.expanduser("~/home"))
        if pfad:
            self.view.pfad_label.configure(text=pfad)
            self.view.basis_pfad = pfad
            self.all_files_cache = []


    def search(self, event=None):
        keywords = self.view.keywords.get()

        if not hasattr(self.view, "basis_pfad") or not self.view.basis_pfad:
            print("kein Pfad ausgewählt")
            return
        if not keywords:
            print("gib einen Suchberiff ein ein")
            return

        if self.search_thread and self.search_thread.is_alive():
            print("Vorherige Suche läuft noch!")
            print("wird abgebrochen...")
            self.cancel_thread_event.set() # beendet den thread hier nicht stellt nur Ampel auf Stop
            self.search_thread.join(timeout=1)

        # Flag zum stoppen des search threads der alle anderen Prozesse und threads startet.
        self.cancel_thread_event = threading.Event()

        self._queue_ui_update(lambda: self.view.clear_results()) # results löschen
        self._queue_ui_update(lambda: self.view.progress_state.set(0)) # reset progress bar

        # Hier wird der code im target dem Thread übergeben Runnable oder Future Code genannt
        self.search_thread = threading.Thread(
            target=self._run_search_thread_multiprocessing,
            args=(keywords, self.cancel_thread_event),
            name="search_thread" + time.strftime("%Y%m%d-%H%M%S"),
            daemon=True
        )
        self.search_thread.start() # Startet den Thread erst
        print(f"🔍 Suche nach '{keywords}' gestartet...")

    def _run_search_thread_multiprocessing(self, keywords, cancel_thread_event):
        """
            Hauptsuchroutine - läuft im Thread, startet Multiprocessing-Pool
            Sammelt Dateien, filtert Namen, verteilt Content-Suche auf Prozesse
        """
        try:
            # Dateien sammeln (mit Cache)
            if not self.all_files_cache:
                all_files = self._collect_files()
                self.all_files_cache = all_files
            else:
                all_files = self.all_files_cache

            if not all_files:
                print("Keine Dateien gefunden")
                return

            total_files = len(all_files)
            print(f"Search Thread: {total_files} Dateien werden auf {self.num_processes} CPU Kernen bearbeitet...")

            # Dateinamen-Filter (superschnell)
            treffer_set = set(self.explorer_service.filter_files_by_name(all_files, keywords)) # Set zerstört Dublikate hier sollten aber onehin keine sein
            namen_treffer = len(treffer_set)

            # Dateinamen-Treffer sofort anzeigen
            for dateipfad in treffer_set:
                if cancel_thread_event.is_set(): # Wenn Stop kommt, dann soll Thread nicht weiter arbeiten
                    print("Breche ab " + threading.current_thread().name + "in for Schleife for dateipfad in treffer_set ...")
                    return
                dateiname = os.path.basename(dateipfad)
                rel_pfad = os.path.relpath(dateipfad, self.view.basis_pfad)
                self._queue_ui_update(
                    lambda d=dateiname, r=rel_pfad:
                    self._display_results([("filename", d, r, None, None)]) # Queue wird mit lamda func gefüllt das kann man auch direkt reinschreiben
                )

            # Dateien für Content-Suche
            zu_pruefen = [f for f in all_files if f not in treffer_set]

            if not zu_pruefen:
                self._queue_ui_update(lambda: self._update_progress(100)) # Fertig wenns nix gibt was noch zu prüfen ist also inhalt
                return

            # Zufällig mischen für Lastverteilung für bessere Aufteilung der Datenmengen auf Processes
            random.shuffle(zu_pruefen)

            # Chunk-Größe bestimmen. Ein Chunk ist die Menge an Files, die zu einem Prozess zugeordnet wird
            chunk_size = math.ceil(len(zu_pruefen) / self.num_processes)

            # 1. i = 0:  meine_liste[0 : 0+3] = meine_liste[0:3] → [0, 1, 2]
            # 2. i = 3:  meine_liste[3 : 3+3] = meine_liste[3:6] → [3, 4, 5]
            # 3. i = 6:  meine_liste[6 : 6+3] = meine_liste[6:9] → [6, 7, 8]
            chunks = [zu_pruefen[i:i + chunk_size] for i in range(0, len(zu_pruefen), chunk_size)]

            # Shared Queue mit Manager prozessübergreifender Zugriff möglich
            manager = Manager()
            progress_queue = manager.Queue()
            chunk_status = [0] * len(chunks)

            # CPU lastige Dinge kommen in den Pool multiprocessing process_chunk_static methode außerhalb der Klasse wegen pickling wird aufgerufen
            with Pool(processes=self.num_processes) as pool:
                results = []
                for i, chunk in enumerate(chunks):
                    result = pool.apply_async(
                        process_chunk_static,
                        (chunk, keywords, self.threads_per_process, i, self.view.basis_pfad, progress_queue)
                    )
                    results.append(result)

                # Progress-Tracking
                inhalt_treffer = 0
                letzter_progress = -1

                # Schnellere Queue-Verarbeitung
                while any(not r.ready() for r in results):
                    if cancel_thread_event.is_set():
                        print("❌ ABBRUCH - Alle Prozesse werden beendet!")
                        pool.terminate()
                        pool.join()
                        return

                    try:
                        # Manager queue sehen alle darum Manager = Prozess übergreifende resource Werte kommen aus der static methode ganz oben
                        msg = progress_queue.get(timeout=0.05)
                        if msg[0] == 'progress':
                            _, chunk_id, chunk_verarbeitet, _ = msg
                            chunk_status[chunk_id] = chunk_verarbeitet

                            total_verarbeitet = namen_treffer + sum(chunk_status)
                            progress = int(total_verarbeitet / total_files * 100)

                            if progress != letzter_progress:
                                self._queue_ui_update(lambda p=progress: self._update_progress(p))
                                letzter_progress = progress

                    except:
                       pass

                # Ergebnisse einsammeln
                for result in results:
                    chunk_treffer = result.get()
                    for treffer in chunk_treffer:
                        typ, dateiname, rel_pfad, keyword, kontext = treffer
                        self._queue_ui_update(
                            lambda d=dateiname, r=rel_pfad, k=keyword, ctx=kontext:
                            self._display_results([(typ, d, r, k, ctx)])
                        )
                        inhalt_treffer += 1

                self._queue_ui_update(lambda: self._update_progress(100))
                print(f"✅ FERTIG: {namen_treffer} Dateinamen, {inhalt_treffer} Inhalts-Treffer")

        except Exception as e:
            print(f"❌ Fehler: {e}")
            import traceback
            traceback.print_exc()





    # Restliche Methoden für result update etc.
    def _display_results(self, results):
        if not self.view:
            return
        for typ, dateiname, rel_pfad, keyword, kontext in results:
            if typ == "filename":
                self.view.add_result(dateiname, f"Fundort: {rel_pfad}", "filename")
            else:
                text = f"'{keyword}' in {rel_pfad}\n...{kontext}..." if kontext else f"Treffer in {rel_pfad}"
                self.view.add_result(dateiname, text, "content")

    def _update_progress(self, value):
        if self.view:
            try:
                self.view.progress_state.set(value)
                self.view.root.update_idletasks()
            except:
                pass

    def cancel_search(self):
        self.cancel_thread_event.set()
        print("Suche wird abgebrochen...")

    def reset_progress_bar(self):
        if self.view:
            self._queue_ui_update(lambda: self.view.progress_state.set(0))

    def clear_cache(self):
        self.all_files_cache = []