"""
Схема БД (SQLite). Таблиці створюються автоматично при старті бота — init_db() в bot.py.
Всі дати зберігаються в локальному часі контейнера (TZ=Europe/Kyiv).
"""
import os

from config import DB_PATH, INVITE_SECRET
from database.connection import get_db

NOW = "(datetime('now','localtime'))"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,          -- Telegram user_id
    full_name   TEXT NOT NULL,
    username    TEXT,
    created_at  TIMESTAMP DEFAULT {NOW}
);

CREATE TABLE IF NOT EXISTS it_staff (
    id          INTEGER PRIMARY KEY,          -- Telegram user_id
    full_name   TEXT NOT NULL,
    username    TEXT,
    added_at    TIMESTAMP DEFAULT {NOW}
);

CREATE TABLE IF NOT EXISTS admins (
    user_id     INTEGER PRIMARY KEY,
    full_name   TEXT,
    username    TEXT,
    added_at    TIMESTAMP DEFAULT {NOW}
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    category_id     INTEGER REFERENCES categories(id),
    enddesk         TEXT,                     -- Енідеск
    description     TEXT,
    contact_tt      TEXT,
    photo_file_id   TEXT,                     -- Telegram file_id фото
    status          TEXT DEFAULT 'pending',   -- pending/in_progress/done
    assignee_id     INTEGER REFERENCES it_staff(id),
    rating          INTEGER,
    created_at      TIMESTAMP DEFAULT {NOW},
    updated_at      TIMESTAMP DEFAULT {NOW}
);

CREATE INDEX IF NOT EXISTS idx_tickets_status   ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_assignee ON tickets(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tickets_user     ON tickets(user_id);

CREATE TABLE IF NOT EXISTS approved_users (
    user_id     INTEGER PRIMARY KEY,
    approved_at TIMESTAMP DEFAULT {NOW}
);

CREATE TABLE IF NOT EXISTS banned_users (
    user_id     INTEGER PRIMARY KEY,
    reason      TEXT,
    banned_at   TIMESTAMP DEFAULT {NOW}
);

CREATE TABLE IF NOT EXISTS suspicious_attempts (
    user_id      INTEGER PRIMARY KEY,
    attempts     INTEGER NOT NULL DEFAULT 1,
    last_attempt TIMESTAMP DEFAULT {NOW}
);

-- Налаштування, які змінюються з бота (наприклад, секрет запрошення)
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);
"""

DEFAULT_CATEGORIES = [
    "Комп'ютер / Ноутбук",
    "Принтер / Сканер",
    "Мережа / Інтернет",
    "Телефонія",
    "Програмне забезпечення",
    "Доступи / Паролі",
    "Інше",
]


async def init_db():
    """Створює папку й таблиці, якщо їх ще немає. Безпечно викликати при кожному старті."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with get_db() as db:
        # WAL — читання не блокуються записом; налаштування зберігається у файлі БД
        await db.execute("PRAGMA journal_mode = WAL")
        await db.executescript(SCHEMA)

        cur = await db.execute("SELECT COUNT(*) FROM categories")
        if (await cur.fetchone())[0] == 0:
            await db.executemany(
                "INSERT INTO categories (name) VALUES (?)",
                [(name,) for name in DEFAULT_CATEGORIES],
            )

        # Початковий секрет береться з .env; далі його можна міняти з адмін-панелі
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('invite_secret', ?)",
            (INVITE_SECRET,),
        )
        await db.commit()
