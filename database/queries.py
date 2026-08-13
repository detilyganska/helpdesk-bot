import asyncio
from database.connection import get_conn


# ──────────────────────────────────────────────
# USERS
# ──────────────────────────────────────────────

async def upsert_user(user_id: int, full_name: str, username: str | None):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "IF NOT EXISTS (SELECT 1 FROM users WHERE id=?) "
        "INSERT INTO users (id, full_name, username) VALUES (?,?,?)",
        user_id, user_id, full_name, username
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# IT STAFF
# ──────────────────────────────────────────────

async def get_all_it_staff() -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, full_name, username FROM it_staff")
    rows = [{"id": r[0], "full_name": r[1], "username": r[2]} for r in cur.fetchall()]
    conn.close()
    return rows


async def is_it_staff(user_id: int) -> bool:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM it_staff WHERE id=?", user_id)
    result = cur.fetchone() is not None
    conn.close()
    return result


async def add_it_staff(user_id: int, full_name: str, username: str | None):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "IF NOT EXISTS (SELECT 1 FROM it_staff WHERE id=?) "
        "INSERT INTO it_staff (id, full_name, username) VALUES (?,?,?)",
        user_id, user_id, full_name, username
    )
    conn.commit()
    conn.close()


async def remove_it_staff(user_id: int):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM it_staff WHERE id=?", user_id)
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# CATEGORIES
# ──────────────────────────────────────────────

async def get_categories() -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY id")
    rows = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    conn.close()
    return rows


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
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tickets (user_id, category_id, enddesk, description, contact_tt, photo_file_id) "
        "OUTPUT INSERTED.id "
        "VALUES (?,?,?,?,?,?)",
        user_id, category_id, enddesk, description, contact_tt, photo_file_id
    )
    ticket_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return ticket_id


async def get_pending_tickets() -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, t.enddesk, t.description, t.photo_file_id, "
        "       c.name as category, t.created_at, u.full_name "
        "FROM tickets t "
        "JOIN categories c ON c.id = t.category_id "
        "JOIN users u ON u.id = t.user_id "
        "WHERE t.status = 'pending' "
        "ORDER BY t.created_at ASC"
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "id": r[0], "enddesk": r[1], "description": r[2],
            "photo_file_id": r[3], "category": r[4],
            "created_at": r[5], "user_full_name": r[6]
        })
    conn.close()
    return rows


async def get_ticket(ticket_id: int) -> dict | None:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, t.user_id, t.enddesk, t.description, t.photo_file_id, "
        "       t.status, t.assignee_id, c.name as category, t.created_at "
        "FROM tickets t "
        "JOIN categories c ON c.id = t.category_id "
        "WHERE t.id=?",
        ticket_id
    )
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0], "user_id": r[1], "enddesk": r[2], "description": r[3],
        "photo_file_id": r[4], "status": r[5], "assignee_id": r[6],
        "category": r[7], "created_at": r[8]
    }


async def take_ticket(ticket_id: int, assignee_id: int) -> bool:
    """Повертає True якщо вдалось взяти (ще pending)."""
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET status='in_progress', assignee_id=?, updated_at=GETDATE() "
        "WHERE id=? AND status='pending'",
        assignee_id, ticket_id
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


async def close_ticket(ticket_id: int, assignee_id: int) -> bool:
    """Закрити заявку може тільки той, хто її взяв."""
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET status='done', updated_at=GETDATE() "
        "WHERE id=? AND assignee_id=? AND status='in_progress'",
        ticket_id, assignee_id
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


