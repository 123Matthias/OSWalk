import os
import sys
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QProgressBar, QScrollArea,
    QFrame, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QObject, QTimer, Property
from PySide6.QtGui import QFont, QPalette, QColor, QIcon, QPainter, QBrush, QLinearGradient, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication
from Service.explorer_service import ExplorerService

from View.gui_console import GUIConsole


class AnimatedToggle(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 40)

        # Basis-Styling (ohne Farb-Animation)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2c2c2c;
                border: 2px solid #3c3c3c;
                border-radius: 20px;
                font-family: "Font Awesome 7 Free", "Font Awesome 6 Free", "FontAwesome", "Arial";
                font-size: 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
                border: 2px solid #00bc8c;
            }
            QPushButton:pressed {
                background-color: #1c1c1c;
            }
            QPushButton:checked {
                background-color: #f39c12;  /* Orange wenn aktiv */
                border: 2px solid #f39c12;
            }
            QPushButton:checked:hover {
                background-color: #e67e22;
                border: 2px solid #e67e22;
            }
        """)

        # Start-Icon: Terminal öffnen ()
        self.setText("\uf120")





class SearchResultCard(QFrame):
    """Moderne Karte für Suchergebnisse mit verbessertem Feedback"""

    clicked = Signal(str)  # Signal mit dem Pfad

    def mousePressEvent(self, event):
        # 🔥 Wenn Card geklickt wird, emittet sie den Pfad!
        self.clicked.emit(self.rel_path)
        super().mousePressEvent(event)

    def __init__(self, title, body, treffer_typ, rel_path, parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        self.setFrameStyle(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)
        self._is_pressed = False
        self.rel_path = rel_path

        # Schatten-Effekt durch Styling
        self.setStyleSheet("""
            #resultCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c2c2c, stop:1 #2a2a2a);
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                margin: 4px 0px;
            }
            #resultCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3c3c3c, stop:1 #3a3a3a);
                border: 1px solid #4c4c4c;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Icon und Titel
        title_layout = QHBoxLayout()

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #00bc8c;
            background-color: none;
        """)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # Typ-Badge
        badge = QLabel(treffer_typ.upper())
        badge.setStyleSheet(f"""
            background-color: none;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        title_layout.addWidget(badge)

        layout.addLayout(title_layout)

        # Body mit schönerer Darstellung
        body_label = QLabel(body)
        body_label.setWordWrap(True)
        body_label.setStyleSheet("""
            color: #b0b0b0;
            font-size: 13px;
            padding: 4px 0px;
            background-color: none;
        """)
        body_label.setTextFormat(Qt.PlainText)
        layout.addWidget(body_label)



