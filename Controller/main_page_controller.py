import os
import threading
import random
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count, Manager
import math

from PySide6.QtCore import QObject, Signal, QTimer  # Qt Signals für Thread-Sicherheit
from PySide6.QtWidgets import QFileDialog  # Qt FileDialog

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
            futures = {}  # dictionary
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
                    progress_queue.put(('treffer', result))

                verarbeitet_im_chunk += 1
                # Progress nur alle 5 Dateien (reduziert Queue-Last)
                if verarbeitet_im_chunk % 5 == 0 or verarbeitet_im_chunk == chunk_size:
                    progress_queue.put(('progress', chunk_id, verarbeitet_im_chunk, chunk_size))

        return []

    except Exception as e:
        print(f"❌ KRITISCHER FEHLER in Prozess {chunk_id}: {e}")
        return []


def process_single_file_static(dateipfad, keyword_list, reader, basis_pfad):
    """Schnellere Textsuche"""
    try:
        # 🔥 max_chars erhöht für bessere Trefferquote
        text = reader.extract_text(dateipfad, max_chars=700)
        if not text:
            return None

        # 🔥 Einmal lower() für alle Keywords
        text_lower = text.lower()
        found = False
        priority = 0
        dateiname = None
        kontext = None
        is_text_generated = False
        # 🔥 Keyword-Check in einem Durchgang
        for i, keyword in enumerate(keyword_list, start=1):
            if keyword in text_lower:
                found = True
                priority += i
                if not is_text_generated: # Kontext wird aus erstem treffer erzeugt.
                    kontext = make_body_text_static(text, keyword, ctx=200)
                    dateiname = os.path.basename(dateipfad)
                    is_text_generated = True
        if found:
            return priority, "content", dateiname, dateipfad, kontext

    except Exception as e:
        print(f"❌ FEHLER in main_page_controller in Method process_single_file_static {e}")
    return None


