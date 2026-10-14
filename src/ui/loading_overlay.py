import tkinter as tk
from tkinter import ttk


class LoadingOverlay(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#1a1a1a")

        box = tk.Frame(self, bg="#1a1a1a")
        box.place(relx=0.5, rely=0.5, anchor="center")

        self._message = tk.StringVar(value="Loading...")
        tk.Label(
            box,
            textvariable=self._message,
            bg="#1a1a1a",
            fg="#e6e6e6",
            font=("TkDefaultFont", 12),
        ).pack(pady=(0, 14))

        self.progress = ttk.Progressbar(box, mode="indeterminate", length=360)
        self.progress.pack()

        self._visible = False

    def show(self, message="Loading..."):
        self._message.set(message)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self.progress.start(12)
        self._visible = True
        self._try_grab()

    def _try_grab(self):
        if not self._visible:
            return
        try:
            self.grab_set()
        except tk.TclError:
            self.after(50, self._try_grab)

    def set_message(self, message):
        self._message.set(message)

    def hide(self):
        if not self._visible:
            return
        self._visible = False
        self.progress.stop()
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.place_forget()
