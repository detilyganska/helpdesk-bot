from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

from states import TicketForm
from validators import validate_input, check_and_notify
from keyboards.buttons import (
    main_menu_user, main_menu_it, main_menu_admin,
    categories_keyboard, skip_photo_keyboard, confirm_keyboard
)
from database.queries import (
    get_categories, create_ticket, get_user_tickets,
    is_approved_user, approve_user, get_invite_secret
)
from notifications import notify_it_new_ticket

router = Router()

STATUS_EMOJI = {
    "pending":     "⏳ Очікується",
    "in_progress": "🔧 В роботі",
    "done":        "✅ Готово",
}


def get_menu(role: str, is_super_admin: bool = False):
    if role == "admin":
        return main_menu_admin(is_super=is_super_admin)
    if role == "it":
        return main_menu_it()
    return main_menu_user()


# ── /start ──────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, role: str, state: FSMContext, is_super_admin: bool = False):
    await state.clear()
    user_id = message.from_user.id

    if role in ("admin", "it"):
        await message.answer(
            "👋 Вітаємо в HelpDesk!\n\nОберіть дію з меню нижче.",
            reply_markup=get_menu(role, is_super_admin)
        )
        return

    if await is_approved_user(user_id):
        await message.answer(
            "👋 Вітаємо в HelpDesk!\n\nОберіть дію з меню нижче.",
            reply_markup=get_menu(role, is_super_admin)
        )
        return

    secret = command.args if command else None
    if secret and secret == await get_invite_secret():
        await approve_user(user_id)
        await message.answer(
            "✅ <b>Доступ підтверджено!</b>\n\n"
            "Тепер ви можете подавати заявки до ІТ відділу.\n\n"
            "👋 Вітаємо в HelpDesk!",
            parse_mode="HTML",
            reply_markup=get_menu("user")
        )
        return

    await message.answer(
        "⛔ <b>Доступ заборонено.</b>\n\n"
        "Для отримання доступу зверніться до ІТ відділу\n"
        "за посиланням для реєстрації.",
        parse_mode="HTML"
    )


# ── Мої заявки ──────────────────────────────────

