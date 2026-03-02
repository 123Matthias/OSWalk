import os
import threading
from tkinter import filedialog

from Service.explorer_service import ExplorerService
from Service.reader_service import ReaderService


class MainPageController:
    def __init__(self):
        self.view = None
        self.reader_service = ReaderService()
        self.explorer_service = ExplorerService()
        self.search_thread = None
        self.cancel_search = False

        self.progress_inkrement = 0.0
        self.all_files_cache = []  # Cache für alle Dateien

    def set_view(self, view):
        """Setzt die View-Referenz nach der Erstellung"""
        self.view = view

    def choose_path(self):
        """Pfad auswählen und in der View aktualisieren"""
        pfad = filedialog.askdirectory(initialdir=os.path.expanduser("~/Downloads"))
        if pfad:
            self.view.pfad_label.configure(text=pfad)
            self.view.basis_pfad = pfad
            # Cache zurücksetzen bei neuem Pfad
            self.all_files_cache = []

    def search(self, event=None):
        """Startet die Suche in einem separaten Thread"""
        keywords = self.view.keywords.get()

        # Prüfen ob ein Pfad ausgewählt wurde
        if not hasattr(self.view, "basis_pfad") or not self.view.basis_pfad:
            print("Kein Pfad ausgewählt")
            return

        if not keywords:
            print("Kein Suchbegriff eingegeben")
            return

        # Prüfen ob bereits ein Suchlauf läuft
        if self.search_thread and self.search_thread.is_alive():
            print("Suche läuft bereits, wird abgebrochen...")
            self.cancel_search = True
            self.search_thread.join(timeout=1.0)

        # Alte Ergebnisse löschen
        self.view.clear_results()

        # Neuen Such-Thread starten
        self.cancel_search = False
        self.search_thread = threading.Thread(target=self._run_search_thread, args=(keywords,))
        self.search_thread.daemon = True
        self.search_thread.start()

        print(f"🔍 Suche nach '{keywords}' gestartet...")

    def _run_search_thread(self, keywords):
        """
        Optimierte Suchlogik mit nur einem os.walk Durchlauf.
        """
        self.reset_progress_bar()

        try:
            # ===== 1️⃣ EINMALIG: Alle Dateien sammeln und zählen =====
            if not self.all_files_cache:
                print("📁 Sammle alle Dateien...")
                # Sammle alle Dateien und zähle sie in einem Durchlauf
                all_files, total_files = self.explorer_service.collect_file_info(
                    self.view.basis_pfad,
                    recursive=True
                )
                self.all_files_cache = all_files
                self.progress_inkrement = 100.0 / total_files if total_files > 0 else 1.0
                print(f"{total_files} Dateien gefunden")
            else:
                # Wenn wir bereits einen Cache haben, nutzen wir den
                all_files = self.all_files_cache
                self.progress_inkrement = 100.0 / len(all_files) if all_files else 1.0

            # ===== 2️⃣ Suche nach Dateinamen =====
            dateinamen_treffer = self.explorer_service.filter_files_by_name(
                all_files,
                keywords
            )

            # Set für schnellen Lookup
            treffer_set = set(dateinamen_treffer)

            namen_treffer_count = 0
            inhalt_treffer_count = 0

            # Keywords für Inhaltssuche vorbereiten
            keyword_list = [k.strip().lower() for k in keywords.replace(',', ' ').split() if k.strip()]

            # ===== 3️⃣ Gemeinsamer Durchlauf für beide Sucharten =====
            for dateipfad in all_files:
                if self.cancel_search:
                    self.reset_progress_bar()
                    print("Suche abgebrochen")
                    return

                dateiname = os.path.basename(dateipfad)
                rel_pfad = os.path.relpath(dateipfad, self.view.basis_pfad)

                # Fortschritt aktualisieren (für jede Datei)
                self.update_progress_bar(self.progress_inkrement)

                # Prüfen ob Dateiname-Treffer
                if dateipfad in treffer_set:
                    snippet_text = f"Fundort: {rel_pfad}"
                    self.view.add_result(dateiname, snippet_text, "filename")
                    namen_treffer_count += 1
                    continue  # Bei Namens-Treffer keine Inhaltssuche mehr nötig

                # Inhaltssuche nur für Dateien ohne Namens-Treffer
                try:
                    text = self.reader_service.extract_text(dateipfad, max_chars=2000)

                    if text:
                        text_lower = text.lower()

                        for keyword in keyword_list:
                            if keyword in text_lower:
                                kontext = self._make_body_text(text, keyword, ctx=200)
                                if kontext:
                                    snippet_text = f"'{keyword}' gefunden in: {rel_pfad}\n...{kontext}..."
                                else:
                                    snippet_text = f"Treffer im Inhalt\nFundort: {rel_pfad}"

                                self.view.add_result(dateiname, snippet_text, "content")
                                inhalt_treffer_count += 1
                                break  # Ein Treffer pro Datei reicht

                except Exception as e:
                    # Falls Datei nicht lesbar, einfach überspringen
                    print(f"⚠️ Konnte {dateipfad} nicht lesen: {e}")
                    continue

            print(f"✅ Suche abgeschlossen: {namen_treffer_count} Treffer im Dateinamen, "
                  f"{inhalt_treffer_count} Treffer im Inhalt, "
                  f"{total_files} Dateien gefunden.")

        except Exception as e:
            print(f"❌ Fehler bei der Suche: {e}")

    def _make_body_text(self, text, keyword, ctx=100):
        """Erstellt ein Snippet mit Keyword im Kontext."""
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

    def cancel_search(self):
        """Bricht die laufende Suche ab"""
        self.cancel_search = True
        print("Suche wird abgebrochen...")

    def update_progress_bar(self, value):
        """Progress-Wert aktualisieren"""
        self.view.progress_state.set(self.view.progress_state.get() + value)

    def reset_progress_bar(self):
        """Progress zurücksetzen"""
        self.view.progress_state.set(0)

    def clear_cache(self):
        """Cache leeren (z.B. bei Pfadwechsel)"""
        self.all_files_cache = []