class MainPage(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.controller.set_view(self)

        # Service-Instanz
        self.explorer_service = ExplorerService()

        # Fenster-Setup
        self.setWindowTitle("OSWalk")
        self.setMinimumSize(1000, 700)

        # Zentrales Widget und Hauptlayout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Header mit animiertem Titel
        self.setup_header(main_layout)

        # Fortschrittsleiste und Toggle
        self.setup_progress_section(main_layout)

        # Pfad-Anzeige
        self.setup_path_label(main_layout)

        # Haupt-Splitter für Ergebnisse und Konsole
        self.setup_main_splitter(main_layout)

        # Styling anwenden
        self.apply_modern_style()

        # Variablen für Animationen
        self.console_visible = True
        self.progress_animation = None
        self.result_count = 0

        # Keyboard Shortcuts
        self.setup_keyboard_shortcuts()

    def setup_keyboard_shortcuts(self):
        """Keyboard-Navigation einrichten"""
        # ESC zum Schließen der Konsole
        QShortcut(QKeySequence.Cancel, self, self.toggle_console_shortcut)
        # Ctrl+A zum Fokus auf Suchfeld
        QShortcut(QKeySequence(Qt.CTRL | Qt.Key_L), self, self.focus_search)

    def focus_search(self):
        """Focus auf das Suchfeld"""
        self.keywords_input.setFocus()
        self.keywords_input.selectAll()

    def toggle_console_shortcut(self):
        """Konsole via Shortcut umschalten"""
        self.console_toggle_btn.setChecked(not self.console_toggle_btn.isChecked())

    def setup_header(self, parent_layout):


        """Moderner Header mit Suchfeld"""

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setSpacing(10)

        # Animierter Titel
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setSpacing(2)
        title_layout.setContentsMargins(0, 0, 0, 0)

        os_label = QLabel("OS")
        os_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #00bc8c;
        """)

        walk_label = QLabel("Walk")
        walk_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #f39c12;
        """)

        title_layout.addWidget(os_label)
        title_layout.addWidget(walk_label)
        title_layout.addStretch()

        header_layout.addWidget(title_widget)


        #Lupe
        self.search_label = QLabel("\uf002")
        self.search_label.setFixedSize(30, 30)  # Breite/Höhe fix
        self.search_label.setAlignment(Qt.AlignCenter)
        self.search_label.setStyleSheet("""
        QLabel {
            font-family: Font Awesome 7 Free;
            font-size: 20px;
        }

        """)

        header_layout.addWidget(self.search_label)

        # Modernes Suchfeld
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("press enter")
        self.keywords_input.setMinimumHeight(40)

        self.keywords_input.setStyleSheet("""
        QLineEdit {
            background-color: #2c2c2c;
            border: 2px solid #3c3c3c;
            border-radius: 20px;
            padding: auto 8px;
            font-size: 16px;
            color: white;
            font-family: Helvetica, Arial, sans-serif;
        }
  
        QLineEdit:focus {
            border: 2px solid #00bc8c;
        }
        """)
        self.keywords_input.returnPressed.connect(self.controller.search)
        header_layout.addWidget(self.keywords_input)

        # Choose Path Button mit Icon
        self.btn = QPushButton()
        self.btn.setMinimumHeight(40)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #2c2c2c;
                border: 2px solid #3c3c3c;
                border-radius: 20px;
                padding: 8px 20px;
                font-size: 14px;
                color: white;
                font-weight: bold;
                font-family: "Font Awesome 7 Free";
            }
            QPushButton:hover {
                background-color: #3c3c3c;
                border: 2px solid #00bc8c;
                color: #00bc8c;
            }
            QPushButton:pressed {
                background-color: #1c1c1c;
            }
        """)

        self.btn.setText("\uf07b")
        self.btn.clicked.connect(self.controller.choose_path)
        header_layout.addWidget(self.btn)

        parent_layout.addWidget(header_widget)

    def setup_progress_section(self, parent_layout):
        """Fortschrittsleiste mit Toggle-Button und Loading-Indicator"""
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setSpacing(10)

        # Animierter Toggle-Button
        self.console_toggle_btn = AnimatedToggle()
        self.console_toggle_btn.setChecked(False)
        self.console_toggle_btn.toggled.connect(self.toggle_console)
        progress_layout.addWidget(self.console_toggle_btn)

        # Fortschrittsleiste
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2e2e2e;
                border: 1px solid #2c2c2c;
                border-radius: 4px;
                height: 5px;
                max-height: 5px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00bc8c, stop:1 #f39c12);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        # Loading-Status Label
        self.search_label = QLabel()
        self.search_label.setStyleSheet("""
            color: #f39c12;
            font-size: 12px;
            font-weight: bold;
            min-width: 150px;
        """)
        self.search_label.setVisible(False)
        progress_layout.addWidget(self.search_label)

        parent_layout.addWidget(progress_widget)

    def setup_path_label(self, parent_layout):
        """Pfad-Anzeige mit gekürzte langen Pfade"""
        self.pfad_label = QLabel("Kein Pfad gewählt")
        self.pfad_label.setAlignment(Qt.AlignCenter)
        self.pfad_label.setStyleSheet("""
            color: #b0b0b0;
            font-size: 14px;
            padding: 10px;
            background-color: #2c2c2c;
            border-radius: 8px;
            border-left: 3px solid #00bc8c;
        """)
        parent_layout.addWidget(self.pfad_label)

    def setup_main_splitter(self, parent_layout):
        """Splitter für Ergebnisse und Konsole"""
        self.splitter = QSplitter(Qt.Vertical)

        # Ergebnis-Bereich mit ScrollArea
        self.setup_results_area()

        # Konsolen-Bereich
        self.setup_console_area()

        self.splitter.addWidget(self.results_scroll)
        self.splitter.addWidget(self.console_container)
        self.splitter.setSizes([500, 200])
        self.splitter.setHandleWidth(8)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2c2c2c;
                border-radius: 4px;
            }
            QSplitter::handle:hover {
                background-color: #3c3c3c;
            }
        """)

        parent_layout.addWidget(self.splitter)

        self.toggle_console(False) # Nachdem es den Splitter gibt soll er togglen damit Console unsichtbar ist.

    def setup_results_area(self):
        """Scrollbarer Bereich für Ergebnisse mit Empty State"""
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameStyle(QFrame.NoFrame)
        self.results_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2c2c2c;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #00bc8c;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #f39c12;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(10, 10, 10, 10)

        # Empty State Label (wird beim Hinzufügen von Ergebnissen versteckt)
        self.empty_state_label = QLabel("🔍 Noch keine Suchergebnisse")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setStyleSheet("""
            color: #666666;
            font-size: 16px;
            padding: 40px 20px;
            font-style: italic;
        """)
        self.results_layout.addWidget(self.empty_state_label)

        self.results_scroll.setWidget(self.results_container)


    def setup_console_area(self):
        """Konsolen-Bereich mit besseres Layout"""
        self.console_container = QWidget()
        console_layout = QVBoxLayout(self.console_container)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.setSpacing(0)

        # Konsolen-Label mit Icon
        console_label = QLabel("📟 Konsole")
        console_label.setStyleSheet("""
            color: #f39c12;
            font-size: 12px;
            font-weight: bold;
            padding: 8px 12px;
            background-color: #2c2c2c;
            border-bottom: 1px solid #3c3c3c;
        """)
        console_layout.addWidget(console_label)

        # GUIConsole direkt einbetten
        self.console = GUIConsole(self.console_container, height=12)
        self.console.redirect()
        console_layout.addWidget(self.console)

        # Stelle sicher, dass die Console beim Schließen restored wird
        self.destroyed.connect(self.console.restore)

    def apply_modern_style(self):
        """Style für die gesamte App in QSS"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Arial', 'Helvetica', sans-serif;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #2c2c2c;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 6px 12px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3c3c3c;
                border: 1px solid #00bc8c;
            }
            QPushButton:pressed {
                background-color: #1c1c1c;
            }
        """)

    def toggle_console(self, checked):
        """Konsole ein-/ausblenden mit Animation"""
        if checked:
            self.splitter.widget(1).show()
            self.console_visible = True
            self.console_toggle_btn.setChecked(True)
        else:
            self.splitter.widget(1).hide()
            self.console_visible = False
            self.console_toggle_btn.setChecked(False)

    def set_search_loading(self, is_loading: bool):
        """Loading-Status anzeigen/verstecken"""
        if is_loading:
            self.search_label.setText("🔄 Suche läuft...")
            self.search_label.setVisible(True)
            self.progress_bar.setValue(0)
        else:
            self.search_label.setVisible(False)

    def add_result(self, title, body, treffer_typ, rel_pfad):
        """Ergebnis als moderne Karte hinzufügen"""

        def _add():
            # Verstecke Empty State beim ersten Ergebnis
            if self.result_count == 0:
                self.empty_state_label.setVisible(False)

            card = SearchResultCard(title, body, treffer_typ, rel_pfad)
            card.clicked.connect(lambda path: self.open_file(path))
            self.results_layout.addWidget(card)
            self.result_count += 1

        # Thread-sichere Ausführung
        if threading.current_thread() is threading.main_thread():
            _add()
        else:
            QTimer.singleShot(0, _add)

    def open_file(self, path):
        import subprocess
        import platform
        from pathlib import Path
        import unicodedata
        import os

        print(path)
        # Normalisierung direkt auf den Eingabe-String
        normalized_path = unicodedata.normalize('NFD', path)

        # Dann absoluten Pfad bauen
        abs_path = Path(normalized_path).expanduser().resolve()

        if not abs_path.is_file():
            print(f"❌ Datei existiert nicht: {abs_path}")
            return

        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", str(abs_path)])
            elif platform.system() == "Windows":
                os.startfile(str(abs_path))
            else:
                subprocess.run(["xdg-open", str(abs_path)])

            print(f"✅ Öffne Datei: {abs_path}")
        except Exception as e:
            print(f"❌ Fehler beim Öffnen: {e}")

    def clear_results(self):
        """Alle Ergebnisse löschen"""

        def _clear():
            # Lösche alle außer dem Empty State Label
            for i in reversed(range(self.results_layout.count())):
                widget = self.results_layout.itemAt(i).widget()
                if widget and widget != self.empty_state_label:
                    widget.deleteLater()

            # Zeige Empty State wieder
            self.empty_state_label.setVisible(True)
            self.result_count = 0

        if threading.current_thread() is threading.main_thread():
            _clear()
        else:
            QTimer.singleShot(0, _clear)

    def show_status(self, message, typ="info"):
        """Status anzeigen (angepasst für PySide)"""
        status_text = f"[{typ.upper()}] {message}"
        print(status_text)

        # Optional: Zeige Status in der Konsole an
        if typ == "error":
            self.search_label.setText(f"❌ {message}")
            self.search_label.setVisible(True)
            # Auto-hide nach 5 Sekunden
            QTimer.singleShot(5000, lambda: self.search_label.setVisible(False))

    def set_progress(self, value):
        """Fortschrittsbalken aktualisieren"""
        self.progress_bar.setValue(int(value))

    def update_path_label(self, path):
        """Pfad-Label aktualisieren mit gekürzte Anzeige bei langen Pfaden"""
        if len(path) > 70:
            # Zeige nur Anfang und Ende bei sehr langen Pfaden
            display_path = path[:35] + ".../" + Path(path).name
        else:
            display_path = path

        self.pfad_label.setText(f"📂 {display_path}")
        self.pfad_label.setToolTip(path)  # Full Path im Tooltip


# Für die Integration mit dem existierenden Controller
class PySideMainPage:
    """Wrapper-Klasse für nahtlose Integration"""

    def __init__(self, controller):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)

        self.window = MainPage(controller)
        self.window.show()

    def run(self):
        return self.app.exec()

    def add_result(self, title, body, treffer_typ, rel_pfad):
        self.window.add_result(title, body, treffer_typ, rel_pfad)

    def clear_results(self):
        self.window.clear_results()

    def show_status(self, message, typ="info"):
        self.window.show_status(message, typ)

    def set_progress(self, value):
        self.window.set_progress(value)

    def update_path_label(self, path):
        self.window.update_path_label(path)

    def set_search_loading(self, is_loading: bool):
        self.window.set_search_loading(is_loading)