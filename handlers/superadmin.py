from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SUPER_ADMIN_ID
from database.queries import (
    get_all_admins, add_admin, remove_admin, find_user_by_username
)

router = Router()


class SuperAdminForm(StatesGroup):
    waiting_input = State()


def is_super(role: str, user_id: int) -> bool:
    return role == "admin" and user_id == SUPER_ADMIN_ID


# ── Управління адмінами ──────────────────────────

@router.message(F.text == "👑 Управління адмінами")
async def manage_admins(message: Message, role: str):
    if not is_super(role, message.from_user.id):
        await message.answer("⛔ Тільки для суперадміна.")
        return

    admins = await get_all_admins()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Додати адміна", callback_data="sa:add")
    builder.adjust(1)

    if not admins:
        await message.answer(
            "👑 <b>Адміністратори</b>\n\nСписок порожній.",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        return

    lines = [f"👑 <b>Адміністратори ({len(admins)}):</b>\n"]
    for a in admins:
        username = f"@{a['username']}" if a["username"] else "—"
        date = a["added_at"].strftime("%d.%m.%Y") if a["added_at"] else "—"
        lines.append(f"• {a['full_name']} ({username}) | {date}")

    remove_builder = InlineKeyboardBuilder()
    for a in admins:
        remove_builder.button(
            text=f"❌ Видалити {a['full_name']}",
            callback_data=f"sa:remove:{a['id']}"
        )
    remove_builder.button(text="➕ Додати адміна", callback_data="sa:add")
    remove_builder.adjust(1)

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=remove_builder.as_markup()
    )


# ── Додати адміна ────────────────────────────────

@router.callback_query(F.data == "sa:add")
async def add_admin_start(callback: CallbackQuery, state: FSMContext, role: str):
    if not is_super(role, callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return

    await state.set_state(SuperAdminForm.waiting_input)
    await callback.message.answer(
        "➕ Введіть <b>username</b> або <b>ID</b> нового адміна:\n\n"
        "<i>Приклади: @ivanov_ivan або 123456789\n"
        "Користувач повинен хоча б раз написати боту.</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SuperAdminForm.waiting_input)
async def add_admin_confirm(message: Message, state: FSMContext, role: str):
    if not is_super(role, message.from_user.id):
        return

    text = message.text.strip()
    user_data = None

    if text.startswith("@") or not text.isdigit():
        user_data = await find_user_by_username(text.lstrip("@"))
        if not user_data:
            await message.answer(
                f"❌ Користувача <code>{text}</code> не знайдено.\n"
                f"<i>Користувач повинен хоча б раз написати боту.</i>",
                parse_mode="HTML"
            )
            await state.clear()
            return
    else:
        user_id = int(text)
        user_data = {"id": user_id, "full_name": f"Admin {user_id}", "username": None}

    # Не можна додати суперадміна як звичайного адміна
    if user_data["id"] == SUPER_ADMIN_ID:
        await message.answer("ℹ️ Це суперадмін — він вже має всі права.")
        await state.clear()
        return

    await add_admin(user_data["id"], user_data["full_name"], user_data.get("username"))
    await state.clear()

    username = f"@{user_data['username']}" if user_data.get("username") else "—"
    await message.answer(
        f"✅ <b>{user_data['full_name']}</b> ({username}) додано як адміністратора.\n"
        f"<i>При наступному зверненні до бота він отримає права адміна.</i>",
        parse_mode="HTML"
    )


# ── Видалити адміна ──────────────────────────────

@router.callback_query(F.data.startswith("sa:remove:"))
async def remove_admin_confirm(callback: CallbackQuery, role: str):
    if not is_super(role, callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return

    user_id = int(callback.data.split(":")[2])

    if user_id == SUPER_ADMIN_ID:
        await callback.answer("⛔ Не можна видалити суперадміна.", show_alert=True)
        return

    await remove_admin(user_id)
    await callback.answer("✅ Видалено!")
    await callback.message.answer(
        f"✅ Адміністратора <code>{user_id}</code> видалено.",
        parse_mode="HTML"
    )
