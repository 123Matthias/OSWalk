import os
import threading
import random
import time

from multiprocessing import Pool, cpu_count, Manager
import math

from PySide6.QtCore import QObject, Signal, QTimer  # Qt Signals für Thread-Sicherheit
from PySide6.QtWidgets import QFileDialog  # Qt FileDialog

from Process.search_process import SearchProcess
from Service.explorer_service import ExplorerService
from Service.reader_service import ReaderService
from project_data import ProjectData


class MainPageController(QObject):  # QObject für Signal-Support
    # Signale sind keine statics. Sie müssen aber auf Klassenebene stehen. siehe Signal - Descriptor
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
        self.path_selected_ui = None

        # KEINE Queue mehr nötig! PySide6 Signals sind thread-sicher
        # self.ui_update_queue = deque()  # 👈 WEG DAMIT!

        # Multiprocessing berechnen der Process Counts
        cpu_cores = ProjectData.get_process_cores()
        self.num_processes = max(1, cpu_cores - 2)  # Min 1 Kern für UI frei lassen
        self.threads_per_process = 4  # Mehr Threads für I/O TODO User könnte das selbst steuern
        print(f"Performance: {self.num_processes} Prozesse mit je {self.threads_per_process} Threads")

    def _collect_files(self):
        """Hilfsmethode zum Sammeln der Dateien aus explorer_service.collect_file_info"""
        all_files, total = self.explorer_service.collect_file_info(
            self.path_selected_ui,
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
            self.view,
            "Verzeichnis auswählen",
            os.path.expanduser("~")  # 👈 Tilde wird zu C:/Users/name
        )

        if pfad:
            # Backslashes korrigieren
            pfad = pfad.replace('\\', '/')

            self.update_path_signal.emit(pfad)
            self.path_selected_ui = pfad
            self.all_files_cache = []

    def search(self, event=None):
        keywords = self.view.keywords_input.text()
        search_depth = int(self.view.search_depth_input.text()) if self.view.search_depth_input.text().isdigit() else 1000 # default einfach 1000
        self.view.search_depth_input.setText(str(search_depth))

        if not self.path_selected_ui:
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
            args=(keywords, search_depth, self.cancel_thread_event),
            name="search_thread" + time.strftime("%Y%m%d-%H%M%S"),
            daemon=True
        )
        self.search_thread.start()  # Startet den Thread erst
        print(f"🔍 Suche nach '{keywords}' gestartet...")

    def _run_search_thread_multiprocessing(self, keywords, search_depth, cancel_thread_event):
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
            filepath_matches_set = set(self.explorer_service.filter_files_by_name(all_files, keywords))  # Set zerstört Dublikate hier sollten aber onehin keine sein
            namen_treffer = len(filepath_matches_set)

            # Dateinamen-Treffer SOFORT anzeigen - DIREKTES Signal!
            for match in filepath_matches_set:
                if cancel_thread_event.is_set():  # Wenn Stop kommt, dann soll Thread nicht weiter arbeiten
                    print(
                        "abbrechen " + threading.current_thread().name + "in for Schleife for dateipfad in filepath_matches_set ...")
                    return
                abs_path = os.path.abspath(match[1])
                filename = os.path.basename(match[1])
                rel_path = os.path.relpath(abs_path, self.path_selected_ui)
                # DIREKTES Signal - sofortige Anzeige!
                self.add_result_signal.emit(match[0], filename, f"Fundort: {rel_path}", "filename", abs_path)

            # Dateien für Content-Suche
            files_content_search = [f for f in all_files if f not in filepath_matches_set]

            if not files_content_search:
                self.update_progress_signal.emit(100)  # Fertig wenns nix gibt was noch zu prüfen ist also inhalt
                return

            # Zufällig mischen für Lastverteilung für bessere Aufteilung der Datenmengen auf Processes
            random.shuffle(files_content_search)

            # Chunk-Größe bestimmen. Ein Chunk ist die Menge an Files, die zu einem Prozess zugeordnet wird
            chunk_size = math.ceil(len(files_content_search) / self.num_processes)

            # 1. i = 0:  meine_liste[0 : 0+3] = meine_liste[0:3] → [0, 1, 2]
            # 2. i = 3:  meine_liste[3 : 3+3] = meine_liste[3:6] → [3, 4, 5]
            # 3. i = 6:  meine_liste[6 : 6+3] = meine_liste[6:9] → [6, 7, 8]
            chunks = [files_content_search[i:i + chunk_size] for i in range(0, len(files_content_search), chunk_size)]

            # Shared Queue mit Manager prozessübergreifender Zugriff möglich
            manager = Manager()
            progress_queue = manager.Queue()
            chunk_status = [0] * len(chunks)

            # CPU lastige Dinge kommen in den Pool multiprocessing process_chunk_static methode außerhalb der Klasse wegen pickling wird aufgerufen
            with Pool(processes=self.num_processes) as pool:
                results = []
                for i, chunk in enumerate(chunks):
                    result = pool.apply_async(
                        SearchProcess.process_chunk_static,
                        (chunk, keywords, search_depth, self.threads_per_process, i, progress_queue)
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

                        elif msg[0] == 'match':
                            # 🔥 TREFFER-UPDATE: Hier werden Treffer aus der Queue geholt!
                            match = msg[1]  # Auspacken des Tuples: ('match', result)
                            priority, typ, filename, abs_path, kontext = match

                            # Formatiere und sende an GUI!
                            text = f"'...{kontext}..."
                            self.add_result_signal.emit(priority, filename, text, "content", abs_path)  # ✨ AN DIE GUI!

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