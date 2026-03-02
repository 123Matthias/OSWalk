"""
Minimale GUI-Konsole für print-Ausgaben
"""

import sys
import threading
from tkinter import scrolledtext


class GUIConsole:
    """Leitet print-Ausgaben in ein Tkinter Text-Widget um"""

    def __init__(self, parent, height=10):
        self.parent = parent
        self.original_stdout = sys.stdout
        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.running = True

        # Text-Widget erstellen
        self.text_widget = scrolledtext.ScrolledText(
            parent,
            height=height,
            state='disabled',
            bg='black',
            fg='lightgreen',
            font=(' ', 10),  # Speziell für Code, viel Platz
            spacing2 = 5,
            spacing3=5,
            wrap='word',
        )

        # Queue-Verarbeitung starten
        self._start_processing()

    def _start_processing(self):
        """Verarbeitet den Ausgabepuffer im Hauptthread"""

        def process():
            if not self.running:
                return

            with self.buffer_lock:
                if self.buffer:
                    self.text_widget.configure(state='normal')
                    for text in self.buffer:
                        self.text_widget.insert('end', text)
                    self.text_widget.see('end')
                    self.text_widget.configure(state='disabled')
                    self.buffer.clear()

            self.parent.after(100, process)

        self.parent.after(100, process)

    def write(self, text):
        """Wird von print aufgerufen"""
        with self.buffer_lock:
            self.buffer.append(text)
        self.original_stdout.write(text)

    def flush(self):
        """Wird von print benötigt"""
        pass

    def redirect(self):
        """Leitet print um"""
        sys.stdout = self

    def restore(self):
        """Stellt originales print wieder her"""
        sys.stdout = self.original_stdout
        self.running = False

    def pack(self, **kwargs):
        """Widget anzeigen"""
        self.text_widget.pack(**kwargs)

    def grid(self, **kwargs):
        """Widget anzeigen"""
        self.text_widget.grid(**kwargs)

    def clear(self):
        """Konsole leeren"""
        self.text_widget.configure(state='normal')
        self.text_widget.delete(1.0, 'end')
        self.text_widget.configure(state='disabled')