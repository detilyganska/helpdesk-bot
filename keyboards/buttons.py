from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ──────────────────────────────────────────────
# Головне меню
# ──────────────────────────────────────────────

def main_menu_user() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Нова заявка")],
            [KeyboardButton(text="📋 Мої заявки")],
        ],
        resize_keyboard=True
    )


def main_menu_it() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Пул заявок")],
            [KeyboardButton(text="🔧 Мої активні заявки")],
            [KeyboardButton(text="👤 Мій профіль")],
        ],
        resize_keyboard=True
    )


def main_menu_admin(is_super: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📝 Нова заявка")],
        [KeyboardButton(text="📋 Мої заявки")],
        [KeyboardButton(text="📥 Пул заявок")],
        [KeyboardButton(text="⚙️ Адмін-панель")],
    ]
    if is_super:
        keyboard.insert(3, [KeyboardButton(text="👑 Управління адмінами")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# ──────────────────────────────────────────────
# Категорії (inline)
# ──────────────────────────────────────────────

def categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat["name"], callback_data=f"cat:{cat['id']}")
    builder.adjust(2)
    return builder.as_markup()


# ──────────────────────────────────────────────
# Пропустити фото
# ──────────────────────────────────────────────

def skip_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустити фото", callback_data="skip_photo")]
    ])


# ──────────────────────────────────────────────
# Підтвердження заявки
# ──────────────────────────────────────────────

def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_ticket"),
            InlineKeyboardButton(text="❌ Скасувати",   callback_data="cancel_ticket"),
        ]
    ])


# ──────────────────────────────────────────────
# Пул заявок (для ІТ)
# ──────────────────────────────────────────────

def take_ticket_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Взяти в роботу",
            callback_data=f"take:{ticket_id}"
        )]
    ])


def close_ticket_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Готово",
            callback_data=f"close:{ticket_id}"
        )]
    ])


# ──────────────────────────────────────────────
# Адмін: управління ІТ
# ──────────────────────────────────────────────

def admin_it_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати ІТ спеціаліста", callback_data="admin:add_it")],
        [InlineKeyboardButton(text="➖ Видалити ІТ спеціаліста", callback_data="admin:list_it_remove")],
        [InlineKeyboardButton(text="📋 Список ІТ відділу", callback_data="admin:list_it")],
    ])


def remove_it_keyboard(staff: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in staff:
        name = s["full_name"]
        builder.button(text=f"❌ {name}", callback_data=f"admin:remove:{s['id']}")
    builder.adjust(1)
    return builder.as_markup()
