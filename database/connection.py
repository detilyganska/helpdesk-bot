import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite

from config import DB_PATH


def _parse_timestamp(value: bytes):
    """SQLite зберігає дати як текст — перетворюємо назад у datetime,
    щоб хендлери могли викликати .strftime() як раніше з MSSQL."""
    text = value.decode()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return text


# Колонки з типом TIMESTAMP автоматично повертаються як datetime
sqlite3.register_converter("TIMESTAMP", _parse_timestamp)


@asynccontextmanager
async def get_db():
    """Відкриває з'єднання з SQLite і закриває його після блоку `async with`."""
    async with aiosqlite.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA busy_timeout = 5000")
        yield db
