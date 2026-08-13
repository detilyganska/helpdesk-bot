from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import JournalForm, CleanupForm, ReOpenForm
from database.queries import (
    get_tickets_filtered, get_full_ticket, get_categories,
    reopen_ticket, delete_ticket,
    delete_tickets_before_date, count_tickets_before_date
)
from notifications import notify_user_status_changed

router = Router()

PAGE_SIZE = 10

STATUS_LABELS = {
    "pending":     "⏳ Очікується",
    "in_progress": "🔧 В роботі",
    "done":        "✅ Готово",
    "all":         "📋 Всі",
}

PERIOD_LABELS = {
    "today": "Сьогодні",
    "week":  "Тиждень",
    "month": "Місяць",
    "all":   "Всі",
}


def filter_keyboard(status: str, period: str, page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Фільтр статус
    for s, label in [("all","📋 Всі"),("pending","⏳"),("in_progress","🔧"),("done","✅")]:
        mark = "•" if s == status else ""
        builder.button(text=f"{mark}{label}", callback_data=f"jf:status:{s}")
    builder.adjust(4)

    # Фільтр період
    for p, label in [("all","Всі"),("today","Сьогодні"),("week","Тиждень"),("month","Місяць")]:
        mark = "•" if p == period else ""
        builder.button(text=f"{mark}{label}", callback_data=f"jf:period:{p}")
    builder.adjust(4)

    # Навігація
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"jf:page:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="jf:noop"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"jf:page:{page+1}"))
    builder.row(*nav)

    return builder.as_markup()


def ticket_list_keyboard(tickets: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tickets:
        status_icon = {"pending": "⏳", "in_progress": "🔧", "done": "✅"}.get(t["status"], "❓")
        builder.button(
            text=f"{status_icon} #{t['id']} | {t['enddesk']} | {t['category']}",
            callback_data=f"jt:detail:{t['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


async def show_journal(message_or_cb, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    status    = data.get("j_status", "all")
    period    = data.get("j_period", "all")
    page      = data.get("j_page", 0)

    tickets, total = await get_tickets_filtered(
        status=status if status != "all" else None,
        period=period if period != "all" else None,
        offset=page * PAGE_SIZE,
        limit=PAGE_SIZE
    )

    if not tickets:
        text = "📭 Заявок не знайдено за вибраними фільтрами."
    else:
        lines = [f"📊 <b>Журнал заявок</b> | Всього: {total}\n"]
        for t in tickets:
            date = t["created_at"].strftime("%d.%m %H:%M") if t["created_at"] else "—"
            status_icon = {"pending": "⏳", "in_progress": "🔧", "done": "✅"}.get(t["status"], "❓")
            lines.append(f"{status_icon} <b>#{t['id']}</b> | {t['enddesk']} | {t['category']} | {date}")
        text = "\n".join(lines)

    kb_filters = filter_keyboard(status, period, page, total)
    kb_tickets = ticket_list_keyboard(tickets) if tickets else None

    if isinstance(message_or_cb, CallbackQuery):
        msg = message_or_cb.message
    else:
        msg = message_or_cb

    await msg.answer(text, parse_mode="HTML", reply_markup=kb_filters)
    if kb_tickets:
        await msg.answer("👇 Оберіть заявку для деталей:", reply_markup=kb_tickets)


# ── Відкрити журнал ──────────────────────────────

@router.message(F.text == "📊 Журнал заявок")
async def open_journal(message: Message, state: FSMContext, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return
    await state.set_state(JournalForm.browsing)
    await state.update_data(j_status="all", j_period="all", j_page=0)
    await show_journal(message, state)


# ── Фільтри ──────────────────────────────────────

@router.callback_query(F.data.startswith("jf:"))
async def journal_filter(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    parts = callback.data.split(":")
    action = parts[1]

    if action == "noop":
        await callback.answer()
        return

    if action == "status":
        await state.update_data(j_status=parts[2], j_page=0)
    elif action == "period":
        await state.update_data(j_period=parts[2], j_page=0)
    elif action == "page":
        await state.update_data(j_page=int(parts[2]))

    await callback.answer()
    await show_journal(callback, state)


# ── Деталі заявки ────────────────────────────────

@router.callback_query(F.data.startswith("jt:detail:"))
async def ticket_detail(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[2])
    t = await get_full_ticket(ticket_id)
    if not t:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    status_label = STATUS_LABELS.get(t["status"], t["status"])
    created = t["created_at"].strftime("%d.%m.%Y %H:%M") if t["created_at"] else "—"
    updated = t["updated_at"].strftime("%d.%m.%Y %H:%M") if t["updated_at"] else "—"
    assignee = t["assignee_name"] or "не призначено"
    username = f"@{t['username']}" if t["username"] else "—"

    rating_str = "⭐" * t["rating"] + "☆" * (5 - t["rating"]) if t.get("rating") else "немає оцінки"

    text = (
        f"📋 <b>Заявка #{t['id']}</b>\n\n"
        f"👤 <b>Від:</b> {t['user_name']} ({username})\n"
        f"🖥 <b>Енідеск:</b> {t['enddesk']}\n"
        f"🗂 <b>Категорія:</b> {t['category']}\n"
        f"📝 <b>Опис:</b> {t['description']}\n"
        f"📞 <b>Контакт з ТТ:</b> {t.get('contact_tt') or '—'}\n"
        f"👷 <b>Виконавець:</b> {assignee}\n"
        f"🔄 <b>Статус:</b> {status_label}\n"
        f"⭐ <b>Оцінка:</b> {rating_str}\n"
        f"📅 <b>Створено:</b> {created}\n"
        f"🕐 <b>Оновлено:</b> {updated}"
    )

    builder = InlineKeyboardBuilder()
    if t["status"] == "done":
        builder.button(text="🔄 Повернути в роботу", callback_data=f"jt:reopen:{ticket_id}")
    if t["status"] == "in_progress":
        builder.button(text="👷 Передати спеціалісту", callback_data=f"jt:reassign:{ticket_id}")
    builder.button(text="🗑 Видалити заявку", callback_data=f"jt:delete:{ticket_id}")
    builder.button(text="◀️ Назад до списку", callback_data="jt:back")
    builder.adjust(1)

    if t.get("photo_file_id"):
        await callback.message.answer_photo(
            photo=t["photo_file_id"],
            caption=text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    await callback.answer()


# ── Повернути в роботу ───────────────────────────

@router.callback_query(F.data.startswith("jt:reopen:"))
async def reopen_ticket_handler(callback: CallbackQuery, bot: Bot, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[2])
    t = await get_full_ticket(ticket_id)

    success = await reopen_ticket(ticket_id)
    if not success:
        await callback.answer("⚠️ Не вдалось повернути заявку.", show_alert=True)
        return

    await callback.answer("✅ Заявку повернено в роботу!")
    await callback.message.answer(f"✅ Заявку <b>#{ticket_id}</b> повернено в роботу.", parse_mode="HTML")

    # Сповіщення виконавцю
    if t and t.get("assignee_id"):
        try:
            from keyboards.buttons import close_ticket_keyboard
            await bot.send_message(
                chat_id=t["assignee_id"],
                text=(
                    f"⚠️ <b>Заявку #{ticket_id} повернено в роботу адміністратором!</b>\n\n"
                    f"🖥 <b>Енідеск:</b> {t['enddesk']}\n"
                    f"🗂 <b>Категорія:</b> {t['category']}\n\n"
                    f"<i>Перевірте та виправте виконання.</i>"
                ),
                parse_mode="HTML",
                reply_markup=close_ticket_keyboard(ticket_id)
            )
        except Exception:
            pass

    # Сповіщення заявнику
    await notify_user_status_changed(bot, ticket_id, "in_progress")


# ── Видалити заявку ──────────────────────────────

@router.callback_query(F.data.startswith("jt:delete:"))
async def delete_ticket_confirm(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[2])
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Так, видалити", callback_data=f"jt:delete_ok:{ticket_id}")
    builder.button(text="❌ Скасувати", callback_data="jt:back")
    builder.adjust(2)

    await callback.message.answer(
        f"🗑 Ви впевнені що хочете видалити заявку <b>#{ticket_id}</b>?",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("jt:delete_ok:"))
async def delete_ticket_ok(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[2])
    success = await delete_ticket(ticket_id)
    if success:
        await callback.answer("✅ Видалено!")
        await callback.message.edit_text(f"🗑 Заявку <b>#{ticket_id}</b> видалено.", parse_mode="HTML")
    else:
        await callback.answer("⚠️ Не вдалось видалити.", show_alert=True)


@router.callback_query(F.data == "jt:back")
async def journal_back(callback: CallbackQuery, state: FSMContext, role: str):
    await callback.answer()
    await show_journal(callback, state)


# ── Чистка заявок ────────────────────────────────

@router.message(F.text == "🗑 Чистка заявок")
async def cleanup_start(message: Message, state: FSMContext, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Видалити за датою", callback_data="cleanup:by_date")
    builder.button(text="🗑 Видалити конкретну", callback_data="cleanup:by_id")
    builder.adjust(1)

    await state.set_state(CleanupForm.choose_method)
    await message.answer(
        "🗑 <b>Чистка заявок</b>\n\nОберіть спосіб:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "cleanup:by_date")
async def cleanup_by_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CleanupForm.waiting_date)
    await callback.message.answer(
        "📅 Введіть дату у форматі <b>ДД.ММ.РРРР</b>\n\n"
        "Всі заявки <b>старші</b> цієї дати будуть видалені.\n"
        "Наприклад: <code>01.01.2025</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CleanupForm.waiting_date)
async def cleanup_date_confirm(message: Message, state: FSMContext):
    from datetime import datetime
    text = message.text.strip()
    try:
        date = datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Невірний формат. Введіть дату як <code>ДД.ММ.РРРР</code>", parse_mode="HTML")
        return

    count = await count_tickets_before_date(date.strftime("%Y-%m-%d"))
    if count == 0:
        await message.answer("📭 Немає заявок старших цієї дати.")
        await state.clear()
        return

    await state.update_data(cleanup_date=date.strftime("%Y-%m-%d"))
    await state.set_state(CleanupForm.confirm_delete)

    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ Так, видалити {count} заявок", callback_data="cleanup:confirm_date")
    builder.button(text="❌ Скасувати", callback_data="cleanup:cancel")
    builder.adjust(1)

    await message.answer(
        f"⚠️ Буде видалено <b>{count}</b> заявок старших <b>{text}</b>.\n\nПідтвердити?",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "cleanup:confirm_date")
async def cleanup_confirm_date(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    count = await delete_tickets_before_date(data["cleanup_date"])
    await state.clear()
    await callback.answer("✅ Готово!")
    await callback.message.edit_text(f"🗑 Видалено <b>{count}</b> заявок.", parse_mode="HTML")


@router.callback_query(F.data == "cleanup:by_id")
async def cleanup_by_id(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CleanupForm.waiting_id)
    await callback.message.answer("🔢 Введіть <b>номер заявки</b> для видалення:", parse_mode="HTML")
    await callback.answer()


@router.message(CleanupForm.waiting_id)
async def cleanup_id_confirm(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Введіть числовий номер заявки.")
        return

    ticket_id = int(text)
    t = await get_full_ticket(ticket_id)
    if not t:
        await message.answer(f"❌ Заявку #{ticket_id} не знайдено.")
        await state.clear()
        return

    await state.update_data(cleanup_ticket_id=ticket_id)
    await state.set_state(CleanupForm.confirm_delete)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Так, видалити", callback_data="cleanup:confirm_id")
    builder.button(text="❌ Скасувати", callback_data="cleanup:cancel")
    builder.adjust(2)

    await message.answer(
        f"⚠️ Видалити заявку <b>#{ticket_id}</b>?\n"
        f"🖥 Енідеск: {t['enddesk']}\n"
        f"🗂 {t['category']}",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "cleanup:confirm_id")
async def cleanup_confirm_id(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await delete_ticket(data["cleanup_ticket_id"])
    await state.clear()
    await callback.answer("✅ Видалено!")
    await callback.message.edit_text(
        f"🗑 Заявку <b>#{data['cleanup_ticket_id']}</b> видалено.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cleanup:cancel")
async def cleanup_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Скасовано.")
    await callback.message.edit_text("❌ Операцію скасовано.")


# ── Оцінка заявки (від заявника) ─────────────────

@router.callback_query(F.data.startswith("rate:"))
async def rate_ticket(callback: CallbackQuery):
    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    rating = int(parts[2])

    from database.queries import set_ticket_rating
    await set_ticket_rating(ticket_id, rating)

    stars = "⭐" * rating + "☆" * (5 - rating)
    await callback.message.edit_text(
        f"✅ Дякуємо за оцінку!\n\n"
        f"Заявка #{ticket_id}: {stars}",
        parse_mode="HTML"
    )
    await callback.answer()


# ── Перепризначення заявки ───────────────────────

@router.callback_query(F.data.startswith("jt:reassign:"))
async def reassign_choose(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    ticket_id = int(callback.data.split(":")[2])
    from database.queries import get_all_it_staff
    staff = await get_all_it_staff()

    if not staff:
        await callback.answer("❌ Немає ІТ спеціалістів.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for s in staff:
        builder.button(
            text=f"👷 {s['full_name']}",
            callback_data=f"jt:reassign_ok:{ticket_id}:{s['id']}"
        )
    builder.button(text="❌ Скасувати", callback_data="jt:back")
    builder.adjust(1)

    await callback.message.answer(
        f"👷 <b>Оберіть нового виконавця для заявки #{ticket_id}:</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("jt:reassign_ok:"))
async def reassign_confirm(callback: CallbackQuery, bot: Bot, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    parts = callback.data.split(":")
    ticket_id = int(parts[2])
    new_assignee_id = int(parts[3])

    t = await get_full_ticket(ticket_id)
    old_assignee_id = t["assignee_id"] if t else None

    from database.queries import reassign_ticket
    success = await reassign_ticket(ticket_id, new_assignee_id)

    if not success:
        await callback.answer("⚠️ Не вдалось перепризначити.", show_alert=True)
        return

    await callback.answer("✅ Заявку перепризначено!")
    await callback.message.edit_text(
        f"✅ Заявку <b>#{ticket_id}</b> передано новому виконавцю.",
        parse_mode="HTML"
    )

    from notifications import notify_reassigned
    if t:
        await notify_reassigned(bot, t, old_assignee_id, new_assignee_id)
