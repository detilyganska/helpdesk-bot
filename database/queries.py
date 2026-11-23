from database.connection import get_db

# Поточний момент у локальному часі (контейнер працює з TZ=Europe/Kyiv)
NOW = "datetime('now','localtime')"


# ──────────────────────────────────────────────
# USERS
# ──────────────────────────────────────────────

async def upsert_user(user_id: int, full_name: str, username: str | None):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, full_name, username) VALUES (?,?,?)",
            (user_id, full_name, username)
        )
        await db.commit()


# ──────────────────────────────────────────────
# IT STAFF
# ──────────────────────────────────────────────

async def get_all_it_staff() -> list[dict]:
    async with get_db() as db:
        cur = await db.execute("SELECT id, full_name, username FROM it_staff")
        return [{"id": r[0], "full_name": r[1], "username": r[2]} for r in await cur.fetchall()]


async def is_it_staff(user_id: int) -> bool:
    async with get_db() as db:
        cur = await db.execute("SELECT 1 FROM it_staff WHERE id=?", (user_id,))
        return await cur.fetchone() is not None


async def add_it_staff(user_id: int, full_name: str, username: str | None):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO it_staff (id, full_name, username) VALUES (?,?,?)",
            (user_id, full_name, username)
        )
        await db.commit()


async def remove_it_staff(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM it_staff WHERE id=?", (user_id,))
        await db.commit()


# ──────────────────────────────────────────────
# CATEGORIES
# ──────────────────────────────────────────────

async def get_categories() -> list[dict]:
    async with get_db() as db:
        cur = await db.execute("SELECT id, name FROM categories ORDER BY id")
        return [{"id": r[0], "name": r[1]} for r in await cur.fetchall()]


# ──────────────────────────────────────────────
# TICKETS
# ──────────────────────────────────────────────

async def create_ticket(
    user_id: int,
    category_id: int,
    enddesk: str,
    description: str,
    contact_tt: str,
    photo_file_id: str | None
) -> int:
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO tickets (user_id, category_id, enddesk, description, contact_tt, photo_file_id) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, category_id, enddesk, description, contact_tt, photo_file_id)
        )
        ticket_id = cur.lastrowid
        await db.commit()
        return ticket_id


async def get_pending_tickets() -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT t.id, t.enddesk, t.description, t.photo_file_id, "
            "       c.name as category, t.created_at, u.full_name "
            "FROM tickets t "
            "JOIN categories c ON c.id = t.category_id "
            "JOIN users u ON u.id = t.user_id "
            "WHERE t.status = 'pending' "
            "ORDER BY t.created_at ASC"
        )
        return [
            {
                "id": r[0], "enddesk": r[1], "description": r[2],
                "photo_file_id": r[3], "category": r[4],
                "created_at": r[5], "user_full_name": r[6]
            }
            for r in await cur.fetchall()
        ]


async def get_ticket(ticket_id: int) -> dict | None:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT t.id, t.user_id, t.enddesk, t.description, t.photo_file_id, "
            "       t.status, t.assignee_id, c.name as category, t.created_at "
            "FROM tickets t "
            "JOIN categories c ON c.id = t.category_id "
            "WHERE t.id=?",
            (ticket_id,)
        )
        r = await cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0], "user_id": r[1], "enddesk": r[2], "description": r[3],
        "photo_file_id": r[4], "status": r[5], "assignee_id": r[6],
        "category": r[7], "created_at": r[8]
    }


