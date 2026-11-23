import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN      = os.getenv("BOT_TOKEN")
ADMIN_IDS      = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))

# SQLite — шлях до файлу БД (у Docker: /app/data/helpdesk.db, папка data/ монтується з хоста)
DB_PATH = os.getenv("DB_PATH", "data/helpdesk.db")

# Початковий секретний код реєстрації — використовується лише при першому старті.
# Далі секрет зберігається в БД (таблиця settings) і міняється з адмін-панелі.
INVITE_SECRET = os.getenv("INVITE_SECRET", "ithelp2024")
