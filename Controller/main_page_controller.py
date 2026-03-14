import os
import platform
import threading
import random
import time

from multiprocessing import Pool, Manager
import math

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QFileDialog, QApplication

from Process.search_process import SearchProcess
from Service.explorer_service import ExplorerService
from Service.reader_service import ReaderService
from View.messages import Messages
from project_data import ProjectData


class MainPageController(QObject):  # QObject für Signal-Support
    # Signale sind keine statics. Sie müssen aber auf Klassenebene stehen. siehe Signal - Descriptor
    add_result_signal = Signal(int, str, str, str, str)  # priority, title, body, treffer_typ, abs_path
    clear_results_signal = Signal()
    update_progress_signal = Signal(int)
    update_path_signal = Signal(str)
    show_status_signal = Signal(str, str)  # message, typ
    search_finished_signal = Signal(bool)
    matches_count_signal = Signal(int)
    no_path_selected_signal = Signal()
    wait_for_cache_file_paths_signal = Signal(bool)

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
        self.matches = 0

        # KEINE Queue mehr nötig! PySide6 Signals sind thread-sicher
        # self.ui_update_queue = deque()  # 👈 WEG DAMIT!

        # Multiprocessing berechnen der Process Counts
        self.num_processes = ProjectData.get_used_cores()
        self.threads_per_process = ProjectData.get_threads_count()  # Mehr Threads für I/O TODO User könnte das selbst steuern
        print(f"Performance: {self.num_processes} Prozesse mit je {self.threads_per_process} Threads")


    def _collect_files(self):
        """Hilfsmethode zum Sammeln der Dateien aus explorer_service.collect_file_info"""

        all_files, total = self.explorer_service.collect_file_info(
            self.path_selected_ui,
            self.search_recursive,
            self.cancel_thread_event
        )

        # Alle Pfad-Strings escapen
        if platform.system() == "Windows":
            for i in range(len(all_files)):
                all_files[i] = all_files[i].replace('\\', '\\\\')

        return all_files

    def set_view(self, view):
        self.view = view
        # Verbinde die Signale mit den View-Methoden
        self.add_result_signal.connect(view.add_result)
        self.clear_results_signal.connect(view.clear_results)
        self.update_progress_signal.connect(view.set_progress)
        self.update_path_signal.connect(view.update_path_label)

        self.search_finished_signal.connect(view.sort_results)
        self.search_finished_signal.connect(view.refresh_results_display)
        self.matches_count_signal.connect(view.set_matches_count)
        self.no_path_selected_signal.connect(lambda: Messages.set_no_path_selected(view))

        self.wait_for_cache_file_paths_signal.connect(
            lambda show: Messages.show_caching_spinner(view, show)
        )

        # KEIN Timer mehr nötig! Signals werden sofort im Haupt-Thread verarbeitet


    def choose_path(self):
        """Qt FileDialog für PySide"""
        pfad = QFileDialog.getExistingDirectory(
            self.view,
            "Verzeichnis auswählen",
            os.path.expanduser("~")
        )

        if pfad:
            self.process_selected_path(pfad)

    # clean path and cache cleanup
    def process_selected_path(self, pfad):
        """Normalize Path and clear cache"""
        # Plattformabhängige Pfadnormalisierung mit platform
        if platform.system() == "Windows":
            # Windows: Backslashes und ESCAPEN für Python-Strings!
            pfad = pfad.replace('/', '\\')  # Erst normalisieren
        else:
            # Linux/Mac: Forward Slashes
            pfad = pfad.replace('\\', '/')

        self.update_path_signal.emit(pfad)
        self.path_selected_ui = pfad
        if self.clear_cache():
            print("cashe cleanup done")
        else:
            print("❌ cache cleanup failed")



    def search(self, event=None):
        keywords = self.view.keywords_input.text()
        # reset matches
        self.matches = 0
        search_depth = int(self.view.search_depth_input.text()) if self.view.search_depth_input.text().isdigit() else ProjectData.search_depth # default einfach 4000
        self.view.search_depth_input.setText(str(search_depth))

        if not self.path_selected_ui:
            if ProjectData.default_search_path:
                self.process_selected_path(ProjectData.default_search_path)
            else:
                print("No path selected")
                self.no_path_selected_signal.emit()
                return


        if not keywords:
            print("No keywords entered.Type some into the input field.")
            return

        if self.search_thread and self.search_thread.is_alive():
            print("Last search is running...")
            print("Cancelling previous search...")
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
        print(f"🔍 START search for '{keywords}' ...")

    def _run_search_thread_multiprocessing(self, keywords, search_depth, cancel_thread_event):
        """
            Hauptsuchroutine - läuft im Thread, startet Multiprocessing-Pool
            Sammelt Dateien, filtert Namen, verteilt Content-Suche auf Prozesse
        """
        try:
            # Collecting all file paths. If not path choose in GUI is done then take cache
            if not self.all_files_cache:
                self.wait_for_cache_file_paths_signal.emit(True)

                print("start caching...")
                print("Collecting all files in selected path ...")
                all_files = self._collect_files()
                self.all_files_cache = all_files
                print("Pfade sammeln erledigt")
                self.wait_for_cache_file_paths_signal.emit(False)

            else:
                all_files = self.all_files_cache
                print("Using cached files from the last search")

            if not all_files:
                print("No files found in selected path")
                return

            total_files = len(all_files)
            print(f"{total_files} files will be processed on {self.num_processes} CPU cores...")

            # Dateinamen-Filter (superschnell)
            filepath_matches_set = set(self.explorer_service.filter_files_by_name(all_files, keywords))  # Set zerstört Dublikate hier sollten aber onehin keine sein
            namen_treffer = len(filepath_matches_set)

            # Dateinamen-Treffer SOFORT anzeigen - DIREKTES Signal!
            for match in filepath_matches_set:
                if cancel_thread_event.is_set():  # Wenn Stop kommt, dann soll Thread nicht weiter arbeiten
                    print(
                        "Cancel Thread" + threading.current_thread().name + "...")
                    return
                abs_path = os.path.abspath(match[1])
                filename = os.path.basename(match[1])
                rel_path = os.path.relpath(abs_path, self.path_selected_ui)
                self.matches += 1
                self.matches_count_signal.emit(self.matches)
                # DIREKTES Signal - sofortige Anzeige!
                self.add_result_signal.emit(match[0], filename, f"Path: {rel_path}", "filename", abs_path)

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
                        (chunk, keywords, search_depth, ProjectData.snippet_size, self.threads_per_process, i, progress_queue)
                    )
                    results.append(result)

                # Progress-Tracking
                letzter_progress = -1

                # Schnellere Queue-Verarbeitung Result ist eine async ops deshalb müssen wir auf ready warten
                while any(not r.ready() for r in results) or not progress_queue.empty():
                    if cancel_thread_event.is_set():
                        print("❌ CANCEL - Stop all Processes!")
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
                            self.matches += 1
                            self.matches_count_signal.emit(self.matches)
                            self.add_result_signal.emit(priority, filename, text, "content", abs_path)  # ✨ AN DIE GUI!

                        elif msg[0] == 'stats':
                            stats = msg[1]
                            print("===========================================")
                            print(f"Chunk {chunk_id} File Reader Service Statistic")
                            for key, value in stats.items():
                                print(f"{key.capitalize():<12}: {value}")
                            print("===========================================\n")

                    except:
                        pass


                self.update_progress_signal.emit(100)
                print(f"✅ Finished: {namen_treffer} filename matches, {self.matches} content matches")
                self.search_finished_signal.emit(True)

        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()



    def cancel_search(self):
        self.cancel_thread_event.set()
        print("Stop searching...")

    def reset_progress_bar(self):
        if self.view:
            self.update_progress_signal.emit(0)

    def clear_cache(self):
        self.all_files_cache = []
        if not self.all_files_cache:
            return True
        else:
            return False