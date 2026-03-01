import os
import sys
from tkinter import filedialog
import ttkbootstrap as ttk
from Service.reader_service import ReaderService  # ✅ Korrekter Import


class MainPageController:
    def __init__(self, view):
        """
        Controller benötigt eine Referenz auf die View
        """
        self.view = view  # Referenz auf die MainPage-Instanz

        # ReaderService direkt im Controller initialisieren (optional)
        # oder über view.reader_service verwenden
        self.reader_service = ReaderService()

    def choose_path(self):
        """Pfad auswählen und in der View aktualisieren"""
        pfad = filedialog.askdirectory(initialdir=os.path.expanduser("~/Downloads"))
        if pfad:
            self.view.pfad_label.configure(text=pfad)
            self.view.basis_pfad = pfad

    def suchen(self, event=None):
        """Erweiterte Suche: Zuerst Dateinamen, dann Dateiinhalt"""
        keywords = self.view.keywords.get()

        # Prüfen ob ein Pfad ausgewählt wurde
        if not hasattr(self.view, "basis_pfad") or not self.view.basis_pfad:
            print("Kein Pfad ausgewählt")
            return

        if not keywords:
            print("Kein Suchbegriff eingegeben")
            return

        # Alte Ergebnisse löschen
        self.clear_results()

        # ===== 1️⃣ ZUERST: Suche nach Dateinamen =====
        dateien_mit_namen = self.view.explorer_service.list_files(
            self.view.basis_pfad,
            keywords,
            recursive=True
        )

        namens_treffer = 0
        for dateipfad in dateien_mit_namen[:30]:  # Erste 30 Namens-Treffer
            dateiname = os.path.basename(dateipfad)
            snippet = f"📁 Treffer im Dateinamen\nFundort: {dateipfad}"

            self.create_snipped(
                self.view.scrollable,
                f"{dateiname} (im Namen)",
                snippet
            )
            namens_treffer += 1

        # ===== 2️⃣ DANN: Suche im Dateiinhalt =====
        # Alle Dateien im Verzeichnis (ohne Namensfilter)
        alle_dateien = self.view.explorer_service.list_files(
            self.view.basis_pfad,
            recursive=True
        )

        # Keywords für die Inhaltssuche aufbereiten
        keyword_list = [k.strip().lower() for k in keywords.replace(',', ' ').split() if k.strip()]

        inhalt_treffer = 0
        max_inhalt_treffer = 30  # Maximal 30 Inhaltstreffer anzeigen

        for dateipfad in alle_dateien:
            if inhalt_treffer >= max_inhalt_treffer:
                break

            # Überspringe Dateien, die schon als Namens-Treffer angezeigt wurden
            if dateipfad in dateien_mit_namen:
                continue

            dateiname = os.path.basename(dateipfad)

            try:
                # ✅ ReaderService für Text-Extraktion nutzen
                # Entweder über view oder über self.reader_service
                if hasattr(self.view, 'reader_service'):
                    text = self.view.reader_service.extract_text(dateipfad, max_chars=2000)
                else:
                    text = self.reader_service.extract_text(dateipfad, max_chars=2000)

                if text:
                    text_lower = text.lower()

                    for keyword in keyword_list:
                        if keyword in text_lower:
                            # Treffer! Snippet mit Kontext erstellen
                            kontext = self.make_snippet(text, keyword, ctx=200)
                            if kontext:
                                snippet = f"🔍 '{keyword}' gefunden:\n...{kontext}..."
                            else:
                                snippet = f"🔍 Treffer im Inhalt\nFundort: {dateipfad}"

                            self.create_snipped(
                                self.view.scrollable,
                                f"{dateiname} (im Inhalt)",
                                snippet
                            )
                            inhalt_treffer += 1
                            break  # Ein Treffer pro Datei reicht

            except Exception as e:
                # Falls Datei nicht lesbar, einfach überspringen
                print(f"⚠️ Konnte {dateipfad} nicht lesen: {e}")
                continue

        # Info anzeigen
        if hasattr(self.view, 'ergebnis_label') and self.view.ergebnis_label:
            self.view.ergebnis_label.configure(
                text=f"{namens_treffer} Treffer im Namen, {inhalt_treffer} Treffer im Inhalt",
                bootstyle="info"
            )
        else:
            print(f"✅ Suche abgeschlossen: {namens_treffer} im Namen, {inhalt_treffer} im Inhalt")

    def clear_results(self):
        """Alle Ergebnisse im Scrollbereich löschen"""
        for w in self.view.scrollable.winfo_children():
            w.destroy()

    def make_snippet(self, text, keyword, ctx=100):
        """
        Erstellt einen Snippet mit Keyword im Kontext.

        Args:
            text: Der Text, in dem gesucht wird
            keyword: Das Suchwort
            ctx: Anzahl Zeichen vor und nach dem Treffer

        Returns:
            String mit dem Kontext oder None
        """
        if not text or not keyword:
            return None

        idx = text.lower().find(keyword.lower())
        if idx == -1:
            return None

        start = max(0, idx - ctx)
        end = min(len(text), idx + len(keyword) + ctx)

        # Bereinige den Text
        kontext = text[start:end].replace("\n", " ").replace("\r", " ")
        # Entferne mehrfache Leerzeichen
        kontext = ' '.join(kontext.split())

        return kontext

    def create_snipped(self, parent, title, body):
        snipped = ttk.Frame(parent, padding=10)
        snipped.pack(fill="x", pady=6)

        title_label = ttk.Label(snipped, text=title, font=("", 14, "bold"), bootstyle="info")
        title_label.pack(anchor="w")
        title_label.visited = False

        body_label = ttk.Label(snipped, text=body, wraplength=900, style="White.TLabel")
        body_label.pack(anchor="w", pady=(4, 0))


        def on_enter(e):
            title_label.configure(font=("", 14, "bold underline"))

        def on_leave(e):
            if title_label.visited:
                title_label.configure(font=("", 14, "bold"))
            else:
                title_label.configure(bootstyle="info", font=("", 14, "bold"))

        def on_click(e):
            title_label.visited = True
            title_label.configure(bootstyle="danger", font=("", 14, "bold"))

        title_label.bind("<Enter>", on_enter)
        title_label.bind("<Leave>", on_leave)
        title_label.bind("<Button-1>", on_click)
        title_label.configure(cursor="hand2")

        for e in [snipped, body_label]:
            e.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
            e.bind("<Leave>", lambda e: e.widget.configure(cursor=""))

        return snipped