async def get_user_tickets(user_id: int) -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, c.name, t.status, t.created_at "
        "FROM tickets t "
        "JOIN categories c ON c.id = t.category_id "
        "WHERE t.user_id=? "
        "ORDER BY t.created_at DESC",
        user_id
    )
    rows = [
        {"id": r[0], "category": r[1], "status": r[2], "created_at": r[3]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


async def get_it_active_tickets(assignee_id: int) -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, c.name, t.enddesk, t.description, t.created_at "
        "FROM tickets t "
        "JOIN categories c ON c.id = t.category_id "
        "WHERE t.assignee_id=? AND t.status='in_progress' "
        "ORDER BY t.created_at ASC",
        assignee_id
    )
    rows = [
        {"id": r[0], "category": r[1], "enddesk": r[2],
         "description": r[3], "created_at": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


# ──────────────────────────────────────────────
# APPROVED USERS (whitelist через invite link)
# ──────────────────────────────────────────────

async def is_approved_user(user_id: int) -> bool:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM approved_users WHERE user_id=?", user_id)
    result = cur.fetchone() is not None
    conn.close()
    return result


async def approve_user(user_id: int):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "IF NOT EXISTS (SELECT 1 FROM approved_users WHERE user_id=?) "
        "INSERT INTO approved_users (user_id) VALUES (?)",
        user_id, user_id
    )
    conn.commit()
    conn.close()


async def remove_approved_user(user_id: int):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM approved_users WHERE user_id=?", user_id)
    conn.commit()
    conn.close()


async def get_approved_users_count() -> int:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM approved_users")
    count = cur.fetchone()[0]
    conn.close()
    return count


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
    conn = await get_conn()
    cur = conn.cursor()

    where = ["1=1"]
    params = []

    if status and status != "all":
        where.append("t.status=?")
        params.append(status)

    if category_id:
        where.append("t.category_id=?")
        params.append(category_id)

    if period == "today":
        where.append("CAST(t.created_at AS DATE) = CAST(GETDATE() AS DATE)")
    elif period == "week":
        where.append("t.created_at >= DATEADD(day, -7, GETDATE())")
    elif period == "month":
        where.append("t.created_at >= DATEADD(day, -30, GETDATE())")

    where_str = " AND ".join(where)

    # Загальна кількість
    cur.execute(
        f"SELECT COUNT(*) FROM tickets t WHERE {where_str}",
        *params
    )
    total = cur.fetchone()[0]

    # Сторінка
    cur.execute(
        f"SELECT t.id, t.enddesk, t.status, t.created_at, "
        f"c.name as category, u.full_name as user_name "
        f"FROM tickets t "
        f"JOIN categories c ON c.id = t.category_id "
        f"JOIN users u ON u.id = t.user_id "
        f"WHERE {where_str} "
        f"ORDER BY t.created_at DESC "
        f"OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        *params, offset, limit
    )
    rows = [
        {
            "id": r[0], "enddesk": r[1], "status": r[2],
            "created_at": r[3], "category": r[4], "user_name": r[5]
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows, total


async def get_full_ticket(ticket_id: int) -> dict | None:
    """Повна інформація про заявку для адміна."""
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, t.user_id, t.enddesk, t.description, t.contact_tt, "
        "t.photo_file_id, t.status, t.created_at, t.updated_at, "
        "c.name as category, u.full_name as user_name, u.username, "
        "s.full_name as assignee_name, t.assignee_id "
        "FROM tickets t "
        "JOIN categories c ON c.id = t.category_id "
        "JOIN users u ON u.id = t.user_id "
        "LEFT JOIN it_staff s ON s.id = t.assignee_id "
        "WHERE t.id=?",
        ticket_id
    )
    r = cur.fetchone()
    conn.close()
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
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET status='in_progress', updated_at=GETDATE() "
        "WHERE id=?",
        ticket_id
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


async def delete_ticket(ticket_id: int) -> bool:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM tickets WHERE id=?", ticket_id)
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


async def delete_tickets_before_date(date_str: str) -> int:
    """Видалити всі заявки старші вказаної дати. Повертає кількість."""
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tickets WHERE created_at < ?", date_str
    )
    count = cur.fetchone()[0]
    cur.execute("DELETE FROM tickets WHERE created_at < ?", date_str)
    conn.commit()
    conn.close()
    return count


async def count_tickets_before_date(date_str: str) -> int:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tickets WHERE created_at < ?", date_str
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


# ──────────────────────────────────────────────
# RATING / REASSIGN / PROFILE
# ──────────────────────────────────────────────

async def set_ticket_rating(ticket_id: int, rating: int):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET rating=? WHERE id=?",
        rating, ticket_id
    )
    conn.commit()
    conn.close()


async def reassign_ticket(ticket_id: int, new_assignee_id: int) -> bool:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET assignee_id=?, updated_at=GETDATE() "
        "WHERE id=? AND status='in_progress'",
        new_assignee_id, ticket_id
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


async def get_it_staff_profile(user_id: int) -> dict | None:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT s.id, s.full_name, s.username, s.added_at, "
        "COUNT(t.id) as total_done, "
        "AVG(CAST(t.rating AS FLOAT)) as avg_rating "
        "FROM it_staff s "
        "LEFT JOIN tickets t ON t.assignee_id = s.id AND t.status='done' "
        "WHERE s.id=? "
        "GROUP BY s.id, s.full_name, s.username, s.added_at",
        user_id
    )
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0], "full_name": r[1], "username": r[2],
        "added_at": r[3], "total_done": r[4] or 0,
        "avg_rating": round(r[5], 1) if r[5] else None
    }


async def get_tickets_for_export(period: str | None = None) -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()

    where = "1=1"
    params = []
    if period == "week":
        where = "t.created_at >= DATEADD(day, -7, GETDATE())"
    elif period == "month":
        where = "t.created_at >= DATEADD(day, -30, GETDATE())"
    elif period == "year":
        where = "t.created_at >= DATEADD(year, -1, GETDATE())"

    cur.execute(
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
    rows = []
    for r in cur.fetchall():
        rows.append({
            "id": r[0], "user_name": r[1], "username": r[2],
            "enddesk": r[3], "category": r[4], "description": r[5],
            "contact_tt": r[6], "status": r[7], "assignee": r[8],
            "rating": r[9], "created_at": r[10], "updated_at": r[11]
        })
    conn.close()
    return rows


async def get_all_it_staff_profiles() -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT s.id, s.full_name, s.username, s.added_at, "
        "COUNT(t.id) as total_done, "
        "AVG(CAST(t.rating AS FLOAT)) as avg_rating "
        "FROM it_staff s "
        "LEFT JOIN tickets t ON t.assignee_id = s.id AND t.status='done' "
        "GROUP BY s.id, s.full_name, s.username, s.added_at "
        "ORDER BY avg_rating DESC"
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "id": r[0], "full_name": r[1], "username": r[2],
            "added_at": r[3], "total_done": r[4] or 0,
            "avg_rating": round(r[5], 1) if r[5] else None
        })
    conn.close()
    return rows


