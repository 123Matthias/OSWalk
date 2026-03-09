import os
import unicodedata
from typing import Optional, List
from pathlib import Path

# PDF
import fitz  # PyMuPDF - AGPL lizenziert

# Word
from docx import Document as DocxDocument

# Excel
import openpyxl
import csv


# PowerPoint
from pptx import Presentation


class ReaderService:
    """
    Service zum Lesen von Text aus verschiedenen Dateiformaten.
    Nutzt spezialisierte Bibliotheken für jedes Format.

    Verwendete Bibliotheken:
    - PyMuPDF (AGPL v3.0): https://pymupdf.readthedocs.io/
    - python-docx (MIT): Für Word-Dokumente
    - openpyxl (MIT): Für Excel-Dateien
    - python-pptx (MIT): Für PowerPoint-Präsentationen
    """

    def __init__(self):
        # Unterstützte Dateiformate
        self.supported_extensions = {
            # Dokumente
            '.pdf', '.txt', '.md', '.html', '.htm',
            '.docx', '.doc', '.odt', '.rtf',
            # Tabellen
            '.xlsx', '.xls', '.csv',
            # Präsentationen
            '.pptx', '.ppt',
        }

        # Für Statistiken/Logging
        self.stats = {
            'success': 0,
            'failed': 0,
            'unsupported': 0
        }


    def extract_text(self, filepath: str, max_chars: Optional[int] = 1000) -> Optional[str]:
        """
        Zentrale Methode: erkennt Dateiformat und ruft passende Extraktionsmethode auf.

        Args:
            filepath: Pfad zur Datei
            max_chars: Maximale Zeichenanzahl - WICHTIG: Dies ist die SUCHTIEFE!
                      Sobald diese Zeichenanzahl erreicht ist, wird abgebrochen.

        Returns:
            Extrahierter Text oder None bei Fehler
        """
        # Pfad normalisieren (nur für Dateisystem-Zugriff)
        path = Path(filepath)
        safe_path = path.as_posix()

        if not os.path.exists(safe_path):
            print(f"❓ Datei nicht gefunden: {safe_path}")
            return None

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in self.supported_extensions:
            print(f"⚠️ Format nicht unterstützt: {filepath}")
            self.stats['unsupported'] += 1
            return None

        # Format-spezifische Extraktion
        try:
            if ext == '.pdf':
                text = self._extract_pdf(safe_path, max_chars)
            elif ext in {'.txt', '.md'}:
                text = self._extract_text_file(safe_path, max_chars)
            elif ext in {'.html', '.htm'}:
                text = self._extract_html(safe_path, max_chars)
            elif ext in {'.docx', '.doc'}:
                text = self._extract_word(safe_path, max_chars)
            elif ext in {'.xlsx', '.xls'}:
                text = self._extract_excel(safe_path, max_chars)
            elif ext == '.csv':
                text = self._extract_csv(safe_path, max_chars)
            elif ext in {'.pptx', '.ppt'}:
                text = self._extract_powerpoint(safe_path, max_chars)
            elif ext == '.odt':
                text = self._extract_opendocument(safe_path, max_chars)
            elif ext == '.rtf':
                text = self._extract_rtf(safe_path, max_chars)
            else:
                text = self._extract_generic(safe_path, max_chars)

            if not text:
                return None

            # 🔥 Text für Vergleich normalisieren (NFC)
            text = unicodedata.normalize('NFC', text)

            # Text bereinigen (mehrfache Leerzeichen entfernen)
            text = ' '.join(text.split())

            self.stats['success'] += 1
            return text

        except Exception as e:
            print(f"❌ Fehler beim Lesen von {filepath}: {e}")
            self.stats['failed'] += 1
            return None

    # ===== PDF =====
    def _extract_pdf(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """PDF-Extraktion mit PyMuPDF - bricht bei max_chars ab."""
        try:
            doc = fitz.open(filepath)
            text_parts = []
            total_chars = 0

            for page_num in range(len(doc)):
                if max_chars and total_chars >= max_chars:
                    break

                page = doc[page_num]
                page_text = page.get_text()

                if max_chars:
                    remaining = max_chars - total_chars
                    if len(page_text) > remaining:
                        page_text = page_text[:remaining]

                text_parts.append(page_text)
                total_chars += len(page_text)

            doc.close()
            return "\n".join(text_parts)

        except Exception as e:
            print(f"⚠️ PyMuPDF Fehler: {e}")
            raise

    # ===== Textdateien =====
    def _extract_text_file(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """Einfache Textdateien - bricht bei max_chars ab."""
        try:
            if max_chars:
                # Nur die ersten max_chars Zeichen lesen
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(max_chars)
            else:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except Exception as e:
            print(f"⚠️ Textdatei-Fehler: {e}")
            raise

    def _extract_html(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """HTML-Dateien - bricht bei max_chars ab."""
        try:
            # Erst gesamten Text extrahieren, dann kürzen
            from bs4 import BeautifulSoup
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                text = soup.get_text(separator=' ', strip=True)

            if max_chars and len(text) > max_chars:
                text = text[:max_chars]
            return text

        except ImportError:
            # Fallback: Einfaches Regex-Stripping
            import re
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()
                text = re.sub(r'<[^>]+>', ' ', html)
                text = re.sub(r'\s+', ' ', text)

            if max_chars and len(text) > max_chars:
                text = text[:max_chars]
            return text.strip()
        except Exception as e:
            print(f"⚠️ HTML-Fehler: {e}")
            raise

    # ===== Word =====
    def _extract_word(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """Word-Dokumente (.docx) - bricht bei max_chars ab."""
        try:
            doc = DocxDocument(filepath)
            text_parts = []
            total_chars = 0

            # Absätze
            for para in doc.paragraphs:
                if max_chars and total_chars >= max_chars:
                    break

                if para.text:
                    if max_chars:
                        remaining = max_chars - total_chars
                        if len(para.text) > remaining:
                            text_parts.append(para.text[:remaining])
                            total_chars = max_chars
                        else:
                            text_parts.append(para.text)
                            total_chars += len(para.text)
                    else:
                        text_parts.append(para.text)
                        total_chars += len(para.text)

            # Tabellen (nur wenn noch Platz)
            if not max_chars or total_chars < max_chars:
                for table in doc.tables:
                    if max_chars and total_chars >= max_chars:
                        break

                    for row in table.rows:
                        if max_chars and total_chars >= max_chars:
                            break

                        for cell in row.cells:
                            if max_chars and total_chars >= max_chars:
                                break

                            if cell.text:
                                if max_chars:
                                    remaining = max_chars - total_chars
                                    if len(cell.text) > remaining:
                                        text_parts.append(cell.text[:remaining])
                                        total_chars = max_chars
                                    else:
                                        text_parts.append(cell.text)
                                        total_chars += len(cell.text)
                                else:
                                    text_parts.append(cell.text)
                                    total_chars += len(cell.text)

            return "\n".join(text_parts)

        except ImportError:
            print("⚠️ python-docx nicht installiert. Bitte installieren: pip install python-docx")
            raise
        except Exception as e:
            print(f"⚠️ Word-Fehler: {e}")
            raise

    # ===== Excel =====
    def _extract_excel(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """Excel-Dateien - bricht bei max_chars ab."""
        text_parts = []
        total_chars = 0

        try:
            if filepath.endswith('.xlsx'):
                import openpyxl
                wb = openpyxl.load_workbook(filepath, data_only=True)

                for sheet_name in wb.sheetnames:
                    if max_chars and total_chars >= max_chars:
                        break

                    sheet = wb[sheet_name]
                    sheet_header = f"--- Sheet: {sheet_name} ---"

                    if max_chars:
                        remaining = max_chars - total_chars
                        if len(sheet_header) > remaining:
                            text_parts.append(sheet_header[:remaining])
                            total_chars = max_chars
                        else:
                            text_parts.append(sheet_header)
                            total_chars += len(sheet_header)
                    else:
                        text_parts.append(sheet_header)
                        total_chars += len(sheet_header)

                    for row in sheet.iter_rows(values_only=True):
                        if max_chars and total_chars >= max_chars:
                            break

                        row_text = ' '.join([str(cell) for cell in row if cell is not None])
                        if row_text.strip():
                            if max_chars:
                                remaining = max_chars - total_chars
                                if len(row_text) > remaining:
                                    text_parts.append(row_text[:remaining])
                                    total_chars = max_chars
                                else:
                                    text_parts.append(row_text)
                                    total_chars += len(row_text)
                            else:
                                text_parts.append(row_text)
                                total_chars += len(row_text)

            elif filepath.endswith('.xls'):
                import xlrd
                wb = xlrd.open_workbook(filepath)

                for sheet_idx in range(wb.nsheets):
                    if max_chars and total_chars >= max_chars:
                        break

                    sheet = wb.sheet_by_index(sheet_idx)
                    sheet_header = f"--- Sheet: {sheet.name} ---"

                    if max_chars:
                        remaining = max_chars - total_chars
                        if len(sheet_header) > remaining:
                            text_parts.append(sheet_header[:remaining])
                            total_chars = max_chars
                        else:
                            text_parts.append(sheet_header)
                            total_chars += len(sheet_header)
                    else:
                        text_parts.append(sheet_header)
                        total_chars += len(sheet_header)

                    for row_idx in range(sheet.nrows):
                        if max_chars and total_chars >= max_chars:
                            break

                        row = sheet.row_values(row_idx)
                        row_text = ' '.join([str(cell) for cell in row if cell != ''])
                        if row_text.strip():
                            if max_chars:
                                remaining = max_chars - total_chars
                                if len(row_text) > remaining:
                                    text_parts.append(row_text[:remaining])
                                    total_chars = max_chars
                                else:
                                    text_parts.append(row_text)
                                    total_chars += len(row_text)
                            else:
                                text_parts.append(row_text)
                                total_chars += len(row_text)

            return "\n".join(text_parts)

        except ImportError as e:
            print(f"⚠️ Excel-Bibliothek fehlt: {e}. Bitte installieren: pip install openpyxl xlrd")
            raise
        except Exception as e:
            print(f"⚠️ Excel-Fehler: {e}")
            raise

    def _extract_csv(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """CSV-Dateien - bricht bei max_chars ab."""
        try:
            text_parts = []
            total_chars = 0
            encodings = ['utf-8', 'latin-1', 'cp1252']

            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if max_chars and total_chars >= max_chars:
                                break

                            row_text = ' '.join(row)
                            if row_text.strip():
                                if max_chars:
                                    remaining = max_chars - total_chars
                                    if len(row_text) > remaining:
                                        text_parts.append(row_text[:remaining])
                                        total_chars = max_chars
                                    else:
                                        text_parts.append(row_text)
                                        total_chars += len(row_text)
                                else:
                                    text_parts.append(row_text)
                                    total_chars += len(row_text)
                    break  # Erfolgreich gelesen
                except UnicodeDecodeError:
                    continue  # Nächstes Encoding probieren

            return "\n".join(text_parts)

        except Exception as e:
            print(f"⚠️ CSV-Fehler: {e}")
            raise

    # ===== PowerPoint =====
    def _extract_powerpoint(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """PowerPoint-Präsentationen - bricht bei max_chars ab."""
        try:
            prs = Presentation(filepath)
            text_parts = []
            total_chars = 0

            for slide_num, slide in enumerate(prs.slides):
                if max_chars and total_chars >= max_chars:
                    break

                slide_header = f"--- Slide {slide_num + 1} ---"

                if max_chars:
                    remaining = max_chars - total_chars
                    if len(slide_header) > remaining:
                        text_parts.append(slide_header[:remaining])
                        total_chars = max_chars
                    else:
                        text_parts.append(slide_header)
                        total_chars += len(slide_header)
                else:
                    text_parts.append(slide_header)
                    total_chars += len(slide_header)

                for shape in slide.shapes:
                    if max_chars and total_chars >= max_chars:
                        break

                    if hasattr(shape, "text") and shape.text.strip():
                        if max_chars:
                            remaining = max_chars - total_chars
                            if len(shape.text) > remaining:
                                text_parts.append(shape.text[:remaining])
                                total_chars = max_chars
                            else:
                                text_parts.append(shape.text)
                                total_chars += len(shape.text)
                        else:
                            text_parts.append(shape.text)
                            total_chars += len(shape.text)

                    # Tabellen in Slides
                    if hasattr(shape, "table"):
                        for row in shape.table.rows:
                            if max_chars and total_chars >= max_chars:
                                break

                            for cell in row.cells:
                                if max_chars and total_chars >= max_chars:
                                    break

                                if cell.text:
                                    if max_chars:
                                        remaining = max_chars - total_chars
                                        if len(cell.text) > remaining:
                                            text_parts.append(cell.text[:remaining])
                                            total_chars = max_chars
                                        else:
                                            text_parts.append(cell.text)
                                            total_chars += len(cell.text)
                                    else:
                                        text_parts.append(cell.text)
                                        total_chars += len(cell.text)

            return "\n".join(text_parts)

        except ImportError:
            print("⚠️ python-pptx nicht installiert. Bitte installieren: pip install python-pptx")
            raise
        except Exception as e:
            print(f"⚠️ PowerPoint-Fehler: {e}")
            raise

    # ===== OpenDocument / RTF =====
    def _extract_opendocument(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """OpenDocument-Text (.odt) - bricht bei max_chars ab."""
        try:
            import zipfile
            with zipfile.ZipFile(filepath, 'r') as odt:
                content = odt.read('content.xml').decode('utf-8', errors='ignore')
                # Einfaches XML-Stripping
                import re
                text = re.sub(r'<[^>]+>', ' ', content)
                text = re.sub(r'\s+', ' ', text)

            if max_chars and len(text) > max_chars:
                text = text[:max_chars]
            return text.strip()

        except Exception as e:
            print(f"⚠️ ODT-Fehler: {e}")
            raise

    def _extract_rtf(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """RTF-Dateien - bricht bei max_chars ab."""
        try:
            from striprtf.striprtf import rtf_to_text
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()
                text = rtf_to_text(rtf_content)

            if max_chars and len(text) > max_chars:
                text = text[:max_chars]
            return text

        except ImportError:
            # Fallback
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                import re
                text = re.sub(r'\\[a-z]+\d*', ' ', content)
                text = re.sub(r'[{}]', ' ', text)
                text = re.sub(r'\s+', ' ', text)

            if max_chars and len(text) > max_chars:
                text = text[:max_chars]
            return text.strip()
        except Exception as e:
            print(f"⚠️ RTF-Fehler: {e}")
            raise


    def _extract_generic(self, filepath: str, max_chars: Optional[int] = None) -> str:
        """Fallback für nicht implementierte Formate."""
        print(f"ℹ️ Generische Extraktion für {filepath} - versuche als Textdatei")
        return self._extract_text_file(filepath, max_chars)

    # ===== Hilfsmethoden =====
    def get_snippet(self, filepath: str, keywords: str = "", context_chars: int = 200) -> Optional[str]:
        """Erste 500 Zeichen als Snippet."""
        text = self.extract_text(filepath, max_chars=None)
        if not text:
            return f"Path: {filepath}"

        # NFC-normalisieren für konsistenten Vergleich
        text = unicodedata.normalize('NFC', text)
        return text[:500] + "..."

    def is_supported(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.supported_extensions

    def get_stats(self) -> dict:
        """Gibt Statistiken zurück."""
        return self.stats.copy()