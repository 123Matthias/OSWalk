import json
import os


class Language:
    _data = {}

    @classmethod
    def load(cls, language="English"):
        """Lädt die Sprachdatei"""
        # EINFACH: Immer vom Projektverzeichnis aus
        file_path = f"assets/languages/{language}.json"

        print(f"📂 Lade von: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            cls._data = json.load(f)

    @classmethod
    def get(cls, page, key):
        return cls._data[page][key]