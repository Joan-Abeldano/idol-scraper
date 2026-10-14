import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk


class PreviewPanel(ttk.Labelframe):
    def __init__(self, master, on_download_selected, on_download_all):
        super().__init__(master, text="Photo Preview", padding=5)

        self._raw_image = None
        self._image_ref = None

        self.canvas = tk.Canvas(self, bg="#181818", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Configure>", self._on_resize)

        self.meta_label = ttk.Label(
            self, text="", font=("Segoe UI", 8), foreground="#666666", anchor=tk.CENTER
        )
        self.meta_label.pack(fill=tk.X, pady=(0, 4))

        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, pady=(2, 0))

        self.download_btn = ttk.Button(
            btn_row, text="Download Photo (Enter)", command=on_download_selected
        )
        self.download_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.download_all_btn = ttk.Button(
            btn_row, text="Download All Photos", command=on_download_all
        )
        self.download_all_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        self.show_message("Select a photo to preview")

    def show_message(self, message):
        self.canvas.delete("all")
        self._image_ref = None
        self._raw_image = None
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        self.canvas.create_text(
            width // 2, height // 2, text=message, fill="#999999", font=("Segoe UI", 10)
        )

    def show_image(self, pil_image, dimensions=None):
        self._raw_image = pil_image
        self._draw(pil_image)
        if dimensions:
            self.set_meta(f"Resolution: {dimensions[0]} × {dimensions[1]}")

    def set_meta(self, text):
        self.meta_label.configure(text=text)

    def _draw(self, pil_image):
        if not pil_image:
            return

        canvas_w = max(self.canvas.winfo_width(), 100)
        canvas_h = max(self.canvas.winfo_height(), 100)

        avail_w = max(canvas_w - 20, 50)
        avail_h = max(canvas_h - 20, 50)

        scaled = pil_image.copy()
        scaled.thumbnail((avail_w, avail_h), Image.Resampling.LANCZOS)
        photo_tk = ImageTk.PhotoImage(scaled)

        self._image_ref = photo_tk
        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_w // 2, canvas_h // 2, image=photo_tk, anchor=tk.CENTER
        )

    def _on_resize(self, event):
        if self._raw_image and event.width > 50 and event.height > 50:
            self._draw(self._raw_image)
