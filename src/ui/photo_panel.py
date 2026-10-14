import tkinter as tk
from tkinter import ttk


class PhotoPanel(ttk.Labelframe):
    def __init__(self, master, on_select):
        super().__init__(master, text="All Photos (0)", padding=5)

        self.listbox = tk.Listbox(self, font=("Segoe UI", 10), exportselection=False)
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", on_select)

    def clear(self):
        self.listbox.delete(0, tk.END)
        self.configure(text="All Photos (0)")

    def set_count(self, count):
        self.configure(text=f"All Photos ({count:,})")

    def append_items(self, titles):
        for title in titles:
            self.listbox.insert(tk.END, title)

    def selected_index(self):
        selection = self.listbox.curselection()
        return selection[0] if selection else None

    def select_first(self):
        if self.listbox.size() > 0:
            self.listbox.selection_set(0)

    def focus_list(self):
        self.listbox.focus_set()