async def take_ticket(ticket_id: int, assignee_id: int) -> bool:
    """Повертає True якщо вдалось взяти (ще pending)."""
    async with get_db() as db:
        cur = await db.execute(
            f"UPDATE tickets SET status='in_progress', assignee_id=?, updated_at={NOW} "
            "WHERE id=? AND status='pending'",
            (assignee_id, ticket_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def close_ticket(ticket_id: int, assignee_id: int) -> bool:
    """Закрити заявку може тільки той, хто її взяв."""
    async with get_db() as db:
        cur = await db.execute(
            f"UPDATE tickets SET status='done', updated_at={NOW} "
            "WHERE id=? AND assignee_id=? AND status='in_progress'",
            (ticket_id, assignee_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def get_user_tickets(user_id: int) -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT t.id, c.name, t.status, t.created_at "
            "FROM tickets t "
            "JOIN categories c ON c.id = t.category_id "
            "WHERE t.user_id=? "
            "ORDER BY t.created_at DESC",
            (user_id,)
        )
        return [
            {"id": r[0], "category": r[1], "status": r[2], "created_at": r[3]}
            for r in await cur.fetchall()
        ]


async def get_it_active_tickets(assignee_id: int) -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT t.id, c.name, t.enddesk, t.description, t.created_at "
            "FROM tickets t "
            "JOIN categories c ON c.id = t.category_id "
            "WHERE t.assignee_id=? AND t.status='in_progress' "
            "ORDER BY t.created_at ASC",
            (assignee_id,)
        )
        return [
            {"id": r[0], "category": r[1], "enddesk": r[2],
             "description": r[3], "created_at": r[4]}
            for r in await cur.fetchall()
        ]


# ──────────────────────────────────────────────
# APPROVED USERS (whitelist через invite link)
# ──────────────────────────────────────────────

async def is_approved_user(user_id: int) -> bool:
    async with get_db() as db:
        cur = await db.execute("SELECT 1 FROM approved_users WHERE user_id=?", (user_id,))
        return await cur.fetchone() is not None


async def approve_user(user_id: int):
    async with get_db() as db:
        await db.execute("INSERT OR IGNORE INTO approved_users (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def remove_approved_user(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM approved_users WHERE user_id=?", (user_id,))
        await db.commit()


async def get_approved_users_count() -> int:
    async with get_db() as db:
        cur = await db.execute("SELECT COUNT(*) FROM approved_users")
        return (await cur.fetchone())[0]


# ──────────────────────────────────────────────
# SETTINGS (секрет запрошення тощо)
# ──────────────────────────────────────────────

async def get_setting(key: str, default: str | None = None) -> str | None:
    async with get_db() as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        r = await cur.fetchone()
    return r[0] if r else default


async def set_setting(key: str, value: str):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        await db.commit()


async def get_invite_secret() -> str:
    from config import INVITE_SECRET
    return await get_setting("invite_secret", INVITE_SECRET)


async def set_invite_secret(secret: str):
    await set_setting("invite_secret", secret)


# ──────────────────────────────────────────────
# JOURNAL / ADMIN
# ──────────────────────────────────────────────

async def get_tickets_filtered(
    status: str | None = None,
    category_id: int | None = None,
    period: str | None = None,
    offset: int = 0,
    limit: int = 10
) -> tuple[list[dict], int]:
    """Повертає (список заявок, загальна кількість)."""
    where = ["1=1"]
    params = []

    if status and status != "all":
        where.append("t.status=?")
        params.append(status)

    if category_id:
        where.append("t.category_id=?")
        params.append(category_id)

    if period == "today":
        where.append("date(t.created_at) = date('now','localtime')")
    elif period == "week":
        where.append("t.created_at >= datetime('now','localtime','-7 days')")
    elif period == "month":
        where.append("t.created_at >= datetime('now','localtime','-30 days')")

    where_str = " AND ".join(where)

    async with get_db() as db:
        # Загальна кількість
        cur = await db.execute(f"SELECT COUNT(*) FROM tickets t WHERE {where_str}", params)
        total = (await cur.fetchone())[0]

        # Сторінка
        cur = await db.execute(
            f"SELECT t.id, t.enddesk, t.status, t.created_at, "
            f"c.name as category, u.full_name as user_name "
            f"FROM tickets t "
            f"JOIN categories c ON c.id = t.category_id "
            f"JOIN users u ON u.id = t.user_id "
            f"WHERE {where_str} "
            f"ORDER BY t.created_at DESC "
            f"LIMIT ? OFFSET ?",
            [*params, limit, offset]
        )
        rows = [
            {
                "id": r[0], "enddesk": r[1], "status": r[2],
                "created_at": r[3], "category": r[4], "user_name": r[5]
            }
            for r in await cur.fetchall()
        ]
    return rows, total


async def get_full_ticket(ticket_id: int) -> dict | None:
    """Повна інформація про заявку для адміна."""
    async with get_db() as db:
        cur = await db.execute(
            "SELECT t.id, t.user_id, t.enddesk, t.description, t.contact_tt, "
            "t.photo_file_id, t.status, t.created_at, t.updated_at, "
            "c.name as category, u.full_name as user_name, u.username, "
            "s.full_name as assignee_name, t.assignee_id "
            "FROM tickets t "
            "JOIN categories c ON c.id = t.category_id "
            "JOIN users u ON u.id = t.user_id "
            "LEFT JOIN it_staff s ON s.id = t.assignee_id "
            "WHERE t.id=?",
            (ticket_id,)
        )
        r = await cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0], "user_id": r[1], "enddesk": r[2], "description": r[3],
        "contact_tt": r[4], "photo_file_id": r[5], "status": r[6],
        "created_at": r[7], "updated_at": r[8], "category": r[9],
        "user_name": r[10], "username": r[11],
        "assignee_name": r[12], "assignee_id": r[13]
    }


