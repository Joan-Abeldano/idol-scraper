import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.status_var = tk.StringVar(value="Initializing...")
        label = ttk.Label(
            self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(10, 4)
        )
        label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.prog_bar = ttk.Progressbar(
            self, orient=tk.HORIZONTAL, mode="determinate", length=140
        )
        self.prog_bar.pack(side=tk.RIGHT, padx=5, pady=2)

    def set_status(self, text):
        self.status_var.set(text)

    def set_progress(self, value, maximum=None):
        if maximum is not None:
            self.prog_bar.configure(maximum=maximum)
        self.prog_bar.configure(value=value)

    def reset_progress(self):
        self.prog_bar.configure(value=0)
