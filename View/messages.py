from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PySide6.QtGui import QPixmap, QMovie


class Messages:

    @staticmethod
    def set_self_destroying_message(parent: QWidget, text: str, duration: int = 3000) -> None:
        colors = parent.colors

        # Container als Child-Widget
        container = QWidget(parent)

        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        # Haupt-Widget für Text + Icon
        msg_widget = QWidget()
        msg_layout = QHBoxLayout(msg_widget)
        msg_layout.setAlignment(Qt.AlignCenter)
        msg_layout.setContentsMargins(25, 20, 25, 20)
        msg_layout.setSpacing(15)

        # Icon
        icon_label = QLabel()
        python_icon = QPixmap("assets/img/pythonFett.png")
        python_icon = python_icon.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(python_icon)

        # Text
        text_label = QLabel(text)
        text_label.setWordWrap(True)

        msg_layout.addWidget(icon_label)
        msg_layout.addWidget(text_label)
        layout.addWidget(msg_widget)

        # Style
        msg_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.UI.CONTAINER_BG.name()};
                border:none;
            }}
            QLabel {{
                color: {colors.Text.PRIMARY.name()};
                font-size: 16px;
                font-weight: 500;
                border: none;
            }}
        """)

        container.show()
        container.adjustSize()

        # Zentrieren über Parent
        x = (parent.width() - container.width()) // 2
        y = (parent.height() - container.height()) // 2
        container.move(x, y)

        # Einfach nach duration löschen
        QTimer.singleShot(duration, container.deleteLater)

    def set_no_path_selected(parent, duration=500):
        """
        Macht den Path-Button und Label kurz dezent rot und setzt danach den normalen Style zurück.
        """
        btn = parent.path_btn
        path = parent.path
        colors = parent.colors

        # Dezentes Rot
        alert_color = "#d9534f"

        # Button kurz rot
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.UI.INPUT_BG.name()};
                border: 2px solid {alert_color};
                border-radius: 20px;
                padding: 10px 20px;
                font-size: 14px;
                color: {alert_color};
                font-weight: bold;
                font-family: "Font Awesome 7 Free";
            }}
        """)

        # Label kurz rot
        path.setStyleSheet(f"color: {alert_color}; font-size: 14px;")

        # Nach duration wieder normalen Style
        QTimer.singleShot(duration, parent.update_path_button_style)
        QTimer.singleShot(duration, parent.update_pfad_label_style)






    def show_caching_spinner(parent: QWidget, show: bool) -> None:
        colors = parent.colors

        if not show:
            for child in parent.findChildren(QWidget):
                if hasattr(child, "_is_caching_msg") and child._is_caching_msg:
                    if hasattr(child, "_spinner_timer"):
                        child._spinner_timer.stop()
                    child.deleteLater()
            return

        # Vorhandene entfernen
        for child in parent.findChildren(QWidget):
            if hasattr(child, "_is_caching_msg") and child._is_caching_msg:
                if hasattr(child, "_spinner_timer"):
                    child._spinner_timer.stop()
                child.deleteLater()

        container = QWidget(parent)
        container._is_caching_msg = True

        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        # Text
        text_label = QLabel("Caching file paths...")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet(f"""
        font-size: 14px;
        color: {colors.Text.PRIMARY.name()};
        border: none;
        """)

        # SPINNER - selbst gemacht mit QTimer und Unicode
        spinner_label = QLabel()
        spinner_label.setAlignment(Qt.AlignCenter)
        spinner_label.setStyleSheet(f"""
            font-size: 32px;
            color: {colors.Primary.MAIN.name()};
            border: none;
        """)

        # Spinner-Frames (verschiedene Unicode-Symbole)
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
        # Alternative: ["◴", "◷", "◶", "◵"]
        # Alternative: ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"]
        # Alternative: ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        frame_index = 0

        def update_spinner():
            nonlocal frame_index
            frame_index = (frame_index + 1) % len(frames)
            spinner_label.setText(frames[frame_index])

        spinner_timer = QTimer()
        spinner_timer.timeout.connect(update_spinner)
        spinner_timer.start(100)  # 100ms = 10fps

        container._spinner_timer = spinner_timer

        # Kleiner Hinweis
        hint_label = QLabel("This may take a moment")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet(f"""
            font-size: 12px;
            color: {colors.Text.SECONDARY.name()};
            opacity: 0.8;
            border: none;
        """)

        layout.addWidget(text_label)
        layout.addWidget(spinner_label)
        layout.addWidget(hint_label)

        container.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.UI.CONTAINER_BG.name()};
                border: 1px solid {colors.Primary.MAIN.name()};
                border-radius: 8px;
                padding: 5px 5px 5px 5px;
            }}
        """)

        container.adjustSize()
        container.show()

        x = (parent.width() - container.width()) // 2
        y = (parent.height() - container.height()) // 2
        container.move(x, y)

        QApplication.processEvents()