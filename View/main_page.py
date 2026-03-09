import os
import sys
import threading
from curses.ascii import controlnames
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QProgressBar, QScrollArea,
    QFrame, QSplitter, QSizePolicy, QGraphicsDropShadowEffect, QSpinBox
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QObject, QTimer, Property
from PySide6.QtGui import QFont, QPalette, QColor, QIcon, QPainter, QBrush, QLinearGradient, QKeySequence, QShortcut, \
    QPixmap, QIntValidator
from PySide6.QtWidgets import QApplication

from Controller.main_page_controller import MainPageController
from Service.explorer_service import ExplorerService

from View.gui_console import GUIConsole
from View.theme_manager import ThemeManager


class AnimatedToggle(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 40)

        # RICHTIG: Als Observer registrieren
        self.theme_manager = ThemeManager()
        self.theme_manager.register_observer(self)

        # Initiale Farben
        self.colors = self.theme_manager.get_colors()
        self.update_style()

        self.setText("\uf120")

    def on_theme_changed(self):
        """Wird bei Theme-Wechsel aufgerufen"""
        self.colors = self.theme_manager.get_colors()
        self.update_style()

    def update_style(self):
        """Style mit aktuellen Farben aktualisieren"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.UI.INPUT_BG.name()};
                border: 2px solid {self.colors.UI.INPUT_BORDER.name()};
                border-radius: 20px;
                font-family: "Font Awesome 7 Free", "Font Awesome 6 Free", "FontAwesome", "Arial";
                font-size: 16px;
                color: {self.colors.Text.PRIMARY.name()};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors.UI.INPUT_BORDER.name()};
                border: 2px solid {self.colors.Primary.MAIN.name()};
            }}
            QPushButton:pressed {{
                background-color: {self.colors.UI.CARD_BG.name()};
            }}
            QPushButton:checked {{
                background-color: {self.colors.Secondary.MAIN.name()};
                border: 2px solid {self.colors.Secondary.MAIN.name()};
            }}
            QPushButton:checked:hover {{
                background-color: {self.colors.Secondary.LIGHT.name()};
                border: 2px solid {self.colors.Secondary.LIGHT.name()};
            }}
        """)


