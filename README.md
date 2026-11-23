# CMM Тех. Підтримка — HelpDesk Telegram Bot

Telegram-бот для прийому та обробки заявок технічної підтримки.

## Стек
- Python 3.12
- aiogram 3.7
- SQLite (aiosqlite)
- openpyxl
- Docker / Docker Compose

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
│   ├── models.py           # SQL схема + init_db()
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
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Запуск у Docker (рекомендовано)

Потрібні Docker і Docker Compose plugin на Linux-сервері.

```bash
git clone https://github.com/detilyganska/helpdesk-bot.git
cd helpdesk-bot
cp .env.example .env      # заповнити BOT_TOKEN, ADMIN_IDS, SUPER_ADMIN_ID, INVITE_SECRET
mkdir -p data
docker compose up -d --build
```

- Таблиці БД створюються автоматично при першому старті.
- Файл БД: `./data/helpdesk.db` — лежить на диску сервера і переживає перебудову контейнера.
- Логи: `docker compose logs -f`
- Оновлення: `git pull && docker compose up -d --build`

## Локальний запуск без Docker

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/python bot.py
```

## .env
```
BOT_TOKEN=...
ADMIN_IDS=123456789
SUPER_ADMIN_ID=123456789
INVITE_SECRET=change_me     # тільки початкове значення, далі міняється з адмін-панелі
DB_PATH=data/helpdesk.db    # у Docker перевизначається в docker-compose.yml
```
