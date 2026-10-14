import os
import queue
import threading
import traceback
from io import BytesIO
from tkinter import messagebox, simpledialog, ttk

import tkinter as tk
from PIL import Image

from ..cache import LRUImageCache
from ..config import (
    DB_PATH,
    DOWNLOAD_ROOT,
    HEADERS,
    SEARCH_DEBOUNCE_MS,
    THUMB_CACHE_CAPACITY,
)
from ..database import DatabaseManager
from ..downloader import PhotoDownloader
from ..http import create_session
from ..scraper import EVENT_IDOLS, EVENT_STATUS, KpoppingScraper
from ..utils import sanitize_filename
from .idol_panel import IdolPanel
from .photo_panel import PhotoPanel
from .preview_panel import PreviewPanel
from .status_bar import StatusBar
from .toolbar import Toolbar


class KpoppingCompleteBrowser(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Idol photos downloader")
        self.geometry("1280x800")
        self.minsize(1050, 650)

        self.session = create_session()
        self.db = DatabaseManager(DB_PATH)
        self.scraper = KpoppingScraper(self.session, self.db)
        self.downloader = PhotoDownloader(self.session, DOWNLOAD_ROOT)

        self.all_idols = []
        self.displayed_idols = []
        self.current_photos = []

        self.active_group_filter = ""
        self._search_timer = None

        self._thumb_cache = LRUImageCache(capacity=THUMB_CACHE_CAPACITY)
        self._current_fetch_id = 0
        self._current_render_id = 0
        self._cancel_signal = threading.Event()
        self._ui_queue = queue.Queue()

        self._build_ui()
        self._bind_keys()
        self.after(50, self._drain_ui_queue)

        cached = self.db.get_all_idols()
        if cached:
            self._append_idols(cached)
            self.set_status(
                f"Loaded {len(cached):,} idols from cache"
                "Checking for updates in background..."
            )
        else:
            self.set_status("Initializing idol directory...")

        threading.Thread(target=self.load_all_idols_master, daemon=True).start()

    def _build_ui(self):
        self.toolbar = Toolbar(
            self,
            on_search_changed=self._on_search_entry_changed,
            on_group_search=self.prompt_group_search,
            on_clear_group=self.clear_group_filter,
        )
        self.toolbar.pack(fill=tk.X)

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.idol_panel = IdolPanel(paned, on_select=self.on_idol_selected)
        paned.add(self.idol_panel, weight=1)

        self.photo_panel = PhotoPanel(paned, on_select=self.on_photo_selected)
        paned.add(self.photo_panel, weight=2)

        self.preview_panel = PreviewPanel(
            paned,
            on_download_selected=self.download_selected,
            on_download_all=self.download_all_photos,
        )
        paned.add(self.preview_panel, weight=2)

        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _bind_keys(self):
        self.idol_panel.listbox.bind(
            "<Right>", lambda e: self.photo_panel.focus_list()
        )
        self.photo_panel.listbox.bind(
            "<Left>", lambda e: self.idol_panel.focus_list()
        )
        self.photo_panel.listbox.bind("<Return>", lambda e: self.download_selected())

        self.bind("<y>", self._handle_y_key)
        self.bind("<Y>", self._handle_y_key)
        self.bind("<Escape>", lambda e: self.clear_group_filter())

    def _handle_y_key(self, event):
        if isinstance(event.widget, (ttk.Entry, tk.Entry)):
            return
        self.prompt_group_search()
        return "break"

    def set_status(self, text):
        self.status_bar.set_status(text)

    def _post(self, func, *args):
        self._ui_queue.put((func, args))

    def _drain_ui_queue(self):
        while True:
            try:
                func, args = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func(*args)
            except Exception:
                traceback.print_exc()
        self.after(50, self._drain_ui_queue)

    def _on_search_entry_changed(self, *args):
        if self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(SEARCH_DEBOUNCE_MS, self.filter_idols)

    def prompt_group_search(self):
        group_query = simpledialog.askstring(
            "Search by Group",
            "Enter group name (e.g., NewJeans, BABYMONSTER, aespa):",
            initialvalue=self.active_group_filter,
            parent=self,
        )

        if group_query is None:
            return

        group_query = group_query.strip()
        if not group_query:
            self.clear_group_filter()
            return

        self.active_group_filter = group_query
        self.toolbar.show_group(group_query)
        self.filter_idols()

        if len(self.displayed_idols) == 0:
            self.set_status(f"Group '{group_query}' not found locally. Searching online...")
            threading.Thread(
                target=self._scrape_group_members_online, args=(group_query,), daemon=True
            ).start()

    def clear_group_filter(self):
        if not self.active_group_filter:
            return
        self.active_group_filter = ""
        self.toolbar.clear_group()
        self.filter_idols()
        self.set_status("Cleared group filter.")

    def _scrape_group_members_online(self, group_name):
        found_members = self.scraper.scrape_group_members(group_name)

        if found_members:
            self._post(self._append_idols, found_members)
            self._post(
                self.set_status,
                f"Discovered {len(found_members)} members for '{group_name}'",
            )
        else:
            self._post(
                self.set_status, f"No group or members found matching '{group_name}'"
            )

    def load_all_idols_master(self):
        for kind, payload in self.scraper.harvest_directory(self.all_idols):
            if kind == EVENT_STATUS:
                self._post(self.set_status, payload)
            elif kind == EVENT_IDOLS:
                self._post(self._append_idols, payload)

        self._post(
            lambda: self.set_status(
                f"Loaded all {len(self.all_idols):,} idols"
            )
        )

    def _append_idols(self, new_batch):
        is_first_load = len(self.all_idols) == 0

        existing = {item["slug"]: item for item in self.all_idols}
        for item in new_batch:
            slug = item["slug"]
            if slug not in existing:
                self.all_idols.append(item)
                existing[slug] = item
            else:
                if item.get("group") and not existing[slug].get("group"):
                    existing[slug]["group"] = item["group"]
                    existing[slug]["name"] = item["name"]

        self.all_idols.sort(key=lambda x: x["raw_name"].lower())
        self.filter_idols()

        if is_first_load and self.displayed_idols:
            self.idol_panel.select_first()
            self.idol_panel.focus_list()
            self.on_idol_selected(None)

    def filter_idols(self, *args):
        idol_query = self.toolbar.search_text().strip().lower()
        group_query = self.active_group_filter.strip().lower()

        filtered = []
        for item in self.all_idols:
            name_matches = (idol_query in item["name"].lower()) if idol_query else True

            group_matches = True
            if group_query:
                item_group = item.get("group", "").lower()
                display_label = item.get("name", "").lower()
                group_matches = (group_query in item_group) or (f"({group_query}" in display_label)

            if name_matches and group_matches:
                filtered.append(item)

        current_name = self.idol_panel.selected_name()

        self.displayed_idols = filtered
        self.idol_panel.set_items([item["name"] for item in filtered])

        total = len(self.all_idols)
        matched = len(self.displayed_idols)

        if group_query or idol_query:
            self.toolbar.set_count(f"Showing: {matched:,} of {total:,} Idols")
            self.idol_panel.set_title(f"Female Idols ({matched:,}/{total:,})")
        else:
            self.toolbar.set_count(f"Total Idols: {total:,}")
            self.idol_panel.set_title(f"Female Idols ({total:,})")

        if current_name:
            self.idol_panel.restore_selection(current_name)

    def on_idol_selected(self, event):
        index = self.idol_panel.selected_index()
        if index is None or index >= len(self.displayed_idols):
            return

        idol = self.displayed_idols[index]

        self._cancel_signal.set()
        self._cancel_signal = threading.Event()
        self._current_fetch_id += 1
        fetch_id = self._current_fetch_id
        cancel_evt = self._cancel_signal

        self.set_status(f"Loading photo archive for {idol['raw_name']}...")
        self.photo_panel.clear()
        self.current_photos.clear()
        self.preview_panel.set_meta("")
        self.preview_panel.show_message("Loading pictures...")

        threading.Thread(
            target=self._fetch_photos_worker,
            args=(idol, fetch_id, cancel_evt),
            daemon=True,
        ).start()

    def _fetch_photos_worker(self, idol, fetch_id, cancel_evt):
        def on_status(message):
            self._post(self.set_status, message)

        def on_batch(photos):
            self._post(self._append_photos, photos, fetch_id)

        def on_empty():
            self._post(self.preview_panel.show_message, "No pictures available")

        self.scraper.fetch_idol_photos(
            idol,
            cancel_evt,
            on_status=on_status,
            on_batch=on_batch,
            on_empty=on_empty,
        )

    def _append_photos(self, new_photos, fetch_id):
        if fetch_id != self._current_fetch_id:
            return

        is_first = len(self.current_photos) == 0
        self.current_photos.extend(new_photos)
        self.photo_panel.append_items([p["title"] for p in new_photos])
        self.photo_panel.set_count(len(self.current_photos))

        if is_first and len(self.current_photos) > 0:
            self.photo_panel.select_first()
            self.on_photo_selected(None)

    def on_photo_selected(self, event):
        index = self.photo_panel.selected_index()
        if index is None or index >= len(self.current_photos):
            return

        photo = self.current_photos[index]
        img_url = photo["url"]

        self._current_render_id += 1
        render_id = self._current_render_id

        cached_entry = self._thumb_cache.get(img_url)
        if cached_entry:
            raw_img, dimensions = cached_entry
            self.preview_panel.show_image(raw_img, dimensions)
            return

        self.preview_panel.show_message("Loading preview...")
        threading.Thread(
            target=self.render_thumbnail, args=(img_url, render_id), daemon=True
        ).start()

    def render_thumbnail(self, img_url, render_id):
        try:
            resp = self.session.get(img_url, headers=HEADERS, timeout=10)
            if resp.status_code != 200 or render_id != self._current_render_id:
                if render_id == self._current_render_id:
                    self._post(
                        self.preview_panel.show_message, "Preview not available"
                    )
                return

            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            orig_size = img.size
            self._thumb_cache.put(img_url, (img, orig_size))

            if render_id != self._current_render_id:
                return

            self._post(self._show_thumbnail_result, img, orig_size, render_id)
        except Exception:
            if render_id == self._current_render_id:
                self._post(
                    self.preview_panel.show_message, "Could not render preview"
                )

    def _show_thumbnail_result(self, img, orig_size, render_id):
        if render_id != self._current_render_id:
            return
        self.preview_panel.show_image(img, orig_size)

    def download_selected(self):
        index = self.photo_panel.selected_index()
        if index is None or index >= len(self.current_photos):
            messagebox.showinfo("Select Picture", "Please select a picture from the list first.")
            return

        photo = self.current_photos[index]
        default_name = sanitize_filename(photo["title"])

        custom_name = simpledialog.askstring(
            "Save Image As",
            "Enter file name for this photo:",
            initialvalue=default_name,
            parent=self,
        )

        if not custom_name:
            return

        threading.Thread(
            target=self._download_single,
            args=(photo, custom_name.strip()),
            daemon=True,
        ).start()

    def _download_single(self, photo, custom_name):
        self._post(self.set_status, f"Downloading high-res: {sanitize_filename(custom_name)}...")
        result = self.downloader.download(photo, custom_name=custom_name)

        if result.status == "saved":
            self._post(self.set_status, f"Saved: {os.path.basename(result.path)}")
        elif result.status == "exists":
            self._post(
                self.set_status, f"Already downloaded: {os.path.basename(result.path)}"
            )
        else:
            self._post(self.set_status, f"Download failed: {result.error}")

    def download_all_photos(self):
        if not self.current_photos:
            messagebox.showinfo("No Photos", "No photos available to download.")
            return

        photos_to_download = list(self.current_photos)
        threading.Thread(
            target=self._download_all_worker, args=(photos_to_download,), daemon=True
        ).start()

    def _download_all_worker(self, photos):
        total = len(photos)
        self._post(self.status_bar.set_progress, 0, total)
        self._post(self.set_status, f"Starting batch download of {total:,} photos...")

        def on_progress(done, _total, _result):
            self._post(self._on_batch_progress, done, total)

        self.downloader.download_all(photos, on_progress=on_progress)
        self._post(self._finish_batch_download, total)

    def _on_batch_progress(self, done, total):
        self.status_bar.set_progress(done)
        self.set_status(f"Downloaded {done}/{total} photos...")

    def _finish_batch_download(self, total):
        self.status_bar.reset_progress()
        self.set_status(f"Finished downloading {total:,} photos to {self.downloader.download_root}")


def main():
    app = KpoppingCompleteBrowser()
    app.mainloop()


if __name__ == "__main__":
    main()
