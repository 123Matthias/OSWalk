import os
import textract
from typing import Optional

class ReaderService:
    """
    Service zum Lesen von Text aus verschiedenen Dateiformaten.
    Verwendet textract als universelle Extraktions-Engine.
    """

    def __init__(self):
        # Unterstützte Dateiformate (für schnelle Prüfung)
        self.supported_extensions = {
            # Dokumente
            '.pdf', '.docx', '.doc', '.odt', '.rtf',
            # Tabellen
            '.xlsx', '.xls', '.csv',
            # Präsentationen
            '.pptx', '.ppt',
            # Apple
            '.pages', '.key', '.numbers',
            # Text
            '.txt', '.md', '.html', '.htm',
            # Bilder (OCR)
           # '.png', '.jpg', '.jpeg', '.gif', '.tiff'
        }

    def extract_text(self, filepath: str, max_chars: int = 1000) -> Optional[str]:
        """
        Extrahiert Text aus einer Datei.

        Args:
            filepath: Pfad zur Datei
            max_chars: Maximale Anzahl Zeichen (für Snippets)

        Returns:
            Extrahierter Text oder None bei Fehler
        """
        try:
            # Prüfe ob Datei existiert
            if not os.path.exists(filepath):
                print(f"❓ Datei nicht gefunden: {filepath}")
                return None

            # Prüfe ob Format unterstützt wird
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in self.supported_extensions:
               # print(f"⚠️ Format nicht unterstützt: {filepath}")
                return None

            # Text mit textract extrahieren
            text_bytes = textract.process(filepath)
            text = text_bytes.decode('utf-8', errors='ignore')

            # Text bereinigen (mehrere Leerzeichen, Zeilenumbrüche)
            text = ' '.join(text.split())

            # Auf maximale Länge begrenzen
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            return text

        except Exception as e:
            print(f"❌ Fehler beim Lesen von {filepath}: {e}")
            return None

    def extract_text_simple(self, filepath: str) -> Optional[str]:
        """
        Einfache Version ohne Maximal-Länge.
        """
        return self.extract_text(filepath, max_chars=None)

    def get_snippet(self, filepath: str, keywords: str, context_chars: int = 200) -> Optional[str]:
        """
        Extrahiert einen Snippet mit Keyword-Kontext.

        Args:
            filepath: Pfad zur Datei
            keywords: Suchbegriffe (für spätere Hervorhebung)
            context_chars: Wie viele Zeichen vor/nach dem Fund

        Returns:
            Text-Snippet oder None
        """
        text = self.extract_text(filepath, max_chars=None)
        if not text:
            return f"Path: {filepath}"

        # Für jetzt: Erste 500 Zeichen zurückgeben
        return text[:500] + "..."

    def is_supported(self, filepath: str) -> bool:
        """Prüft ob ein Dateiformat unterstützt wird."""
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.supported_extensions