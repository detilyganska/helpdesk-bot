from aiogram import Bot
from database.queries import get_all_it_staff, get_ticket
from keyboards.buttons import take_ticket_keyboard, close_ticket_keyboard

STATUS_LABELS = {
    "pending":     "⏳ Очікується",
    "in_progress": "🔧 В роботі",
    "done":        "✅ Готово",
}


async def notify_it_new_ticket(bot: Bot, ticket: dict):
    """Розсилає всім ІТ спеціалістам сповіщення про нову заявку."""
    staff = await get_all_it_staff()
    if not staff:
        return

    # Формуємо контакт заявника
    if ticket.get("username"):
        contact = (
            f"@{ticket['username']} "
            f"(<a href='tg://user?id={ticket['user_id']}'>{ticket['user_full_name']}</a>)"
        )
    else:
        contact = f"<a href='tg://user?id={ticket['user_id']}'>{ticket['user_full_name']}</a>"

    text = (
        f"🆕 <b>Нова заявка #{ticket['id']}</b>\n\n"
        f"👤 <b>Від:</b> {contact}\n"
        f"🖥 <b>Єндеск:</b> {ticket['enddesk']}\n"
        f"🗂 <b>Категорія:</b> {ticket['category']}\n"
        f"📝 <b>Опис:</b> {ticket['description']}\n"
        f"📞 <b>Контакт з ТТ:</b> {ticket.get('contact_tt', '—')}"
    )

    for member in staff:
        try:
            if ticket.get("photo_file_id"):
                await bot.send_photo(
                    chat_id=member["id"],
                    photo=ticket["photo_file_id"],
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=take_ticket_keyboard(ticket["id"])
                )
            else:
                await bot.send_message(
                    chat_id=member["id"],
                    text=text,
                    parse_mode="HTML",
                    reply_markup=take_ticket_keyboard(ticket["id"])
                )
        except Exception:
            pass  # Якщо ІТ не запустив бота — ігноруємо


async def notify_user_status_changed(bot: Bot, ticket_id: int, new_status: str):
    """Сповіщає заявника про зміну статусу."""
    ticket = await get_ticket(ticket_id)
    if not ticket:
        return

    label = STATUS_LABELS.get(new_status, new_status)
    text = (
        f"📬 <b>Статус вашої заявки #{ticket_id} змінено</b>\n\n"
        f"🗂 <b>Категорія:</b> {ticket['category']}\n"
        f"🖥 <b>Єндеск:</b> {ticket['enddesk']}\n"
        f"🔄 <b>Новий статус:</b> {label}"
    )

    try:
        await bot.send_message(
            chat_id=ticket["user_id"],
            text=text,
            parse_mode="HTML"
        )
    except Exception:
        pass


async def notify_it_ticket_taken(bot: Bot, ticket_id: int, taken_by_id: int):
    """
    Повідомляє всіх інших ІТ спеціалістів, що заявку вже взяли,
    щоб прибрати кнопку 'Взяти в роботу'.
    """
    staff = await get_all_it_staff()
    ticket = await get_ticket(ticket_id)
    if not ticket:
        return

    text = (
        f"ℹ️ Заявку <b>#{ticket_id}</b> "
        f"(<i>{ticket['category']}</i>) вже взято в роботу."
    )

    for member in staff:
        if member["id"] == taken_by_id:
            continue
        try:
            await bot.send_message(
                chat_id=member["id"],
                text=text,
                parse_mode="HTML"
            )
        except Exception:
            pass


async def ask_ticket_rating(bot: Bot, ticket_id: int, user_id: int, category: str, enddesk: str):
    """Просить заявника оцінити виконання."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text=f"{'⭐'*i}", callback_data=f"rate:{ticket_id}:{i}")
    builder.adjust(5)

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🌟 <b>Оцініть виконання заявки #{ticket_id}</b>\n\n"
                f"🗂 {category}\n"
                f"🖥 Енідеск: {enddesk}\n\n"
                f"Ваша оцінка допоможе покращити якість роботи ІТ відділу:"
            ),
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    except Exception:
        pass


async def notify_reassigned(bot: Bot, ticket: dict, old_assignee_id: int, new_assignee_id: int):
    """Сповіщення при перепризначенні заявки."""
    from keyboards.buttons import close_ticket_keyboard

    # Старому виконавцю
    try:
        await bot.send_message(
            chat_id=old_assignee_id,
            text=(
                f"ℹ️ Заявку <b>#{ticket['id']}</b> передано іншому спеціалісту.\n"
                f"🖥 Енідеск: {ticket['enddesk']}"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Новому виконавцю
    try:
        await bot.send_message(
            chat_id=new_assignee_id,
            text=(
                f"📋 <b>Вам передано заявку #{ticket['id']}!</b>\n\n"
                f"🖥 <b>Енідеск:</b> {ticket['enddesk']}\n"
                f"🗂 <b>Категорія:</b> {ticket['category']}\n"
                f"📝 {ticket['description']}\n"
                f"📞 <b>Контакт з ТТ:</b> {ticket.get('contact_tt') or '—'}"
            ),
            parse_mode="HTML",
            reply_markup=close_ticket_keyboard(ticket["id"])
        )
    except Exception:
        pass
