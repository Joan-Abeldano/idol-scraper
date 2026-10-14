# Idol Scraper

A small toolfor browsing the https://kpopping.com and downloading photos of kpop idols to pc.

## Using the tool

The window has three panes:

1. **Female Idols** (left) — the idol list.
2. **Photos** (middle) — every photo found for the selected idol.
3. **Preview** (right) — a preview of the selected photo.

- **Search an idol** — type in the *Search Idol* box (filters as you type).
- **Search a group** — press **`Y`** (or click *Search Group*). Enter a group name
  (e.g. `NewJeans`, `aespa`). Matches from the local list are shown immediately;
  if nothing matches, the app looks the group up on Kpopping and adds its members.
  After results appear, focus returns to the idol list.
- **Clear a group filter** — press **`Esc`** or click *✕ Clear Group*.
- **Browse** — **`↑`/`↓`** in the idol list, **`→`** to move to the photos pane,
  **`←`** to go back.
- **Download one photo** — select it and press **`Enter`** (or the download
  button), then name the file.
- **Download all photos of an idol** — use the *Download all* action in the
  preview pane; progress is shown in the status bar.

Downloaded photos are saved to the `kpop_downloaded/` folder (created next to the
app / project root).

## About `kpop_cache.db` (the cache)

`kpop_cache.db` is a small **SQLite database that stores the idol directory** —
each idol's slug, name, group, profile URL, and internal UUID. It lives next to
the app (or in `KPOP_DATA_DIR`, see below).

Why it exists:

- **Speed.** Building the directory means requesting ~28 pages from Kpopping
  (the `num`/`A`–`Z` sections plus sitemaps), and the very first request also pays
  a one-time DNS/connection warmup that can take ~10 seconds. The cache turns that
  into an instant startup.
- **Fewer requests.** The cached UUID is reused so the app doesn't have to
  re-discover each idol's ID before fetching photos.

Think of it as a local snapshot of the directory — not of the photos themselves.
Deleting a downloaded photo does not touch the cache, and clearing the cache does
not delete downloaded photos.

To force a fresh directory scan, **delete `kpop_cache.db`** and start the app
again.

By Gallet4
