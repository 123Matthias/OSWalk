import ttkbootstrap as ttk
from Controller.main_page_controller import MainPageController
from Service.explorer_service import ExplorerService


class MainPage:
    def __init__(self):
        self.root = ttk.Window(themename="darkly")
        self.root.title("OSWalk")

        # Controller-Instanz erstellen und View referenzieren
        self.controller = MainPageController(self)

        # Service-Instanz für spätere Nutzung
        self.explorer_service = ExplorerService()

        # Header
        self.header = ttk.Frame(self.root)
        self.header.pack(padx=(50, 50), pady=(40, 10), fill="x")

        self.title_os = ttk.Label(self.header, text="OS", font=("", 32, "bold"), bootstyle="info")
        self.title_os.pack(side="left", padx=(0, 2))

        self.title_walk = ttk.Label(self.header, text="Walk", font=("", 32, "bold"), bootstyle="warning")
        self.title_walk.pack(side="left", padx=(0, 12))

        self.keywords = ttk.Entry(self.header, bootstyle="light", font=("", 16))
        self.keywords.pack(side="left", fill="x", expand=True)
        self.keywords.bind("<Return>", lambda e: self.controller.suchen(e))

        # Pfad-Label
        self.pfad_label = ttk.Label(self.root, text="Kein Pfad gewählt", bootstyle="light")
        self.pfad_label.pack(pady=(10, 5))

        self.btn = ttk.Button(self.root, text="choose-path", command=self.controller.choose_path)
        self.btn.pack(pady=(0, 10))

        # ===== Results (Scroll-Container) mit Canvas =====
        self.results_wrap = ttk.Frame(self.root)
        self.results_wrap.pack(fill="both", expand=True, padx=50, pady=(10, 20))

        # Canvas für Scrolling
        self.canvas = ttk.Canvas(self.results_wrap, highlightthickness=0)

        # Scrollbar - STANDARD SQUARE DESIGN (kein bootstyle = default square)
        self.scrollbar = ttk.Scrollbar(self.results_wrap, orient="vertical", command=self.canvas.yview)

        # Frame für Snippets (wird in Canvas eingebettet)
        self.scrollable = ttk.Frame(self.canvas)

        # Canvas und Scrollbar verbinden
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Scrollable Frame in Canvas einbetten
        self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")

        # Bei Größenänderung des Frames den Scrollbereich anpassen
        self.scrollable.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Packen
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self._enable_mousewheel()
        self.root.mainloop()

    def _enable_mousewheel(self):
        """Mausrad-Scrolling für normale Mäuse (Windows/Linux/macOS mit Rad)"""

        def on_mousewheel(event):
            # Normale Maus: delta = 120, 240, ...
            if event.delta:
                # Sanftes Scrollen: 120/40 = 3 Schritte pro Raste
                steps = int(-1 * (event.delta / 40))
                self.canvas.yview_scroll(steps, "units")

            # Linux Fallback
            elif event.num == 4:
                self.canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(3, "units")

            return "break"

        # Nur Standard-Mausrad-Events binden
        self.root.bind_all("<MouseWheel>", on_mousewheel)  # Windows/
        self.root.bind_all("<Button-4>", on_mousewheel)  # Linux hoch
        self.root.bind_all("<Button-5>", on_mousewheel)  # Linux runter

        print("🖱️ Mausrad-Scrolling für normale Mäuse aktiviert")


