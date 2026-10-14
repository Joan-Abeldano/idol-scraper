import sqlite3
import threading

from .config import DB_PATH


class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()
        self._init_db()

    def _get_connection(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=20.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._local.conn = conn
        return conn

    def _init_db(self):
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idols (
                    slug TEXT PRIMARY KEY,
                    raw_name TEXT,
                    display_name TEXT,
                    url TEXT,
                    uuid TEXT,
                    group_name TEXT
                )
                """
            )
            conn.commit()

    def get_all_idols(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT slug, raw_name, display_name, url, uuid, group_name "
                "FROM idols ORDER BY raw_name COLLATE NOCASE ASC"
            )
            rows = cursor.fetchall()
            return [
                {
                    "slug": r[0],
                    "raw_name": r[1],
                    "name": r[2],
                    "url": r[3],
                    "uuid": r[4],
                    "group": r[5] or "",
                }
                for r in rows
            ]

    def save_idols_batch(self, idols_list):
        rows = [
            {
                "slug": item["slug"],
                "raw_name": item["raw_name"],
                "name": item["name"],
                "url": item["url"],
                "uuid": item.get("uuid"),
                "group": item.get("group", ""),
            }
            for item in idols_list
        ]
        if not rows:
            return
        with self._lock, self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO idols (slug, raw_name, display_name, url, uuid, group_name)
                VALUES (:slug, :raw_name, :name, :url, :uuid, :group)
                ON CONFLICT(slug) DO UPDATE SET
                    group_name = CASE WHEN excluded.group_name != '' THEN excluded.group_name ELSE idols.group_name END,
                    display_name = excluded.display_name
                """,
                rows,
            )
            conn.commit()

    def update_uuid(self, slug, uuid):
        with self._lock, self._get_connection() as conn:
            conn.execute("UPDATE idols SET uuid = ? WHERE slug = ?", (uuid, slug))
            conn.commit()

    def clear(self):
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM idols")
            conn.commit()
