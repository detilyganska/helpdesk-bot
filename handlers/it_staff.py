from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from keyboards.buttons import take_ticket_keyboard, close_ticket_keyboard
from database.queries import (
    get_pending_tickets, get_ticket,
    take_ticket, close_ticket,
    get_it_active_tickets
)
from notifications import notify_user_status_changed, notify_it_ticket_taken

router = Router()


# ── Пул заявок ──────────────────────────────────

@router.message(F.text == "📥 Пул заявок")
async def show_pool(message: Message, role: str):
    if role not in ("it", "admin"):
        await message.answer("⛔ Доступ заборонено.")
        return

    tickets = await get_pending_tickets()
    if not tickets:
        await message.answer("📭 Наразі нових заявок немає.")
        return

    await message.answer(f"📥 <b>Нових заявок: {len(tickets)}</b>", parse_mode="HTML")

    for t in tickets:
        date = t["created_at"].strftime("%d.%m.%Y %H:%M") if t["created_at"] else "—"
        text = (
            f"🆕 <b>Заявка #{t['id']}</b>\n"
            f"👤 {t['user_full_name']}\n"
            f"🖥 <b>Енідеск:</b> {t['enddesk']}\n"
            f"🗂 <b>Категорія:</b> {t['category']}\n"
            f"📝 {t['description']}\n"
            f"📞 <b>Контакт з ТТ:</b> {t.get('contact_tt', '—')}\n"
            f"🕐 {date}"
        )
        kb = take_ticket_keyboard(t["id"])

        if t.get("photo_file_id"):
            await message.answer_photo(
                photo=t["photo_file_id"],
                caption=text,
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            await message.answer(text, parse_mode="HTML", reply_markup=kb)


# ── Взяти в роботу ──────────────────────────────

@router.callback_query(F.data.startswith("take:"))
async def handle_take_ticket(callback: CallbackQuery, bot: Bot, role: str):
    if role not in ("it", "admin"):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[1])
    success = await take_ticket(ticket_id, callback.from_user.id)

    if not success:
        await callback.answer("⚠️ Заявку вже хтось взяв.", show_alert=True)
        return

    await callback.answer("✅ Заявку взято в роботу!")

    ticket = await get_ticket(ticket_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        f"🔧 Ви взяли заявку <b>#{ticket_id}</b> в роботу.\n"
        f"🖥 <b>Енідеск:</b> {ticket['enddesk']}",
        parse_mode="HTML",
        reply_markup=close_ticket_keyboard(ticket_id)
    )

    await notify_user_status_changed(bot, ticket_id, "in_progress")
    await notify_it_ticket_taken(bot, ticket_id, callback.from_user.id)


# ── Готово ───────────────────────────────────────

@router.callback_query(F.data.startswith("close:"))
async def handle_close_ticket(callback: CallbackQuery, bot: Bot, role: str):
    if role not in ("it", "admin"):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[1])

    # Перевіряємо що саме ця людина взяла заявку
    ticket = await get_ticket(ticket_id)
    if not ticket:
        await callback.answer("⚠️ Заявку не знайдено.", show_alert=True)
        return

    if ticket["assignee_id"] != callback.from_user.id:
        await callback.answer(
            "⛔ Ви не можете закрити цю заявку — її взяв інший спеціаліст.",
            show_alert=True
        )
        return

    success = await close_ticket(ticket_id, callback.from_user.id)
    if not success:
        await callback.answer("⚠️ Не вдалось закрити заявку.", show_alert=True)
        return

    await callback.answer("✅ Заявку закрито!")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        f"✅ Заявку <b>#{ticket_id}</b> закрито. Гарна робота!",
        parse_mode="HTML"
    )
    await notify_user_status_changed(bot, ticket_id, "done")

    # Просимо оцінку у заявника
    full_ticket = await get_ticket(ticket_id)
    if full_ticket:
        from notifications import ask_ticket_rating
        await ask_ticket_rating(
            bot, ticket_id,
            full_ticket["user_id"],
            full_ticket["category"],
            full_ticket["enddesk"]
        )


# ── Мої активні заявки ───────────────────────────

@router.message(F.text == "🔧 Мої активні заявки")
async def my_active_tickets(message: Message, role: str):
    if role not in ("it", "admin"):
        await message.answer("⛔ Доступ заборонено.")
        return

    tickets = await get_it_active_tickets(message.from_user.id)
    if not tickets:
        await message.answer("📭 У вас немає активних заявок.")
        return

    await message.answer(
        f"🔧 <b>Ваші активні заявки ({len(tickets)}):</b>",
        parse_mode="HTML"
    )

    for t in tickets:
        date = t["created_at"].strftime("%d.%m.%Y %H:%M") if t["created_at"] else "—"
        text = (
            f"<b>#{t['id']}</b> | {t['category']}\n"
            f"🖥 <b>Енідеск:</b> {t['enddesk']}\n"
            f"📝 {t['description']}\n"
            f"🕐 {date}"
        )
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=close_ticket_keyboard(t["id"])
        )
