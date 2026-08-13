import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from config import ADMIN_IDS
from database.connection import get_conn

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30 * 60   # кожні 30 хвилин
HANG_HOURS     = 4          # заявка вважається зависшою після 4 годин


async def check_hanging_tickets(bot: Bot):
    """Перевіряє заявки що висять в роботі більше HANG_HOURS годин."""
    conn = await get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, t.enddesk, t.updated_at, s.full_name "
        "FROM tickets t "
        "LEFT JOIN it_staff s ON s.id = t.assignee_id "
        "WHERE t.status = 'in_progress' "
        "AND t.updated_at <= DATEADD(hour, -?, GETDATE())",
        HANG_HOURS
    )
    tickets = [
        {"id": r[0], "enddesk": r[1], "updated_at": r[2], "assignee": r[3]}
        for r in cur.fetchall()
    ]
    conn.close()

    if not tickets:
        return

    for ticket in tickets:
        hours = int((datetime.now() - ticket["updated_at"]).total_seconds() // 3600)
        assignee = ticket["assignee"] or "невідомо"
        text = (
            f"⚠️ <b>Заявка #{ticket['id']} висить {hours} год!</b>\n\n"
            f"🖥 <b>Енідеск:</b> {ticket['enddesk']}\n"
            f"👷 <b>Виконавець:</b> {assignee}\n\n"
            f"<i>Статус: В роботі вже більше {HANG_HOURS} годин</i>"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception:
                pass


async def scheduler_loop(bot: Bot):
    """Фонова задача — запускається разом з ботом."""
    logger.info("Планувальник запущено.")
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            await check_hanging_tickets(bot)
        except Exception as e:
            logger.error(f"Помилка планувальника: {e}")