async def update_it_staff_info(user_id: int, full_name: str, username: str | None):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE it_staff SET full_name=?, username=? WHERE id=?",
        full_name, username, user_id
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# BAN SYSTEM
# ──────────────────────────────────────────────

async def ban_user(user_id: int, reason: str = "Вручну адміністратором") -> bool:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "IF NOT EXISTS (SELECT 1 FROM banned_users WHERE user_id=?) "
        "INSERT INTO banned_users (user_id, reason) VALUES (?,?)",
        user_id, user_id, reason
    )
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0


async def unban_user(user_id: int) -> bool:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM banned_users WHERE user_id=?", user_id)
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0


async def is_banned(user_id: int) -> bool:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM banned_users WHERE user_id=?", user_id)
    result = cur.fetchone() is not None
    conn.close()
    return result


async def get_banned_users() -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT b.user_id, u.full_name, u.username, b.reason, b.banned_at "
        "FROM banned_users b "
        "LEFT JOIN users u ON u.id = b.user_id "
        "ORDER BY b.banned_at DESC"
    )
    rows = [
        {
            "user_id": r[0], "full_name": r[1] or "Невідомо",
            "username": r[2], "reason": r[3], "banned_at": r[4]
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


async def find_user_by_username(username: str) -> dict | None:
    conn = await get_conn()
    cur = conn.cursor()
    username = username.lstrip("@")
    cur.execute(
        "SELECT id, full_name, username FROM users WHERE username=?", username
    )
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {"id": r[0], "full_name": r[1], "username": r[2]}


# ──────────────────────────────────────────────
# ADMINS TABLE
# ──────────────────────────────────────────────

async def get_admin_ids_from_db() -> list[int]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins")
    ids = [r[0] for r in cur.fetchall()]
    conn.close()
    return ids


async def get_all_admins() -> list[dict]:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, full_name, username, added_at FROM admins ORDER BY added_at")
    rows = [
        {"id": r[0], "full_name": r[1], "username": r[2], "added_at": r[3]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


async def add_admin(user_id: int, full_name: str, username: str | None):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "IF NOT EXISTS (SELECT 1 FROM admins WHERE user_id=?) "
        "INSERT INTO admins (user_id, full_name, username) VALUES (?,?,?)",
        user_id, user_id, full_name, username
    )
    conn.commit()
    conn.close()


async def remove_admin(user_id: int):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM admins WHERE user_id=?", user_id)
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# SUSPICIOUS ATTEMPTS
# ──────────────────────────────────────────────

async def increment_suspicious_attempts(user_id: int) -> int:
    """Збільшує лічильник підозрілих спроб. Повертає поточну кількість."""
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "IF EXISTS (SELECT 1 FROM suspicious_attempts WHERE user_id=?) "
        "UPDATE suspicious_attempts SET attempts = attempts + 1, last_attempt = GETDATE() WHERE user_id=? "
        "ELSE INSERT INTO suspicious_attempts (user_id) VALUES (?)",
        user_id, user_id, user_id
    )
    conn.commit()
    cur.execute("SELECT attempts FROM suspicious_attempts WHERE user_id=?", user_id)
    attempts = cur.fetchone()[0]
    conn.close()
    return attempts


async def reset_suspicious_attempts(user_id: int):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM suspicious_attempts WHERE user_id=?", user_id)
    conn.commit()
    conn.close()


async def get_suspicious_attempts(user_id: int) -> int:
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("SELECT attempts FROM suspicious_attempts WHERE user_id=?", user_id)
    r = cur.fetchone()
    conn.close()
    return r[0] if r else 0


# ──────────────────────────────────────────────
# SUSPICIOUS ATTEMPTS
# ──────────────────────────────────────────────

async def add_suspicious_attempt(user_id: int) -> int:
    """Додає спробу і повертає загальну кількість."""
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "IF EXISTS (SELECT 1 FROM suspicious_attempts WHERE user_id=?) "
        "UPDATE suspicious_attempts SET attempts = attempts + 1, last_attempt = GETDATE() WHERE user_id=? "
        "ELSE INSERT INTO suspicious_attempts (user_id) VALUES (?)",
        user_id, user_id, user_id
    )
    conn.commit()
    cur.execute("SELECT attempts FROM suspicious_attempts WHERE user_id=?", user_id)
    attempts = cur.fetchone()[0]
    conn.close()
    return attempts


async def reset_suspicious_attempts(user_id: int):
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM suspicious_attempts WHERE user_id=?", user_id)
    conn.commit()
    conn.close()
