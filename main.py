import sys
from PySide6.QtWidgets import QApplication
from Controller.main_page_controller import MainPageController
from View.main_page import MainPage
from Service.font_awesome_service import FontAwesomeService
from View.theme_manager import ThemeManager
from project_data import ProjectData
from language import Language
from View.settings_page import SettingsWindow


class Main:
    def __init__(self, my_app):  # 👈 app Parameter
        self.app = my_app

        # Settings laden
        settings = SettingsWindow()
        settings.load_settings()

        # ProjectData setzen
        ProjectData.set_settings(
            keyword_weight=settings.keyword_weight.isChecked(),
            search_depth=int(settings.search_depth.text()),
            snippet_size=int(settings.snippet_size.text()),
            default_search_path=settings.default_search_path.text(),
            language=settings.language.currentText()
        )

        # Sprache laden
        Language.load(ProjectData.language)
        print(f"✅ {Language.get('MainPage', 'noPathMessage')}")


        # Fonts
        self.font_awesome_7 = FontAwesomeService.load_font_awesome_free()
        self.python_font = FontAwesomeService.load_python_selfmade()

        # Theme
        ThemeManager().initialize(self.app)  # 👈 self.app

        # Controller
        self.main_page_controller = MainPageController()

        # MainPage erstellen und anzeigen
        self.main_page = MainPage(self.main_page_controller)
        self.main_page.show()


        print("✅ Main fertig")

    def run(self):
        return self.app.exec()  # 👈 self.app


    def load_and_reload_page(self):
        # Controller
        self.main_page_controller = MainPageController()

        # MainPage erstellen und anzeigen
        self.main_page = MainPage(self.main_page_controller)
        self.main_page.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("KeySeek")
    app.setApplicationDisplayName("KeySeek")

    main_app = Main(app)  # 👈 app übergeben
    sys.exit(main_app.run())