def make_body_text_static(text, keyword, ctx=300):
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
class MainPageController(QObject):  # QObject für Signal-Support
    # Signale für Thread-sichere UI-Updates - DIREKT und SOFORT!
    add_result_signal = Signal(int, str, str, str, str)  # priority, title, body, treffer_typ, abs_path
    clear_results_signal = Signal()
    update_progress_signal = Signal(int)
    update_path_signal = Signal(str)
    show_status_signal = Signal(str, str)  # message, typ
    search_finished_signal = Signal(bool)

    def __init__(self):
        super().__init__()  # QObject Init aufrufen
        self.view = None
        self.reader_service = ReaderService()
        self.explorer_service = ExplorerService()
        self.cancel_thread_event = threading.Event()
        self.search_thread = None
        self.search_recursive = True
        self.all_files_cache = []

        # KEINE Queue mehr nötig! PySide6 Signals sind thread-sicher
        # self.ui_update_queue = deque()  # 👈 WEG DAMIT!

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
        # Verbinde die Signale mit den View-Methoden
        self.add_result_signal.connect(view.add_result)
        self.clear_results_signal.connect(view.clear_results)
        self.update_progress_signal.connect(view.set_progress)
        self.update_path_signal.connect(view.update_path_label)
        self.show_status_signal.connect(view.show_status)
        self.search_finished_signal.connect(view.sort_results)
        self.search_finished_signal.connect(view.refresh_results_display)

        # KEIN Timer mehr nötig! Signals werden sofort im Haupt-Thread verarbeitet

    def choose_path(self):
        """Qt FileDialog für PySide"""
        pfad = QFileDialog.getExistingDirectory(
            self.view,  # parent widget
            "Verzeichnis auswählen",
            os.path.expanduser("~")
        )

        if pfad:
            # DIREKTES Signal - sofortige Aktualisierung
            self.update_path_signal.emit(pfad)
            self.view.basis_pfad = pfad
            self.all_files_cache = []

    def search(self, event=None):
        keywords = self.view.keywords_input.text()  # .text() statt .get() für Qt

        if not hasattr(self.view, "basis_pfad") or not self.view.basis_pfad:
            print("kein Pfad ausgewählt")
            return
        if not keywords:
            print("gib einen Suchberiff ein")
            return

        if self.search_thread and self.search_thread.is_alive():
            print("Vorherige Suche läuft noch!")
            print("wird abgebrochen...")
            self.cancel_thread_event.set()  # beendet den thread hier nicht stellt nur Ampel auf Stop
            self.search_thread.join(timeout=1)

        # Flag zum stoppen des search threads der alle anderen Prozesse und threads startet.
        self.cancel_thread_event = threading.Event()

        # DIREKTE Signale - sofortige Aktualisierung
        self.clear_results_signal.emit()  # results löschen
        self.update_progress_signal.emit(0)  # reset progress bar

        # Hier wird der code im target dem Thread übergeben Runnable oder Future Code genannt
        self.search_thread = threading.Thread(
            target=self._run_search_thread_multiprocessing,
            args=(keywords, self.cancel_thread_event),
            name="search_thread" + time.strftime("%Y%m%d-%H%M%S"),
            daemon=True
        )
        self.search_thread.start()  # Startet den Thread erst
        print(f"🔍 Suche nach '{keywords}' gestartet...")

    def _run_search_thread_multiprocessing(self, keywords, cancel_thread_event):
        """
            Hauptsuchroutine - läuft im Thread, startet Multiprocessing-Pool
            Sammelt Dateien, filtert Namen, verteilt Content-Suche auf Prozesse
        """
        try:
            # Dateien sammeln (mit Cache)
            if not self.all_files_cache:
                print("sammle pfade")
                all_files = self._collect_files()
                self.all_files_cache = all_files
                print("Pfade sammeln erledigt")
            else:
                all_files = self.all_files_cache
                print("verwende cache auch letzter Suche für Path")

            if not all_files:
                print("Keine Dateien gefunden")
                return

            total_files = len(all_files)
            print(f"Search Thread: {total_files} Dateien werden auf {self.num_processes} CPU Kernen bearbeitet...")

            # Dateinamen-Filter (superschnell)
            treffer_set = set(self.explorer_service.filter_files_by_name(all_files, keywords))  # Set zerstört Dublikate hier sollten aber onehin keine sein
            namen_treffer = len(treffer_set)

            # Dateinamen-Treffer SOFORT anzeigen - DIREKTES Signal!
            for treffer in treffer_set:
                if cancel_thread_event.is_set():  # Wenn Stop kommt, dann soll Thread nicht weiter arbeiten
                    print(
                        "abbrechen " + threading.current_thread().name + "in for Schleife for dateipfad in treffer_set ...")
                    return
                abs_pfad = os.path.abspath(treffer[1])
                dateiname = os.path.basename(treffer[1])
                rel_pfad = os.path.relpath(abs_pfad, self.view.basis_pfad)
                # DIREKTES Signal - sofortige Anzeige!
                self.add_result_signal.emit(treffer[0], dateiname, f"Fundort: {rel_pfad}", "filename", abs_pfad)

            # Dateien für Content-Suche
            zu_pruefen = [f for f in all_files if f not in treffer_set]

            if not zu_pruefen:
                self.update_progress_signal.emit(100)  # Fertig wenns nix gibt was noch zu prüfen ist also inhalt
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

                # Schnellere Queue-Verarbeitung Result ist eine async ops deshalb müssen wir auf ready warten
                while any(not r.ready() for r in results) or not progress_queue.empty():
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
                                # DIREKTES Signal - sofortige Progress-Anzeige!
                                self.update_progress_signal.emit(progress)
                                letzter_progress = progress

                        elif msg[0] == 'treffer':
                            # 🔥 TREFFER-UPDATE: Hier werden Treffer aus der Queue geholt!
                            treffer = msg[1]  # Auspacken des Tuples: ('treffer', result)
                            priority, typ, dateiname, abs_pfad, kontext = treffer

                            # Formatiere und sende an GUI!
                            text = f"'...{kontext}..."
                            self.add_result_signal.emit(priority, dateiname, text, "content", abs_pfad)  # ✨ AN DIE GUI!

                    except:
                        pass


                self.update_progress_signal.emit(100)
                print(f"✅ FERTIG: {namen_treffer} Dateinamen, {inhalt_treffer} Inhalts-Treffer")
                self.search_finished_signal.emit(True)

        except Exception as e:
            print(f"❌ Fehler: {e}")
            import traceback
            traceback.print_exc()



    def cancel_search(self):
        self.cancel_thread_event.set()
        print("Suche wird abgebrochen...")

    def reset_progress_bar(self):
        if self.view:
            self.update_progress_signal.emit(0)

    def clear_cache(self):
        self.all_files_cache = []