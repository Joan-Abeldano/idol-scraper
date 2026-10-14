import tkinter as tk
from tkinter import ttk


class IdolPanel(ttk.Labelframe):
    def __init__(self, master, on_select):
        super().__init__(master, text="Female Idols (0)", padding=5)

        self.listbox = tk.Listbox(self, font=("Segoe UI", 10), exportselection=False)
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", on_select)

    def set_items(self, names):
        self.listbox.delete(0, tk.END)
        for name in names:
            self.listbox.insert(tk.END, name)

    def set_title(self, text):
        self.configure(text=text)

    def selected_index(self):
        selection = self.listbox.curselection()
        return selection[0] if selection else None

    def selected_name(self):
        index = self.selected_index()
        return self.listbox.get(index) if index is not None else None

    def select_first(self):
        if self.listbox.size() > 0:
            self.listbox.selection_set(0)

    def restore_selection(self, name):
        for i in range(self.listbox.size()):
            if self.listbox.get(i) == name:
                self.listbox.selection_set(i)
                break

    def focus_list(self):
        self.listbox.focus_set()
