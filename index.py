import ttkbootstrap as ttk
from tkinter import filedialog
import os

class MeineApp:
    def __init__(self):
        self.root = ttk.Window(themename="darkly")
        self.root.title("Meine schöne App")
        
        btn = ttk.Button(
            self.root, 
            text="öffnen",
            bootstyle="primary",
            command=self.datei_oeffnen
        )
        btn.pack(pady=50, padx=50)
        
        self.root.mainloop()
    
    def datei_oeffnen(self):
        datei = filedialog.askopenfilename(
            initialdir=os.path.expanduser("~/Downloads")
        )
        if datei:
            print(f"Zugriff erlaubt auf: {datei}")

if __name__ == "__main__":
    MeineApp()