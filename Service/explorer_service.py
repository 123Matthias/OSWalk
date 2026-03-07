import os
import threading
import unicodedata
from threading import Thread
from typing import List, Tuple, Optional, Generator


class ExplorerService:

    Keyword_List:List[str] = []
    Max_Priority: int = 0

    def __init__(self):
        pass

    def walk_files(self, directory: str, recursive: bool = True, cancel_thread_event = None) -> Generator[str, None, None]:
        """
        Generiert alle Dateipfade in einem Verzeichnis (optional rekursiv).
        Dies ist die einzige Stelle, die os.walk aufruft.
        """
        if cancel_thread_event.is_set():
            print(threading.current_thread().name + "wird beendet")
            return

        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if cancel_thread_event.is_set():
                        print(threading.current_thread().name + "wird beendet")
                        return
                    yield os.path.join(root, file)
        else:
            try:
                for item in os.listdir(directory):
                    full_path = os.path.join(directory, item)
                    if os.path.isfile(full_path):
                        yield full_path
            except PermissionError:
                # Bei Zugriffsfehlern einfach ignorieren und weitermachen
                pass

    def collect_file_info(self, directory: str, recursive: bool = True, cancel_thread_event = None) -> Tuple[List[str], int]:
        """
        Sammelt einmalig alle Dateipfade und zählt sie gleichzeitig.
        Gibt ein Tuple zurück: (liste_aller_dateien, anzahl_dateien)
        """
        all_files = []
        count = 0

        for filepath in self.walk_files(directory, recursive, cancel_thread_event):
            all_files.append(filepath)
            count += 1
        return all_files, count

    def filter_files_by_name(self, filepaths: List[str], keywords: Optional[str] = None) -> List[Tuple[int, str]]:
        """
        Filtert eine Liste von Dateipfaden nach Keywords im Dateinamen.
        Gibt pro Datei ein Tuple zurück: (priority, max_priority, filepath)
        """
        if not keywords:
            return [(0, filepath) for filepath in filepaths]

        # Keywords aufbereiten
        cleaned = keywords.replace(',', ' ')
        keyword_list = [k.strip().lower() for k in cleaned.split() if k.strip()]

        if not keyword_list:
            return [(0,filepath) for filepath in filepaths]

        ExplorerService.Keyword_List = keyword_list
        filtered_files = []
        ExplorerService.Max_Priority = sum(i + 1 for i in range(len(keyword_list)))  # z.B. 5 Keywords → 15

        for filepath in filepaths:
            priority = 0  # Reset pro Datei
            filename = os.path.basename(filepath)
            file_lower = filename.lower()
            file_normalized = unicodedata.normalize('NFC', file_lower)

            for i, keyword in enumerate(keyword_list, start=1):
                keyword_normalized = unicodedata.normalize('NFC', keyword.lower())
                if keyword_normalized in file_normalized:
                    priority += i  # Summe aller Treffer

            if priority > 0:  # Nur Dateien mit mindestens einem Treffer
                filtered_files.append((priority, filepath))  # Ein Tuple pro Datei

        return filtered_files

    def count_files(self, path: str) -> int:
        """
        Zählt Dateien - jetzt effizienter mit einem schnellen Durchlauf.
        """
        count = 0
        try:
            for root, dirs, files in os.walk(path):
                count += len(files)
        except Exception:
            pass
        return count

    # Alternative, wenn Sie den Generator wiederverwenden wollen:
    def count_files_fast(self, path: str) -> int:
        """
        Noch effizientere Zählung, die nur zählt, ohne die Pfade zu speichern.
        """
        count = 0
        for _ in self.walk_files(path, recursive=True):
            count += 1
        return count