async def reopen_ticket(ticket_id: int) -> bool:
    """Повернути заявку в роботу."""
    async with get_db() as db:
        cur = await db.execute(
            f"UPDATE tickets SET status='in_progress', updated_at={NOW} WHERE id=?",
            (ticket_id,)
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_ticket(ticket_id: int) -> bool:
    async with get_db() as db:
        cur = await db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
        await db.commit()
        return cur.rowcount > 0


async def delete_tickets_before_date(date_str: str) -> int:
    """Видалити всі заявки старші вказаної дати (YYYY-MM-DD). Повертає кількість."""
    async with get_db() as db:
        cur = await db.execute("DELETE FROM tickets WHERE created_at < ?", (date_str,))
        await db.commit()
        return cur.rowcount


async def count_tickets_before_date(date_str: str) -> int:
    async with get_db() as db:
        cur = await db.execute("SELECT COUNT(*) FROM tickets WHERE created_at < ?", (date_str,))
        return (await cur.fetchone())[0]


# ──────────────────────────────────────────────
# RATING / REASSIGN / PROFILE
# ──────────────────────────────────────────────

async def set_ticket_rating(ticket_id: int, rating: int):
    async with get_db() as db:
        await db.execute("UPDATE tickets SET rating=? WHERE id=?", (rating, ticket_id))
        await db.commit()


async def reassign_ticket(ticket_id: int, new_assignee_id: int) -> bool:
    async with get_db() as db:
        cur = await db.execute(
            f"UPDATE tickets SET assignee_id=?, updated_at={NOW} "
            "WHERE id=? AND status='in_progress'",
            (new_assignee_id, ticket_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def get_it_staff_profile(user_id: int) -> dict | None:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT s.id, s.full_name, s.username, s.added_at, "
            "COUNT(t.id) as total_done, "
            "AVG(t.rating) as avg_rating "
            "FROM it_staff s "
            "LEFT JOIN tickets t ON t.assignee_id = s.id AND t.status='done' "
            "WHERE s.id=? "
            "GROUP BY s.id, s.full_name, s.username, s.added_at",
            (user_id,)
        )
        r = await cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0], "full_name": r[1], "username": r[2],
        "added_at": r[3], "total_done": r[4] or 0,
        "avg_rating": round(r[5], 1) if r[5] else None
    }


async def get_tickets_for_export(period: str | None = None) -> list[dict]:
    where = "1=1"
    if period == "week":
        where = "t.created_at >= datetime('now','localtime','-7 days')"
    elif period == "month":
        where = "t.created_at >= datetime('now','localtime','-30 days')"
    elif period == "year":
        where = "t.created_at >= datetime('now','localtime','-1 year')"

    async with get_db() as db:
        cur = await db.execute(
            f"SELECT t.id, u.full_name, u.username, t.enddesk, c.name, "
            f"t.description, t.contact_tt, t.status, "
            f"s.full_name as assignee, t.rating, t.created_at, t.updated_at "
            f"FROM tickets t "
            f"JOIN users u ON u.id = t.user_id "
            f"JOIN categories c ON c.id = t.category_id "
            f"LEFT JOIN it_staff s ON s.id = t.assignee_id "
            f"WHERE {where} "
            f"ORDER BY t.created_at DESC"
        )
        return [
            {
                "id": r[0], "user_name": r[1], "username": r[2],
                "enddesk": r[3], "category": r[4], "description": r[5],
                "contact_tt": r[6], "status": r[7], "assignee": r[8],
                "rating": r[9], "created_at": r[10], "updated_at": r[11]
            }
            for r in await cur.fetchall()
        ]