@router.message(F.text == "📋 Мої заявки")
async def my_tickets(message: Message, role: str):
    if role == "user" and not await is_approved_user(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return

    tickets = await get_user_tickets(message.from_user.id)
    if not tickets:
        await message.answer("У вас ще немає заявок.")
        return

    lines = ["<b>Ваші заявки:</b>\n"]
    for t in tickets:
        status = STATUS_EMOJI.get(t["status"], t["status"])
        date = t["created_at"].strftime("%d.%m.%Y %H:%M") if t["created_at"] else "—"
        lines.append(f"• <b>#{t['id']}</b> | {t['category']} | {status} | {date}")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ── Нова заявка: крок 1 — категорія ────────────

@router.message(F.text == "📝 Нова заявка")
async def new_ticket_start(message: Message, state: FSMContext, role: str):
    if role == "user" and not await is_approved_user(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return

    categories = await get_categories()
    await state.set_state(TicketForm.category)
    await message.answer(
        "🗂 <b>Оберіть категорію проблеми:</b>",
        parse_mode="HTML",
        reply_markup=categories_keyboard(categories)
    )


@router.callback_query(TicketForm.category, F.data.startswith("cat:"))
async def ticket_category(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split(":")[1])
    categories = await get_categories()
    cat_name = next((c["name"] for c in categories if c["id"] == cat_id), "—")

    await state.update_data(category_id=cat_id, category_name=cat_name)
    await state.set_state(TicketForm.enddesk)
    await callback.message.edit_text(
        f"✅ Категорія: <b>{cat_name}</b>\n\n"
        "🖥 Введіть <b>Енідеск</b> (прописом, наприклад: <i>пк-бухгалтерія-01</i>):",
        parse_mode="HTML"
    )


# ── Крок 2 — Енідеск ────────────────────────────

@router.message(TicketForm.enddesk)
async def ticket_enddesk(message: Message, state: FSMContext, bot: Bot):
    await check_and_notify(message.text, "enddesk", message.from_user, bot)
    valid, err = validate_input(message.text, "enddesk")
    if not valid:
        await message.answer(err)
        return
    await state.update_data(enddesk=message.text.strip())
    await state.set_state(TicketForm.description)
    await message.answer("📝 Опишіть проблему детально:")


# ── Крок 3 — опис ───────────────────────────────

@router.message(TicketForm.description)
async def ticket_description(message: Message, state: FSMContext, bot: Bot):
    await check_and_notify(message.text, "description", message.from_user, bot)
    valid, err = validate_input(message.text, "description")
    if not valid:
        await message.answer(err)
        return
    await state.update_data(description=message.text.strip())
    await state.set_state(TicketForm.contact_tt)
    await message.answer(
        "📞 Введіть <b>контакт з ТТ</b> (телефон або ім'я відповідальної особи):",
        parse_mode="HTML"
    )


# ── Крок 4 — контакт з ТТ ───────────────────────

@router.message(TicketForm.contact_tt)
async def ticket_contact_tt(message: Message, state: FSMContext, bot: Bot):
    await check_and_notify(message.text, "contact_tt", message.from_user, bot)
    valid, err = validate_input(message.text, "contact_tt")
    if not valid:
        await message.answer(err)
        return
    await state.update_data(contact_tt=message.text.strip())
    await state.set_state(TicketForm.photo)
    await message.answer(
        "📷 Надішліть фото проблеми або пропустіть:",
        reply_markup=skip_photo_keyboard()
    )


# ── Крок 5 — фото ───────────────────────────────

@router.message(TicketForm.photo, F.photo)
async def ticket_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=file_id)
    await show_confirm(message, state)


@router.callback_query(TicketForm.photo, F.data == "skip_photo")
async def ticket_skip_photo(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photo_file_id=None)
    await callback.message.delete()
    await show_confirm(callback.message, state)


async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    photo = "є" if data.get("photo_file_id") else "немає"
    text = (
        "📋 <b>Перевірте заявку:</b>\n\n"
        f"🗂 <b>Категорія:</b> {data['category_name']}\n"
        f"🖥 <b>Енідеск:</b> {data['enddesk']}\n"
        f"📝 <b>Опис:</b> {data['description']}\n"
        f"📞 <b>Контакт з ТТ:</b> {data['contact_tt']}\n"
        f"📷 <b>Фото:</b> {photo}"
    )
    await state.set_state(TicketForm.confirm)
    await message.answer(text, parse_mode="HTML", reply_markup=confirm_keyboard())


# ── Крок 6 — підтвердження ──────────────────────

@router.callback_query(TicketForm.confirm, F.data == "confirm_ticket")
async def ticket_confirmed(callback: CallbackQuery, state: FSMContext, bot: Bot, role: str, is_super_admin: bool = False):
    data = await state.get_data()
    await state.clear()

    ticket_id = await create_ticket(
        user_id=callback.from_user.id,
        category_id=data["category_id"],
        enddesk=data["enddesk"],
        description=data["description"],
        contact_tt=data["contact_tt"],
        photo_file_id=data.get("photo_file_id"),
    )

    await callback.message.edit_text(
        f"✅ <b>Заявку #{ticket_id} прийнято!</b>\n"
        "Ви отримаєте сповіщення, коли ІТ спеціаліст візьме її в роботу.",
        parse_mode="HTML"
    )
    await callback.message.answer("Головне меню:", reply_markup=get_menu(role, is_super_admin))

    ticket_data = {
        "id": ticket_id,
        "user_id": callback.from_user.id,
        "user_full_name": callback.from_user.full_name,
        "username": callback.from_user.username,
        "enddesk": data["enddesk"],
        "category": data["category_name"],
        "description": data["description"],
        "contact_tt": data["contact_tt"],
        "photo_file_id": data.get("photo_file_id"),
    }
    await notify_it_new_ticket(bot, ticket_data)


@router.callback_query(TicketForm.confirm, F.data == "cancel_ticket")
async def ticket_cancelled(callback: CallbackQuery, state: FSMContext, role: str, is_super_admin: bool = False):
    await state.clear()
    await callback.message.edit_text("❌ Заявку скасовано.")
    await callback.message.answer("Головне меню:", reply_markup=get_menu(role, is_super_admin))
