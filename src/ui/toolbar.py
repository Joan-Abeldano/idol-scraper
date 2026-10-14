import tkinter as tk
from tkinter import ttk


class Toolbar(ttk.Frame):
    def __init__(self, master, on_search_changed, on_group_search, on_clear_group):
        super().__init__(master, padding=(10, 8))

        ttk.Label(self, text="Search Idol:").pack(side=tk.LEFT, padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", on_search_changed)
        self.search_entry = ttk.Entry(self, textvariable=self.search_var, width=22)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))

        self.group_btn = ttk.Button(self, text="Search Group [Y]", command=on_group_search)
        self.group_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.group_badge = ttk.Label(
            self, text="", font=("Segoe UI", 9, "bold"), foreground="#d946ef"
        )
        self.group_badge.pack(side=tk.LEFT, padx=(0, 6))

        self.clear_group_btn = ttk.Button(self, text="✕ Clear Group", command=on_clear_group)

        self.count_var = tk.StringVar(value="Total Idols: 0")
        self.count_badge = ttk.Label(
            self,
            textvariable=self.count_var,
            font=("Segoe UI", 10, "bold"),
            foreground="#0066cc",
        )
        self.count_badge.pack(side=tk.LEFT, padx=(10, 15))

        ttk.Label(
            self,
            text="[Y] Group Search | [↑/↓] Browse | [Tab]/[→] Panes | [Enter] Name & Download",
            font=("Segoe UI", 9, "italic"),
        ).pack(side=tk.RIGHT)

    def search_text(self):
        return self.search_var.get()

    def set_count(self, text):
        self.count_var.set(text)

    def show_group(self, name):
        self.group_badge.configure(text=f"Group: {name}")
        self.clear_group_btn.pack(side=tk.LEFT, padx=(0, 6), before=self.count_badge)

    def clear_group(self):
        self.group_badge.configure(text="")
        self.clear_group_btn.pack_forget()
