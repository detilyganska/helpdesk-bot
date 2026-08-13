# CMM Тех. Підтримка — HelpDesk Telegram Bot

Telegram-бот для прийому та обробки заявок технічної підтримки.

## Стек
- Python 3.11
- aiogram 3.7
- MSSQL (pyodbc)
- openpyxl

## Ролі
- **Суперадмін** — повний доступ, управління адмінами
- **Адмін** — журнал, бан-лист, експорт, управління ІТ
- **ІТ спеціаліст** — пул заявок, профіль
- **Користувач** — подача заявок (тільки за invite link)

## Структура
```
helpdesk_bot/
├── bot.py                  # точка входу
├── config.py               # налаштування
├── states.py               # FSM стани
├── validators.py           # валідація вводу + автобан
├── notifications.py        # сповіщення
├── scheduler.py            # фонові задачі
├── database/
│   ├── connection.py
│   ├── models.py           # SQL схема
│   └── queries.py          # всі запити
├── handlers/
│   ├── user.py             # flow користувача
│   ├── it_staff.py         # flow ІТ спеціаліста
│   ├── admin.py            # адмін-панель
│   ├── superadmin.py       # управління адмінами
│   ├── journal.py          # журнал заявок
│   ├── profile.py          # профілі ІТ
│   ├── export.py           # експорт в Excel
│   └── ban.py              # бан-система
├── keyboards/
│   └── buttons.py
├── middlewares/
│   └── role.py
└── requirements.txt
```

## Встановлення

1. Встановити Python 3.11
2. Встановити ODBC Driver 17 for SQL Server
3. Створити БД в MSSQL і виконати `database/models.py`
4. Скопіювати `.env.example` → `.env` і заповнити
5. Створити venv і встановити залежності:
```bash
py -3.11 -m venv venv
venv\Scripts\pip install -r requirements.txt
```
6. Запустити:
```bash
venv\Scripts\python bot.py
```

## .env
```
BOT_TOKEN=...
ADMIN_IDS=123456789
SUPER_ADMIN_ID=123456789
DB_SERVER=localhost
DB_NAME=it_support
INVITE_SECRET=ithelp2024
```
