"""
Minimale GUI-Konsole für print-Ausgaben
"""

import sys
import threading
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont, QTextCursor, QColor, QPalette


class GUIConsole(QWidget):
    """Leitet print-Ausgaben in ein PySide6 Text-Widget um"""

    def __init__(self, parent=None, height=10):
        super().__init__(parent)
        self.parent = parent
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.running = True

        # Layout erstellen
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Text-Widget erstellen
        self.text_widget = QTextEdit()
        self.text_widget.setReadOnly(True)

        # Höhe basierend auf Zeilen (ungefähr)
        line_height = 20  # Pixel pro Zeile (ungefähr)
        self.text_widget.setMinimumHeight(height * line_height)
        self.text_widget.setMaximumHeight(height * line_height * 1.5)

        # Word Wrap aktivieren
        self.text_widget.setLineWrapMode(QTextEdit.WidgetWidth)

        # Monospace Font für Code-Darstellung
        font = QFont("Monaco", 10)  # Verwende Monaco auf Mac, sonst Courier
        font.setStyleHint(QFont.Monospace)
        self.text_widget.setFont(font)

        # Dark Theme mit grüner Schrift (wie im Original)
        palette = self.text_widget.palette()
        palette.setColor(QPalette.Base, QColor(0, 0, 0))      # Schwarzer Hintergrund
        palette.setColor(QPalette.Text, QColor(144, 238, 144))  # Hellgrüne Schrift (lightgreen)
        self.text_widget.setPalette(palette)

        # Zeilenabstand erhöhen (entspricht spacing2 und spacing3 im Original)
        # QTextEdit hat keinen direkten Line Spacing, daher über Stylesheet
        self.text_widget.setStyleSheet("""
            QTextEdit {
                line-height: 150%;
                padding: 5px;
            }
        """)

        layout.addWidget(self.text_widget)

        # Queue-Verarbeitung starten
        self._start_processing()

    def _start_processing(self):
        """Verarbeitet den Ausgabepuffer im Hauptthread"""

        def process():
            if not self.running:
                return

            with self.buffer_lock:
                if self.buffer:
                    # Text einfügen (immer im normalen Modus, da readonly erst nachher)
                    cursor = self.text_widget.textCursor()
                    cursor.movePosition(QTextCursor.End)
                    for text in self.buffer:
                        cursor.insertText(text)

                    # Zum Ende scrollen (entspricht see('end'))
                    self.text_widget.setTextCursor(cursor)
                    self.text_widget.ensureCursorVisible()

                    self.buffer.clear()

            # QTimer.singleShot ist der Ersatz für after() in tkinter
            QTimer.singleShot(2000, process)

        # Ersten Aufruf starten
        QTimer.singleShot(2000, process)

    def write(self, text):
        """Wird von print aufgerufen"""
        with self.buffer_lock:
            self.buffer.append(text)
        self.original_stdout.write(text)

    def flush(self):
        """Wird von print benötigt"""
        # In Qt nicht nötig, aber für Kompatibilität
        pass

    def redirect(self):
        """Leitet print um"""
        sys.stdout = self
        sys.stderr = self  # Auch stderr umleiten

    def restore(self):
        """Stellt originales print wieder her"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.running = False

    def pack(self, **kwargs):
        """Widget anzeigen - für Kompatibilität mit tkinter-Code"""
        # In Qt wird show() verwendet, aber wir lassen es als no-op
        self.show()
        # Wenn expand=True, dann Layout entsprechend anpassen
        if kwargs.get('fill', None) == 'both' or kwargs.get('expand', False):
            # In Qt passiert das über Layouts, nicht hier
            pass

    def grid(self, **kwargs):
        """Widget anzeigen - für Kompatibilität mit tkinter-Code"""
        self.show()

    def clear(self):
        """Konsole leeren"""
        self.text_widget.clear()

    def closeEvent(self, event):
        """Beim Schließen der Console"""
        self.restore()
        event.accept()