class SearchResultCard(QFrame):
    clicked = Signal(str)  # Signal mit dem Pfad

    def highlight_words(self, text: str) -> str:
        import re
        clean_text = text  # Originaltext behalten, nur markieren
        for kw in ExplorerService.Keyword_List:
            # Regex: match unabhängig von Groß-/Kleinschreibung
            # re.escape, falls Sonderzeichen im Keyword sind
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            clean_text = pattern.sub(lambda m: f'<span style="font-weight: bold">{m.group(0)}</span>', clean_text)

        return clean_text

    def __init__(self, priority, title, body, treffer_typ, rel_path, parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        self.setFrameStyle(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)
        self.rel_path = rel_path
        self.priority = priority
        self.checked = False

        # RICHTIG: Als Observer registrieren
        self.theme_manager = ThemeManager()
        self.theme_manager.register_observer(self)

        # Initiale Farben
        self.colors = self.theme_manager.get_colors()



        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Titel
        title_layout = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel") # WICHTIG wegen css selektor ID unten bei hover Card
        self.title_label.setTextFormat(Qt.RichText)
        self.title_label.setText(self.highlight_words(title))

        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # Berechne den Wert (z.B. 3/5 = 0.6)
        priority_value = self.priority / ExplorerService.Max_Priority

        # Runde auf 1 Dezimalstelle
        priority_display = round(priority_value, 1)

        self.priority_label = QLabel(f"⚡ {priority_display}")

        title_layout.addWidget(self.priority_label)

        self.badge = QLabel(treffer_typ.upper())
        title_layout.addWidget(self.badge)
        layout.addLayout(title_layout)

        # Body
        self.body_label = QLabel()
        self.body_label.setWordWrap(True)
        self.body_label.setTextFormat(Qt.RichText)
        self.body_label.setText(self.highlight_words(body))
        layout.addWidget(self.body_label)

        self.update_style() # Style Update immer am Ende

    def enterEvent(self, event):
        """Maus über der Card"""
        # Farbe je nach checked-State
        color = self.colors.Primary.CLICKED.name() if self.checked else self.colors.Primary.MAIN.name()

        self.title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {color};
            background-color: none;
            text-decoration: underline;
        """)

        super().enterEvent(event)

    def leaveEvent(self, event):
        """Maus verlässt Card"""
        # Farbe je nach checked-State
        color = self.colors.Primary.CLICKED.name() if self.checked else self.colors.Primary.MAIN.name()

        self.title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {color};
            background-color: none;
            text-decoration: none;
        """)

        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit(self.rel_path)

        # Einmal auf True setzen und nie zurück
        if not self.checked:
            self.checked = True
            self.title_label.setStyleSheet(f"""
                font-size: 16px;
                font-weight: bold;
                color: {self.colors.Primary.CLICKED.name()};
                background-color: none;
            """)

        super().mousePressEvent(event)

    def on_theme_changed(self):
        """Wird bei Theme-Wechsel aufgerufen"""
        self.colors = self.theme_manager.get_colors()
        self.update_style()

    def update_style(self):
        """Style mit aktuellen Farben aktualisieren"""
        self.setStyleSheet(f"""
            #resultCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self.colors.UI.CARD_BG_GRADIENT_START.name()}, 
                    stop:1 {self.colors.UI.CARD_BG_GRADIENT_END.name()});
                border: 1px solid {self.colors.UI.INPUT_BORDER.name()};
                border-radius: 8px;
                margin: 4px 0px;
                max-width: 1200px;
                min-width: 600px;
            }}
            
        """)


        self.title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {self.colors.Primary.MAIN.name()};
            background-color: none;
            text-decoration: none;
        """)


        # Badge (falls du einen Zugriff darauf brauchst - hier müsstest du badge als Instanzvariable speichern)
        if hasattr(self, 'badge'):
            self.badge.setStyleSheet(f"""
                background-color: none;
                color: {self.colors.Primary.MAIN.name()};
                padding: 2px 8px 2px 4px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            """)

        if hasattr(self, 'priority_label'):
            self.priority_label.setStyleSheet(f"""
                background-color: none;
                color: {self.colors.Secondary.MAIN.name()};
                padding: 2px 4px;
            
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            """)

        self.body_label.setStyleSheet(f"""
            color: {self.colors.Text.SECONDARY.name()};
            font-size: 13px;
            padding: 4px 4px;
            background-color: none;
        """)





class MainPage(QMainWindow):

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.controller.set_view(self)

        # Service-Instanz
        self.explorer_service = ExplorerService()

        # ThemeManager holen und ALS OBSERVER REGISTRIEREN
        self.theme_manager = ThemeManager()
        self.theme_manager.register_observer(self)

        # Einmal die aktuellen Farben holen
        self.colors = self.theme_manager.get_colors()

        # Fenster-Setup
        self.setWindowTitle("")
        self.setMinimumSize(1000, 700)

        # Zentrales Widget und Hauptlayout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(30, 30, 30, 30)

        # Header mit animiertem Titel
        self.setup_header(self.main_layout)

        # Fortschrittsleiste und Toggle
        self.setup_progress_section(self.main_layout)

        # Pfad-Anzeige
        self.setup_path_label(self.main_layout)

        # Haupt-Splitter für Ergebnisse und Konsole
        self.setup_main_splitter(self.main_layout)



        # Variablen für Animationen
        self.console_visible = True
        self.progress_animation = None
        self.result_count = 0

        # Keyboard Shortcuts
        self.setup_keyboard_shortcuts()

        self.update_all_widgets_style() # Alle Gui Elemente Style laden

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

        colors = ThemeManager().get_colors()
        self.key_label = QLabel("Key")

        s_label = QLabel()
        s_label.setPixmap(QPixmap("assets/img/pythonFett.png").scaled(
            36, 36,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))

        self.eek_label = QLabel("eek")


        title_layout.addWidget(self.key_label)
        title_layout.addWidget(s_label)
        title_layout.addWidget(self.eek_label)
        title_layout.addStretch()

        header_layout.addWidget(title_widget)



        # Label für Suchtiefe
        self.search_depth_label = QLabel("\ue698")
        header_layout.addWidget(self.search_depth_label)

        # Input-Feld für search_depth
        self.search_depth_input = QLineEdit()
        self.search_depth_input.setPlaceholderText("1000")
        self.search_depth_input.setToolTip("Länge der Suchtiefe in Dateien in Zeichen.\nEine Seite hat etwa 2000 Zeichen.\nWeniger Suchtiefe beschleunigt die Suche ist aber ungenauer.")
        self.search_depth_input.setAlignment(Qt.AlignCenter)
        self.search_depth_input.setFocusPolicy(Qt.ClickFocus)

        header_layout.addWidget(self.search_depth_input)

        # Lupe
        self.search_icon_keywords = QLabel("\uf002")
        self.search_icon_keywords.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.search_icon_keywords)

        # Modernes Suchfeld
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("Suche starten mit Enter")
        self.keywords_input.setMinimumHeight(40)
        self.keywords_input.setFocusPolicy(Qt.ClickFocus)


        self.keywords_input.returnPressed.connect(self.controller.search)
        header_layout.addWidget(self.keywords_input)

        # Choose Path Button mit Icon
        self.btn = QPushButton()
        self.btn.setMinimumHeight(40)

        self.btn.setText("\uf07b")
        self.btn.clicked.connect(self.controller.choose_path)
        header_layout.addWidget(self.btn)

        parent_layout.addWidget(header_widget)

    def setup_progress_section(self, parent_layout):
        """Fortschrittsleiste mit Toggle-Button und Loading-Indicator"""
        self.progress_widget = QWidget()
        self.progress_layout = QHBoxLayout(self.progress_widget)
        self.progress_layout.setSpacing(10)

        # Animierter Toggle-Button
        self.console_toggle_btn = AnimatedToggle()
        self.console_toggle_btn.setChecked(False)
        self.console_toggle_btn.toggled.connect(self.toggle_console)
        self.progress_layout.addWidget(self.console_toggle_btn)

        # Fortschrittsleiste
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(3)
        self.progress_bar.setTextVisible(False)

        # Loading-Status Label - NEU!
        self.loading_label = QLabel()  # <-- Hier muss es wieder rein!
        self.loading_label.setVisible(False)
        self.progress_layout.addWidget(self.loading_label)

        self.progress_layout.addWidget(self.progress_bar)


        parent_layout.addWidget(self.progress_widget)

    def setup_path_label(self, parent_layout):
        """Pfad-Anzeige mit gekürzte langen Pfade"""

        self.h_box_path = QHBoxLayout()
        self.h_box_path.setAlignment(Qt.AlignCenter)

        self.text_label = QLabel("Suchpfad: ")
        self.pfad_label = QLabel("Kein Pfad gewählt")



        self.h_box_path.addWidget(self.text_label)
        self.h_box_path.addWidget(self.pfad_label)
        parent_layout.addLayout(self.h_box_path)

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


        parent_layout.addWidget(self.splitter)

        self.toggle_console(False)  # Nachdem es den Splitter gibt soll er togglen damit Console unsichtbar ist.

    def setup_results_area(self):
        """Scrollbarer Bereich für Ergebnisse mit Empty State"""
        colors = ThemeManager().get_colors()
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameStyle(QFrame.NoFrame)


        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(10, 10, 10, 10)

        # Empty State Label (wird beim Hinzufügen von Ergebnissen versteckt)
        self.empty_state_label = QLabel("Noch keine Suchergebnisse...")
        self.empty_state_label.setAlignment(Qt.AlignCenter)

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

        console_layout.addWidget(console_label)

        # GUIConsole direkt einbetten
        self.console = GUIConsole(self.console_container, height=12)
        self.console.redirect()
        console_layout.addWidget(self.console)

        # Stelle sicher, dass die Console beim Schließen restored wird
        self.destroyed.connect(self.console.restore)


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
        if hasattr(self, 'loading_label'):  # <-- Sicherheitscheck
            if is_loading:
                self.loading_label.setText("🔄 Suche läuft...")  # <-- loading_label
                self.loading_label.setVisible(True)
                self.progress_bar.setValue(0)
            else:
                self.loading_label.setVisible(False)

    def show_status(self, message, typ="info"):
        """Status anzeigen (angepasst für PySide)"""
        status_text = f"[{typ.upper()}] {message}"
        print(status_text)

        if typ == "error" and hasattr(self, 'loading_label'):
            self.loading_label.setText(f"❌ {message}")  # <-- loading_label
            self.loading_label.setVisible(True)
            # Auto-hide nach 5 Sekunden
            QTimer.singleShot(5000, lambda: self.loading_label.setVisible(False))

    def add_result(self, priority, title, body, treffer_typ, abs_path):
        """Ergebnis als moderne Karte hinzufügen"""

        def _add():
            # Verstecke Empty State beim ersten Ergebnis
            if self.result_count == 0:
                self.empty_state_label.setVisible(False)

            # Erstelle Card
            card = SearchResultCard(priority, title, body, treffer_typ, abs_path)
            card.clicked.connect(lambda path=abs_path: self.open_file(path))

            # Einfach nur hinzufügen - fertig!
            self.results_layout.addWidget(card)
            self.result_count += 1

        # Thread-sichere Ausführung
        if threading.current_thread() is threading.main_thread():
            _add()
        else:
            QTimer.singleShot(0, _add)

    def refresh_results_display(self):
        """Erzwingt ein komplettes Neu-Rendern der Ergebnisse"""
        # Einfach das Layout zwingen, sich zu aktualisieren
        self.results_layout.activate()
        self.results_container.updateGeometry()
        self.results_container.repaint()
        self.results_scroll.repaint()

        # Optional: Kleines Debug
        print(f"📊 Ergebnisse neu gerendert: {self.result_count} Karten")

    def sort_results(self):
        # 1. Sammle alle Karten außer empty_state_label
        cards = []
        for i in range(self.results_layout.count()):
            widget = self.results_layout.itemAt(i).widget()
            if widget and widget != self.empty_state_label:
                cards.append(widget)

        # 2. Sortiere nach priority absteigend
        cards.sort(key=lambda c: getattr(c, 'priority', 0), reverse=True)

        # 3. Layout leeren (außer empty_state_label)
        for i in reversed(range(self.results_layout.count())):
            widget = self.results_layout.itemAt(i).widget()
            if widget and widget != self.empty_state_label:
                self.results_layout.removeWidget(widget)

        # 4. Sortierte Widgets wieder hinzufügen
        for card in cards:
            self.results_layout.addWidget(card)

    def open_file(self, path):
        import subprocess
        import platform
        from pathlib import Path
        import unicodedata
        import os

        # RICHTIG: Path-Objekt erstellen und absolut machen
        path = Path(path).resolve()  # oder .absolute()

        print(f"Absoluter Pfad: {path}")

        # Prüft ob etwas existiert (Datei ODER Verzeichnis)
        if not path.exists():
            print(f"❌ Pfad existiert nicht: {path}")
            return

        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(path)])
            elif platform.system() == "Windows":
                os.startfile(str(path))
            else:  # Linux
                subprocess.run(["xdg-open", str(path)])

            print(f"✅ Öffne: {path}")
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
        display_path = path
        self.pfad_label.setText(f"📂 {display_path}")



    # ===== ALLE UPDATE METHODEN FÜR EINZELNE WIDGETS =====

    def update_key_label_style(self):
        """Aktualisiert den Key-Label Style"""
        if hasattr(self, 'key_label'):
            self.key_label.setStyleSheet(f"""
                font-size: 36px;
                font-weight: bold;
                color: {self.colors.Primary.MAIN.name()};
                margin: 0;
                padding: 0;
            """)

    def update_eek_label_style(self):
        """Aktualisiert den Eek-Label Style"""
        if hasattr(self, 'eek_label'):
            self.eek_label.setStyleSheet(f"""
                font-size: 36px;
                font-weight: bold;
                color: {self.colors.Secondary.MAIN.name()};
                margin: 0;
                padding: 0;
            """)

    def update_search_depth_style(self):
        """Aktualisiert den Style des Suchtiefe-Eingabefelds"""

        # Label Style
        if hasattr(self, 'search_depth_label'):
            self.search_depth_label.setStyleSheet(f"""
                QLabel {{
                    font-family: 'Font Awesome 7 Free';
                    font-size: 20px;
                    background-color: none;
                }}
            """)

        # Input Field Style - angepasst an keyword_input
        if hasattr(self, 'search_depth_input'):
            self.search_depth_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.colors.UI.INPUT_BG.name()};
                    border: 2px solid {self.colors.UI.INPUT_BORDER.name()};
                    color: {self.colors.Text.PRIMARY.name()};
                    font-size: 16px;
                    padding: 10px 4px;
                    border-radius: 20px;
                    max-width: 50px;
                    
                }}
                QLineEdit:focus {{
                    border: 2px solid {self.colors.Primary.MAIN.name()};
                }}
                QLineEdit::placeholder {{
                    color: {self.colors.Text.DISABLED.name()};
                    font-style: italic;
                }}
            """)

    def update_search_icon_style(self):
        """Aktualisiert den Such-Label (Lupe) Style"""
        if hasattr(self, 'search_icon_keywords'):
            self.search_icon_keywords.setStyleSheet("""
                QLabel {
                    font-family: Font Awesome 7 Free;
                    font-size: 20px;
                }
            """)

    def update_keywords_input_style(self):
        """Aktualisiert das Suchfeld Style"""
        if hasattr(self, 'keywords_input'):
            self.keywords_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.colors.UI.INPUT_BG.name()};
                    border: 2px solid {self.colors.UI.INPUT_BORDER.name()};
                    border-radius: 20px;
                    padding: 10px 8px;
                    font-size: 16px;
                    color: {self.colors.Text.PRIMARY.name()};
                    font-family: Helvetica, Arial, sans-serif;
                }}
                QLineEdit:focus {{
                    border: 2px solid {self.colors.Primary.MAIN.name()};
                }}
            """)

    def update_path_button_style(self):
        """Aktualisiert den Path-Button Style"""
        if hasattr(self, 'btn'):
            self.btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors.UI.INPUT_BG.name()};
                    border: 2px solid {self.colors.UI.INPUT_BORDER.name()};
                    border-radius: 20px;
                    padding: 10px 20px;
                    font-size: 14px;
                    color: {self.colors.Text.PRIMARY.name()};
                    font-weight: bold;
                    font-family: "Font Awesome 7 Free";
                }}
                QPushButton:hover {{
                    background-color: {self.colors.UI.INPUT_BORDER.name()};
                    border: 2px solid {self.colors.Primary.MAIN.name()};
                    color: {self.colors.Primary.MAIN.name()};
                }}
                QPushButton:pressed {{
                    background-color: {self.colors.UI.CARD_BG.name()};
                }}
            """)

    def update_progress_bar_style(self):
        """Aktualisiert die Progress Bar Style"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.colors.UI.INPUT_BG.name()};
                    border: 1px solid {self.colors.UI.INPUT_BORDER.name()};
                    border-radius: 4px;
                    height: 5px;
                    max-height: 5px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {self.colors.Primary.MAIN.name()}, 
                        stop:1 {self.colors.Secondary.MAIN.name()});
                    border-radius: 4px;
                }}
            """)

    def update_loading_label_style(self):
        """Aktualisiert das Loading-Label Style"""
        if hasattr(self, 'loading_label'):
            self.loading_label.setStyleSheet(f"""
                color: {self.colors.Secondary.MAIN.name()};
                font-size: 12px;
                font-weight: bold;
                min-width: 150px;
            """)

    def update_text_label_style(self):
        """Aktualisiert das Text-Label (Suchpfad:) Style"""
        if hasattr(self, 'text_label'):
            self.text_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 14px;
                    padding: 0px 0px 0px 0px;
                    margin: 0px 0px 0px 0px;
                    color: {self.colors.Text.SECONDARY.name()};
                }}
            """)

    def update_pfad_label_style(self):
        """Aktualisiert das Pfad-Label Style"""
        if hasattr(self, 'pfad_label'):
            self.pfad_label.setStyleSheet(f"""
                QLabel {{
                    color: {self.colors.Text.SECONDARY.name()};
                    font-size: 14px;
                    padding: 0px 0px 0px 0px;
                    margin: 0px 0px 0px 0px;
                }}
            """)

    def update_splitter_style(self):
        """Aktualisiert den Splitter Style"""
        if hasattr(self, 'splitter'):
            self.splitter.setStyleSheet(f"""
                QSplitter::handle {{
                    background-color: {self.colors.UI.SPLITTER_HANDLE.name()};
                    border-radius: 4px;
                }}
                QSplitter::handle:hover {{
                    background-color: {self.colors.UI.SPLITTER_HANDLE_HOVER.name()};
                }}
            """)

    def update_results_scroll_style(self):
        """Aktualisiert die ScrollArea Style"""
        if hasattr(self, 'results_scroll'):
            self.results_scroll.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {self.colors.UI.CONTAINER_BG.name()};
                    border: none;
                }}
                QScrollBar:vertical {{
                    background-color: {self.colors.UI.INPUT_BG.name()};
                    width: 12px;
                    border-radius: 6px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: {self.colors.Primary.MAIN.name()};
                    border-radius: 6px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: {self.colors.Secondary.MAIN.name()};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    border: none;
                    background: none;
                }}
            """)

    def update_empty_state_label_style(self):
        """Aktualisiert das Empty-State Label Style"""
        if hasattr(self, 'empty_state_label'):
            self.empty_state_label.setStyleSheet(f"""
                color: {self.colors.Text.DISABLED.name()};
                font-size: 16px;
                padding: 40px auto;
                font-style: italic;
            """)

    def update_console_label_style(self):
        """Aktualisiert das Konsolen-Label Style"""
        if hasattr(self, 'console_container'):
            console_label = self.console_container.findChild(QLabel)
            if console_label:
                console_label.setStyleSheet(f"""
                    color: {self.colors.Secondary.MAIN.name()};
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 12px;
                    background-color: {self.colors.UI.TOOLBAR_BG.name()};
                    border-bottom: 1px solid {self.colors.UI.INPUT_BORDER.name()};
                """)

    def update_global_style(self):
        """Aktualisiert das globale Stylesheet"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors.UI.CONTAINER_BG.name()};
            }}
            QWidget {{
                background-color: {self.colors.UI.CONTAINER_BG.name()};
                color: {self.colors.Text.PRIMARY.name()};
                font-family: 'Arial', 'Helvetica', sans-serif;
            }}
            QLabel {{
                color: {self.colors.Text.PRIMARY.name()};
            }}
            QPushButton {{
                background-color: {self.colors.UI.INPUT_BG.name()};
                border: 1px solid {self.colors.UI.INPUT_BORDER.name()};
                border-radius: 4px;
                padding: 6px 12px;
                color: {self.colors.Text.PRIMARY.name()};
            }}
            QPushButton:hover {{
                background-color: {self.colors.UI.INPUT_BORDER.name()};
                border: 1px solid {self.colors.Primary.MAIN.name()};
            }}
            QPushButton:pressed {{
                background-color: {self.colors.UI.CARD_BG.name()};
            }}
        """)

    # ===== ZENTRALE UPDATE METHODE =====

    def update_all_widgets_style(self):
        """Aktualisiert ALLE Widget-Styles mit den aktuellen Farben"""
        print("🔄 Aktualisiere alle Widget-Styles...")

        # Zuerst globales Stylesheet
        self.update_global_style()


        # Dann alle Einzel-Widgets
        self.update_key_label_style()
        self.update_eek_label_style()
        self.update_search_depth_style()
        self.update_search_icon_style()
        self.update_keywords_input_style()
        self.update_path_button_style()
        self.update_progress_bar_style()
        self.update_loading_label_style()
        self.update_text_label_style()
        self.update_pfad_label_style()
        self.update_splitter_style()
        self.update_results_scroll_style()
        self.update_empty_state_label_style()
        self.update_console_label_style()

        print("✅ Alle Widget-Styles aktualisiert")

        # Debug

        print(f"✅ UI aktualisiert mit {self.theme_manager._current_theme} Theme")



    def on_theme_changed(self):
        """Wird bei Theme-Wechsel automatisch aufgerufen"""
        print("🎨 MainPage: Theme wurde geändert, aktualisiere UI...")

        # Neue Farben holen
        self.colors = self.theme_manager.get_colors()

        # ALLE Widgets updaten
        self.update_all_widgets_style()

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

    def add_result(self, title, body, treffer_typ, abs_path):
        self.window.add_result(title, body, treffer_typ, abs_path)

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