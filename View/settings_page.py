import os, json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QCheckBox, QComboBox
from chardet.metadata import languages

from project_data import ProjectData


def get_settings_path():
    home = os.path.expanduser("~")
    settings_dir = os.path.join(home, "keysearch_app_settings")
    os.makedirs(settings_dir, exist_ok=True)
    return os.path.join(settings_dir, "settings.json")


class SettingsWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()
        form = QFormLayout()

        # Eingabefelder
        self.keyword_weight = QCheckBox("Aktiv")
        self.search_depth = QLineEdit("4000")
        self.snippet_size = QLineEdit("250")
        self.default_search_path = QLineEdit("~")
        self.language = QComboBox()

        # Clear existing items first (optional)
        self.language.clear()

        # Get all files in the languages directory
        language_files = os.listdir("./assets/languages/")

        # Add each filename without extension
        for filename in language_files:
            # Get filename without extension
            name_without_ext = os.path.splitext(filename)[0]
            self.language.addItem(name_without_ext)

        form.addRow("Gewichtung Keywords", self.keyword_weight)
        form.addRow("Default Suchtiefe", self.search_depth)
        form.addRow("Snippet Größe", self.snippet_size)
        form.addRow("Default Suchpfad", self.default_search_path)
        form.addRow("Sprache", self.language)

        layout.addLayout(form)

        save_btn = QPushButton("Speichern")
        save_btn.clicked.connect(self.save_settings)

        layout.addWidget(save_btn)
        self.setLayout(layout)

        self.load_settings()  # beim Start laden

    def save_settings(self):
        data = {
            "keyword_weight": self.keyword_weight.isChecked(),
            "search_depth": self.search_depth.text(),
            "snippet_size": self.snippet_size.text(),
            "default_search_path": self.default_search_path.text(),
            "language": self.language.currentText(),
        }
        with open(get_settings_path(), "w") as f:
            json.dump(data, f, indent=4)
        self.close()  # Fenster schließen
        ProjectData.set_settings(
            keyword_weight=self.keyword_weight.isChecked(),
            search_depth=int(self.search_depth.text()),
            snippet_size=int(self.snippet_size.text()),
            default_search_path=self.default_search_path.text(),
            language=self.language.currentText(),
        )

    def load_settings(self):
        path = get_settings_path()
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                self.keyword_weight.setChecked(data.get("keyword_weight", False))
                self.search_depth.setText(data.get("search_depth", 4000))
                self.snippet_size.setText(data.get("snippet_size", 250))
                self.default_search_path.setText(data.get("default_search_path", "~"))
                self.language.setCurrentText(data.get("language", "English"))