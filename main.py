from View.main_page import PySideMainPage
from Controller.main_page_controller import MainPageController
import sys


class Main:
    def __init__(self):
        self.main_page_controller = MainPageController()
        self.main_page = PySideMainPage(self.main_page_controller)

    def run(self):
        """Startet die PySide6 App"""
        return self.main_page.run()  # Wichtig: run() aufrufen!


if __name__ == "__main__":
    main_app = Main()
    sys.exit(main_app.run())  # Hier wird der Event-Loop gestartet