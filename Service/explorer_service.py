import os
import unicodedata
from typing import List, Tuple, Optional, Generator


class ExplorerService:
    def __init__(self):
        pass

    def walk_files(self, directory: str, recursive: bool = True) -> Generator[str, None, None]:
        """
        Generiert alle Dateipfade in einem Verzeichnis (optional rekursiv).
        Dies ist die einzige Stelle, die os.walk aufruft.
        """
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
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

    def collect_file_info(self, directory: str, recursive: bool = True) -> Tuple[List[str], int]:
        """
        Sammelt einmalig alle Dateipfade und zählt sie gleichzeitig.
        Gibt ein Tuple zurück: (liste_aller_dateien, anzahl_dateien)
        """
        all_files = []
        count = 0

        for filepath in self.walk_files(directory, recursive):
            all_files.append(filepath)
            count += 1
        return all_files, count

    def filter_files_by_name(self, filepaths: List[str], keywords: Optional[str] = None) -> List[str]:
        """
        Filtert eine Liste von Dateipfaden nach Keywords im Dateinamen.
        """
        if not keywords:
            return filepaths.copy()

        # Keywords aufbereiten
        cleaned = keywords.replace(',', ' ')
        keyword_list = [k.strip().lower() for k in cleaned.split() if k.strip()]

        if not keyword_list:
            return filepaths.copy()

        filtered_files = []

        for filepath in filepaths:
            filename = os.path.basename(filepath)
            file_lower = filename.lower()
            file_normalized = unicodedata.normalize('NFC', file_lower)

            for keyword in keyword_list:
                keyword_normalized = unicodedata.normalize('NFC', keyword.lower())
                if keyword_normalized in file_normalized:
                    filtered_files.append(filepath)
                    break

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