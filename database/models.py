"""
Запускати один раз для створення таблиць у MSSQL.
Виклик: python -m database.models
"""
import pyodbc
from config import DB_CONN_STR

SCHEMA = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
CREATE TABLE users (
    id          BIGINT PRIMARY KEY,          -- Telegram user_id
    full_name   NVARCHAR(255) NOT NULL,
    username    NVARCHAR(100),
    created_at  DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='it_staff' AND xtype='U')
CREATE TABLE it_staff (
    id          BIGINT PRIMARY KEY,          -- Telegram user_id
    full_name   NVARCHAR(255) NOT NULL,
    username    NVARCHAR(100),
    added_at    DATETIME DEFAULT GETDATE()
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='categories' AND xtype='U')
CREATE TABLE categories (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    name        NVARCHAR(100) NOT NULL
);

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='tickets' AND xtype='U')
CREATE TABLE tickets (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id),
    category_id     INT REFERENCES categories(id),
    enddesk         NVARCHAR(100),           -- Енідеск прописом
    description     NVARCHAR(MAX),
    photo_file_id   NVARCHAR(255),           -- Telegram file_id фото
    status          NVARCHAR(20) DEFAULT 'pending',  -- pending/in_progress/done
    assignee_id     BIGINT REFERENCES it_staff(id),
    created_at      DATETIME DEFAULT GETDATE(),
    updated_at      DATETIME DEFAULT GETDATE()
);

-- Початкові категорії
IF NOT EXISTS (SELECT * FROM categories)
BEGIN
    INSERT INTO categories (name) VALUES
    (N'Комп''ютер / Ноутбук'),
    (N'Принтер / Сканер'),
    (N'Мережа / Інтернет'),
    (N'Телефонія'),
    (N'Програмне забезпечення'),
    (N'Доступи / Паролі'),
    (N'Інше');
END
"""

if __name__ == "__main__":
    conn = pyodbc.connect(DB_CONN_STR)
    cursor = conn.cursor()
    for statement in SCHEMA.strip().split(";\n\n"):
        s = statement.strip()
        if s:
            cursor.execute(s)
    conn.commit()
    conn.close()
    print("Таблиці створено успішно.")


APPROVED_USERS_TABLE = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='approved_users' AND xtype='U')
CREATE TABLE approved_users (
    user_id     BIGINT PRIMARY KEY,
    approved_at DATETIME DEFAULT GETDATE()
);
"""
