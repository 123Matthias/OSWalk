# Service/font_awesome_service.py
import os
from PySide6.QtGui import QFontDatabase, QFont
import sys

class FontAwesomeService:

    @staticmethod
    def load_font():
        # Absoluter Pfad von dieser Datei aus
        file_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(file_dir, "../assets/fa-7-Free-Solid-900.otf")

        font_path = os.path.abspath(font_path)  # sicherer absoluter Pfad

        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            print(f"❌ Font konnte nicht geladen werden: {font_path}")
            sys.exit(1)

        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        font_awesome_7 = QFont(family, 16)
        print(f"✅ Geladene Font-Familien: {family}")
        return font_awesome_7

