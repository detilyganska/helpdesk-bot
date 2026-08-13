from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.buttons import admin_it_keyboard, remove_it_keyboard
from database.queries import (
    get_all_it_staff, add_it_staff, remove_it_staff,
    get_approved_users_count
)

router = Router()


class AdminForm(StatesGroup):
    waiting_user_id    = State()
    waiting_new_secret = State()


def admin_panel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Управління ІТ складом")],
            [KeyboardButton(text="👥 Профілі ІТ відділу")],
            [KeyboardButton(text="🔗 Посилання для реєстрації")],
            [KeyboardButton(text="🔄 Змінити секрет запрошення")],
            [KeyboardButton(text="📊 Журнал заявок")],
            [KeyboardButton(text="🗑 Чистка заявок")],
            [KeyboardButton(text="📥 Експорт в Excel")],
            [KeyboardButton(text="🚫 Бан-лист")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True
    )


# ── Відкрити адмін-панель ────────────────────────

@router.message(F.text == "⚙️ Адмін-панель")
async def open_admin_panel(message: Message, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return
    await message.answer(
        "⚙️ <b>Адмін-панель</b>\n\nОберіть дію:",
        parse_mode="HTML",
        reply_markup=admin_panel_menu()
    )


# ── Назад ────────────────────────────────────────

@router.message(F.text == "◀️ Назад")
async def back_to_main(message: Message, role: str, is_super_admin: bool = False):
    from keyboards.buttons import main_menu_admin
    await message.answer("Головне меню:", reply_markup=main_menu_admin(is_super=is_super_admin))


# ── Посилання для реєстрації ─────────────────────

@router.message(F.text == "🔗 Посилання для реєстрації")
async def show_invite_link(message: Message, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return

    from config import INVITE_SECRET
    bot_info = await message.bot.get_me()
    count = await get_approved_users_count()
    link = f"https://t.me/{bot_info.username}?start={INVITE_SECRET}"

    await message.answer(
        f"🔗 <b>Посилання для реєстрації:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"👥 Зареєстровано: <b>{count}</b> користувачів\n\n"
        f"<i>Надішліть це посилання співробітнику — після переходу він отримає доступ.</i>",
        parse_mode="HTML"
    )


# ── Змінити секрет ───────────────────────────────

@router.message(F.text == "🔄 Змінити секрет запрошення")
async def change_secret_start(message: Message, state: FSMContext, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return

    from config import INVITE_SECRET
    await state.set_state(AdminForm.waiting_new_secret)
    await message.answer(
        f"🔄 Поточний секрет: <code>{INVITE_SECRET}</code>\n\n"
        f"Введіть новий секретний код (тільки латиниця та цифри):",
        parse_mode="HTML"
    )


@router.message(AdminForm.waiting_new_secret)
async def change_secret_confirm(message: Message, state: FSMContext, role: str):
    if role != "admin":
        return

    import re
    import config

    new_secret = message.text.strip()
    if not re.match(r'^[a-zA-Z0-9_]{4,32}$', new_secret):
        await message.answer(
            "❌ Невірний формат. Тільки латиниця, цифри та _ від 4 до 32 символів."
        )
        return

    # Оновлюємо в пам'яті
    config.INVITE_SECRET = new_secret

    # Оновлюємо в .env файлі
    try:
        with open(".env", "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(".env", "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith("INVITE_SECRET="):
                    f.write(f"INVITE_SECRET={new_secret}\n")
                else:
                    f.write(line)
    except Exception as e:
        await message.answer(f"⚠️ Секрет змінено в пам'яті, але не збережено у файл: {e}")
        await state.clear()
        return

    await state.clear()
    bot_info = await message.bot.get_me()
    new_link = f"https://t.me/{bot_info.username}?start={new_secret}"
    await message.answer(
        f"✅ Секрет змінено!\n\n"
        f"🔗 Нове посилання:\n<code>{new_link}</code>",
        parse_mode="HTML",
        reply_markup=admin_panel_menu()
    )


# ── Управління ІТ складом ────────────────────────

@router.message(F.text == "👥 Управління ІТ складом")
async def admin_it_panel(message: Message, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return
    await message.answer(
        "👥 <b>Управління ІТ відділом</b>\n\nОберіть дію:",
        parse_mode="HTML",
        reply_markup=admin_it_keyboard()
    )


@router.callback_query(F.data == "admin:list_it")
async def list_it(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return
    staff = await get_all_it_staff()
    if not staff:
        await callback.message.edit_text("📭 ІТ відділ порожній.")
        return

    lines = ["<b>👥 ІТ відділ:</b>\n"]
    for s in staff:
        uname = f"@{s['username']}" if s["username"] else "без username"
        lines.append(f"• {s['full_name']} ({uname}) — ID: <code>{s['id']}</code>")

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=admin_it_keyboard()
    )


@router.callback_query(F.data == "admin:add_it")
async def add_it_start(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(AdminForm.waiting_user_id)
    await callback.message.edit_text(
        "➕ Введіть <b>Telegram ID</b> нового ІТ спеціаліста:\n\n"
        "<i>Щоб дізнатись ID — попросіть людину написати боту /start, "
        "або скористайтесь @userinfobot</i>",
        parse_mode="HTML"
    )


@router.message(AdminForm.waiting_user_id)
async def add_it_confirm(message: Message, state: FSMContext, role: str):
    if role != "admin":
        return

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Введіть числовий Telegram ID.")
        return

    new_id = int(text)
    staff = await get_all_it_staff()
    if any(s["id"] == new_id for s in staff):
        await state.clear()
        await message.answer(
            f"⚠️ Користувач <code>{new_id}</code> вже в ІТ відділі.",
            parse_mode="HTML",
            reply_markup=admin_it_keyboard()
        )
        return

    await add_it_staff(user_id=new_id, full_name=f"IT Staff {new_id}", username=None)
    await state.clear()
    await message.answer(
        f"✅ Користувача <code>{new_id}</code> додано до ІТ відділу.",
        parse_mode="HTML",
        reply_markup=admin_panel_menu()
    )


@router.callback_query(F.data == "admin:list_it_remove")
async def list_it_for_remove(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return
    staff = await get_all_it_staff()
    if not staff:
        await callback.message.edit_text("📭 ІТ відділ порожній.")
        return

    await callback.message.edit_text(
        "❌ <b>Оберіть кого видалити:</b>",
        parse_mode="HTML",
        reply_markup=remove_it_keyboard(staff)
    )


@router.callback_query(F.data.startswith("admin:remove:"))
async def remove_it_confirm(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return
    remove_id = int(callback.data.split(":")[2])
    await remove_it_staff(remove_id)
    await callback.answer("✅ Видалено!")
    await callback.message.edit_text(
        f"✅ Користувача <code>{remove_id}</code> видалено з ІТ відділу.",
        parse_mode="HTML",
        reply_markup=admin_it_keyboard()
    )
