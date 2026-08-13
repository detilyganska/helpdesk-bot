from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import (
    ban_user, unban_user, get_banned_users, find_user_by_username
)

router = Router()


class BanForm(StatesGroup):
    waiting_input = State()


# ── Бан-лист ─────────────────────────────────────

@router.message(F.text == "🚫 Бан-лист")
async def banlist(message: Message, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return

    banned = await get_banned_users()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Забанити користувача", callback_data="ban:add")
    builder.adjust(1)

    if not banned:
        await message.answer(
            "🚫 <b>Бан-лист порожній</b>",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        return

    lines = [f"🚫 <b>Забанені користувачі ({len(banned)}):</b>\n"]
    for b in banned:
        username = f"@{b['username']}" if b["username"] else "—"
        date = b["banned_at"].strftime("%d.%m.%Y") if b["banned_at"] else "—"
        lines.append(f"• {b['full_name']} ({username}) | <code>{b['user_id']}</code> | {date}")

    # Кнопки розбану
    unban_builder = InlineKeyboardBuilder()
    for b in banned:
        name = b["full_name"]
        unban_builder.button(
            text=f"✅ Розбанити {name}",
            callback_data=f"ban:unban:{b['user_id']}"
        )
    unban_builder.button(text="➕ Забанити користувача", callback_data="ban:add")
    unban_builder.adjust(1)

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=unban_builder.as_markup())


# ── Додати бан ───────────────────────────────────

@router.callback_query(F.data == "ban:add")
async def ban_add_start(callback: CallbackQuery, state: FSMContext, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(BanForm.waiting_input)
    await callback.message.answer(
        "🚫 Введіть <b>username</b> або <b>ID</b> користувача для бану:\n\n"
        "<i>Приклади: @ivanov_ivan або 123456789</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(BanForm.waiting_input)
async def ban_add_confirm(message: Message, state: FSMContext, role: str):
    if role != "admin":
        return

    text = message.text.strip()
    user_data = None

    if text.startswith("@") or (not text.isdigit()):
        # Пошук по username
        user_data = await find_user_by_username(text.lstrip("@"))
        if not user_data:
            await message.answer(
                f"❌ Користувача <code>{text}</code> не знайдено в базі.\n"
                f"<i>Користувач повинен хоча б раз написати боту.</i>",
                parse_mode="HTML"
            )
            await state.clear()
            return
    else:
        # По ID
        user_id = int(text)
        user_data = {"id": user_id, "full_name": f"ID {user_id}", "username": None}

    await ban_user(user_data["id"])
    await state.clear()

    username = f"@{user_data['username']}" if user_data.get("username") else "—"
    await message.answer(
        f"🚫 Користувача <b>{user_data['full_name']}</b> ({username}) забанено.\n"
        f"🆔 ID: <code>{user_data['id']}</code>",
        parse_mode="HTML"
    )


# ── Розбан ───────────────────────────────────────

@router.callback_query(F.data.startswith("ban:unban:"))
async def ban_unban(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    user_id = int(callback.data.split(":")[2])
    success = await unban_user(user_id)

    if success:
        await callback.answer("✅ Розбанено!")
        await callback.message.answer(
            f"✅ Користувача <code>{user_id}</code> розбанено.",
            parse_mode="HTML"
        )
    else:
        await callback.answer("⚠️ Користувача не знайдено в бан-листі.", show_alert=True)
