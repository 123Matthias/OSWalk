from ensurepip import bootstrap
from textwrap import fill
import tkinter as tk
import threading
import ttkbootstrap as ttk
from Service.explorer_service import ExplorerService
from View.gui_console import GUIConsole


class MainPage:
    def __init__(self, controller):
        self.controller = controller

        self.root = ttk.Window(themename="darkly")
        self.root.title("OSWalk")
        self.root.geometry("900x700")

        self.controller.set_view(self)

        # Service-Instanz
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
        self.keywords.bind("<Return>", lambda e: self.controller.search())

        # ===== PROGRESS FRAME (Button + Progressbar inline) =====
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill="x", padx=50, pady=10)

        # Toggle-Button LINKS im Progress-Frame
        self.toggle_btn = ttk.Button(
            progress_frame,
            text="❯_",
            command=self.toggle_console,
            bootstyle="warning-outline",
            width=3
        )
        self.toggle_btn.pack(side="left", padx=(0, 5))

        # Progressbar RECHTS vom Button (nimmt restlichen Platz)
        self.progress_state = tk.DoubleVar(master=self.root, value=0)
        progress_bar = ttk.Progressbar(
            progress_frame,
            bootstyle="info-striped",
            orient="horizontal",
            variable=self.progress_state
        )
        progress_bar.pack(side="left", fill="x", expand=True)

        # Pfad-Label
        self.pfad_label = ttk.Label(self.root, text="Kein Pfad gewählt", bootstyle="light")
        self.pfad_label.pack(pady=(10, 5))

        # Button
        self.btn = ttk.Button(self.root, text="choose-path", bootstyle="darkly", command=self.controller.choose_path)
        self.btn.pack(pady=(0, 10))
        self.btn.bind("<Enter>", self._on_btn_enter)
        self.btn.bind("<Leave>", self._on_btn_leave)

        # ===== PANED WINDOW =====
        self.console_pane = ttk.Panedwindow(self.root, orient='vertical', bootstyle="darkly")
        self.console_pane.pack(fill='both', expand=True, padx=10, pady=5)
        self.console_visible = True

        # === OBERER TEIL: Results ===
        self.results_wrap = ttk.Frame(self.console_pane)
        self.console_pane.add(self.results_wrap, weight=3)

        # Canvas für Scrolling
        self.canvas = ttk.Canvas(self.results_wrap, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.results_wrap, orient="vertical", command=self.canvas.yview, bootstyle="info")
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # === UNTERER TEIL: Konsole ===
        self.console_frame = ttk.Labelframe(self.console_pane, text="Console", bootstyle="warning")
        self.console_pane.add(self.console_frame, weight=1)

        # GUIConsole
        self.console = GUIConsole(self.console_frame, height=8)
        self.console.pack(fill='both', expand=True, padx=5, pady=5)
        self.console.redirect()

        # Mausrad-Scrolling
        self._enable_mousewheel()

        self.root.mainloop()

    def _enable_mousewheel(self):
        """Mausrad-Scrolling für Canvas"""

        def on_mousewheel(event):
            # Canvas scrollen
            if event.delta:
                steps = int(-1 * (event.delta / 60))
                self.canvas.yview_scroll(steps, "units")
            elif event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
            return "break"

        # Global binden mit Positionsprüfung
        def on_global_mousewheel(event):
            mouse_x = event.x_root
            mouse_y = event.y_root

            canvas_x = self.canvas.winfo_rootx()
            canvas_y = self.canvas.winfo_rooty()
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()

            if (canvas_x <= mouse_x <= canvas_x + canvas_w and
                    canvas_y <= mouse_y <= canvas_y + canvas_h):
                return on_mousewheel(event)

        self.root.bind_all("<MouseWheel>", on_global_mousewheel)
        self.root.bind_all("<Button-4>", on_global_mousewheel)
        self.root.bind_all("<Button-5>", on_global_mousewheel)

    def toggle_console(self):
        """Nur die Konsole ein-/ausblenden, Results bleibt"""
        if self.console_visible:
            self.console_pane.forget(self.console_frame)
            self.console_visible = False
        else:
            self.console_pane.add(self.console_frame, weight=1)
            self.console_visible = True

    def add_result(self, title, body, treffer_typ):
        def _add():
            snipped = ttk.Frame(self.scrollable_frame, padding=10)
            snipped.pack(fill="x", pady=6)

            emoji = "📁" if treffer_typ == "filename" else "🔍"
            title_label = ttk.Label(snipped, text=f"{emoji} {title}",
                                   wraplength=650, font=("", 14, "bold"),
                                   bootstyle="info", anchor="w", justify="left")
            title_label.pack(fill="x", anchor="w")
            title_label.visited = False

            body_label = ttk.Label(snipped, text=body, wraplength=650,
                                  anchor="w", justify="left")
            body_label.pack(fill="x", pady=(4, 0))

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

        self.root.after(0, _add)

    def clear_results(self):
        def _clear():
            for w in self.scrollable_frame.winfo_children():
                w.destroy()
        self.root.after(0, _clear)

    def show_status(self, message, typ="info"):
        def _show():
            if hasattr(self, 'status_label'):
                self.status_label.configure(text=message, bootstyle=typ)
        self.root.after(0, _show)

    def _on_btn_enter(self, e):
        self.btn.configure(bootstyle="light")

    def _on_btn_leave(self, e):
        self.btn.configure(bootstyle="secondary")