async def get_all_it_staff_profiles() -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT s.id, s.full_name, s.username, s.added_at, "
            "COUNT(t.id) as total_done, "
            "AVG(t.rating) as avg_rating "
            "FROM it_staff s "
            "LEFT JOIN tickets t ON t.assignee_id = s.id AND t.status='done' "
            "GROUP BY s.id, s.full_name, s.username, s.added_at "
            "ORDER BY avg_rating DESC"
        )
        return [
            {
                "id": r[0], "full_name": r[1], "username": r[2],
                "added_at": r[3], "total_done": r[4] or 0,
                "avg_rating": round(r[5], 1) if r[5] else None
            }
            for r in await cur.fetchall()
        ]


async def update_it_staff_info(user_id: int, full_name: str, username: str | None):
    async with get_db() as db:
        await db.execute(
            "UPDATE it_staff SET full_name=?, username=? WHERE id=?",
            (full_name, username, user_id)
        )
        await db.commit()


# ──────────────────────────────────────────────
# BAN SYSTEM
# ──────────────────────────────────────────────

async def ban_user(user_id: int, reason: str = "Вручну адміністратором") -> bool:
    async with get_db() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO banned_users (user_id, reason) VALUES (?,?)",
            (user_id, reason)
        )
        await db.commit()
        return cur.rowcount > 0


async def unban_user(user_id: int) -> bool:
    async with get_db() as db:
        cur = await db.execute("DELETE FROM banned_users WHERE user_id=?", (user_id,))
        await db.commit()
        return cur.rowcount > 0


async def is_banned(user_id: int) -> bool:
    async with get_db() as db:
        cur = await db.execute("SELECT 1 FROM banned_users WHERE user_id=?", (user_id,))
        return await cur.fetchone() is not None


async def get_banned_users() -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT b.user_id, u.full_name, u.username, b.reason, b.banned_at "
            "FROM banned_users b "
            "LEFT JOIN users u ON u.id = b.user_id "
            "ORDER BY b.banned_at DESC"
        )
        return [
            {
                "user_id": r[0], "full_name": r[1] or "Невідомо",
                "username": r[2], "reason": r[3], "banned_at": r[4]
            }
            for r in await cur.fetchall()
        ]


async def find_user_by_username(username: str) -> dict | None:
    username = username.lstrip("@")
    async with get_db() as db:
        cur = await db.execute(
            "SELECT id, full_name, username FROM users WHERE username=?", (username,)
        )
        r = await cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "full_name": r[1], "username": r[2]}


# ──────────────────────────────────────────────
# ADMINS TABLE
# ──────────────────────────────────────────────

async def get_admin_ids_from_db() -> list[int]:
    async with get_db() as db:
        cur = await db.execute("SELECT user_id FROM admins")
        return [r[0] for r in await cur.fetchall()]


async def get_all_admins() -> list[dict]:
    async with get_db() as db:
        cur = await db.execute(
            "SELECT user_id, full_name, username, added_at FROM admins ORDER BY added_at"
        )
        return [
            {"id": r[0], "full_name": r[1], "username": r[2], "added_at": r[3]}
            for r in await cur.fetchall()
        ]


async def add_admin(user_id: int, full_name: str, username: str | None):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, full_name, username) VALUES (?,?,?)",
            (user_id, full_name, username)
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


# ──────────────────────────────────────────────
# SUSPICIOUS ATTEMPTS
# ──────────────────────────────────────────────

async def add_suspicious_attempt(user_id: int) -> int:
    """Додає спробу і повертає загальну кількість."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO suspicious_attempts (user_id) VALUES (?) "
            f"ON CONFLICT(user_id) DO UPDATE SET attempts = attempts + 1, last_attempt = {NOW}",
            (user_id,)
        )
        await db.commit()
        cur = await db.execute("SELECT attempts FROM suspicious_attempts WHERE user_id=?", (user_id,))
        return (await cur.fetchone())[0]


async def get_suspicious_attempts(user_id: int) -> int:
    async with get_db() as db:
        cur = await db.execute("SELECT attempts FROM suspicious_attempts WHERE user_id=?", (user_id,))
        r = await cur.fetchone()
    return r[0] if r else 0


async def reset_suspicious_attempts(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM suspicious_attempts WHERE user_id=?", (user_id,))
        await db.commit()
