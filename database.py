import aiosqlite
import logging
from datetime import datetime
from typing import Optional, List, Dict

from config import DATABASE_PATH

logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                is_blocked INTEGER DEFAULT 0,
                join_date TEXT DEFAULT (datetime('now')),
                last_active TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                added_by INTEGER,
                added_at TEXT DEFAULT (datetime('now')),
                role TEXT DEFAULT 'admin'
            );
            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_username TEXT,
                channel_name TEXT,
                is_active INTEGER DEFAULT 1,
                added_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS required_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT UNIQUE NOT NULL,
                group_username TEXT,
                group_name TEXT,
                is_active INTEGER DEFAULT 1,
                added_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                url TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                file_size INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS music_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                song_name TEXT,
                artist TEXT,
                download_id INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        defaults = [
            ("subscription_check", "true"),
            ("music_detection", "true"),
            ("similar_songs", "true"),
            ("bot_start_time", datetime.now().isoformat()),
        ]
        for key, value in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)", (key, value)
            )
        await db.commit()
    logger.info("Database initialized.")


# ── USERS ──────────────────────────────────────────────────────────────────

async def upsert_user(telegram_id: int, username: Optional[str], full_name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                last_active=datetime('now')
        """, (telegram_id, username, full_name))
        await db.commit()


async def get_user(telegram_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)) as c:
            row = await c.fetchone()
            return dict(row) if row else None


async def is_user_blocked(telegram_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT is_blocked FROM users WHERE telegram_id=?", (telegram_id,)) as c:
            row = await c.fetchone()
            return bool(row[0]) if row else False


async def block_user(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=1 WHERE telegram_id=?", (telegram_id,))
        await db.commit()


async def unblock_user(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=0 WHERE telegram_id=?", (telegram_id,))
        await db.commit()


async def get_all_users(limit: int = 0) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM users ORDER BY join_date DESC"
        if limit:
            q += f" LIMIT {limit}"
        async with db.execute(q) as c:
            return [dict(r) for r in await c.fetchall()]


async def get_users_count(period: str = "all") -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if period == "today":
            q = "SELECT COUNT(*) FROM users WHERE date(join_date)=date('now')"
        elif period == "week":
            q = "SELECT COUNT(*) FROM users WHERE join_date>=datetime('now','-7 days')"
        else:
            q = "SELECT COUNT(*) FROM users"
        async with db.execute(q) as c:
            row = await c.fetchone(); return row[0] if row else 0


async def get_active_users_today() -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE date(last_active)=date('now')") as c:
            row = await c.fetchone(); return row[0] if row else 0


async def search_user(query: str) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if query.lstrip("@").isdigit():
            async with db.execute("SELECT * FROM users WHERE telegram_id=?", (int(query.lstrip("@")),)) as c:
                row = await c.fetchone()
        else:
            async with db.execute("SELECT * FROM users WHERE username=?", (query.lstrip("@"),)) as c:
                row = await c.fetchone()
        return dict(row) if row else None


async def get_blocked_users() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_blocked=1") as c:
            return [dict(r) for r in await c.fetchall()]


# ── ADMINS ─────────────────────────────────────────────────────────────────

async def is_admin(telegram_id: int) -> bool:
    from config import SUPERADMIN_ID
    if telegram_id == SUPERADMIN_ID:
        return True
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT id FROM admins WHERE telegram_id=?", (telegram_id,)) as c:
            return await c.fetchone() is not None


async def add_admin(telegram_id: int, username: Optional[str], added_by: int, role: str = "admin"):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO admins (telegram_id, username, added_by, role) VALUES (?,?,?,?)",
            (telegram_id, username, added_by, role)
        )
        await db.commit()


async def remove_admin(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM admins WHERE telegram_id=?", (telegram_id,))
        await db.commit()


async def get_all_admins() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins ORDER BY added_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]


# ── CHANNELS / GROUPS ──────────────────────────────────────────────────────

async def add_required_channel(channel_id: str, username: Optional[str], name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO required_channels (channel_id, channel_username, channel_name) VALUES (?,?,?)",
            (channel_id, username, name)
        )
        await db.commit()


async def remove_required_channel(channel_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM required_channels WHERE channel_id=?", (channel_id,))
        await db.commit()


async def get_required_channels() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM required_channels WHERE is_active=1") as c:
            return [dict(r) for r in await c.fetchall()]


async def get_all_channels() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM required_channels") as c:
            return [dict(r) for r in await c.fetchall()]


async def toggle_channel(channel_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE required_channels SET is_active=1-is_active WHERE channel_id=?", (channel_id,))
        await db.commit()


async def add_required_group(group_id: str, username: Optional[str], name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO required_groups (group_id, group_username, group_name) VALUES (?,?,?)",
            (group_id, username, name)
        )
        await db.commit()


async def remove_required_group(group_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM required_groups WHERE group_id=?", (group_id,))
        await db.commit()


async def get_required_groups() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM required_groups WHERE is_active=1") as c:
            return [dict(r) for r in await c.fetchall()]


async def get_all_groups() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM required_groups") as c:
            return [dict(r) for r in await c.fetchall()]


async def toggle_group(group_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE required_groups SET is_active=1-is_active WHERE group_id=?", (group_id,))
        await db.commit()


# ── DOWNLOADS ──────────────────────────────────────────────────────────────

async def add_download(user_id: int, dl_type: str, url: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        c = await db.execute(
            "INSERT INTO downloads (user_id, type, url, status) VALUES ((SELECT id FROM users WHERE telegram_id=?),?,?,'pending')",
            (user_id, dl_type, url)
        )
        await db.commit()
        return c.lastrowid


async def update_download(download_id: int, status: str, file_size: int = 0):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE downloads SET status=?, file_size=? WHERE id=?", (status, file_size, download_id))
        await db.commit()


async def get_downloads_count(dl_type: str = "all") -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if dl_type == "all":
            async with db.execute("SELECT COUNT(*) FROM downloads WHERE status='completed'") as c:
                row = await c.fetchone()
        else:
            async with db.execute("SELECT COUNT(*) FROM downloads WHERE type=? AND status='completed'", (dl_type,)) as c:
                row = await c.fetchone()
        return row[0] if row else 0


async def get_user_download_count(telegram_id: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM downloads d JOIN users u ON u.id=d.user_id WHERE u.telegram_id=? AND d.status='completed'",
            (telegram_id,)
        ) as c:
            row = await c.fetchone(); return row[0] if row else 0


# ── MUSIC ──────────────────────────────────────────────────────────────────

async def add_music_search(user_id: int, song_name: str, artist: str, download_id: Optional[int] = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO music_searches (user_id, song_name, artist, download_id) VALUES ((SELECT id FROM users WHERE telegram_id=?),?,?,?)",
            (user_id, song_name, artist, download_id)
        )
        await db.commit()


async def get_music_searches_count() -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM music_searches") as c:
            row = await c.fetchone(); return row[0] if row else 0


# ── SETTINGS ───────────────────────────────────────────────────────────────

async def get_setting(key: str) -> Optional[str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key=?", (key,)) as c:
            row = await c.fetchone(); return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()


async def get_all_settings() -> Dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT key, value FROM bot_settings") as c:
            return {r[0]: r[1] for r in await c.fetchall()}
