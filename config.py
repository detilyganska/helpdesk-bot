import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN      = os.getenv("BOT_TOKEN")
ADMIN_IDS      = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))

# MSSQL
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME   = os.getenv("DB_NAME", "it_support")

DB_CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"Trusted_Connection=yes;"
    f"TrustServerCertificate=yes;"
)

# Секретний код реєстрації
INVITE_SECRET = os.getenv("INVITE_SECRET", "ithelp2024")
