from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import SUPER_ADMIN_ID
from database.queries import (
    is_it_staff, upsert_user, update_it_staff_info,
    is_banned, get_admin_ids_from_db
)


class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            # Суперадмін — завжди має доступ
            if user.id == SUPER_ADMIN_ID:
                await upsert_user(user.id, user.full_name, user.username)
                data["role"] = "admin"
                data["is_super_admin"] = True
                return await handler(event, data)

            # Перевірка бану
            if await is_banned(user.id):
                if isinstance(event, Message):
                    await event.answer("⛔ Ваш акаунт заблоковано. Зверніться до адміністратора.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔ Ваш акаунт заблоковано.", show_alert=True)
                return

            await upsert_user(user.id, user.full_name, user.username)

            # Адміни з БД
            admin_ids = await get_admin_ids_from_db()

            if user.id in admin_ids:
                data["role"] = "admin"
                data["is_super_admin"] = False
            elif await is_it_staff(user.id):
                await update_it_staff_info(user.id, user.full_name, user.username)
                data["role"] = "it"
                data["is_super_admin"] = False
            else:
                data["role"] = "user"
                data["is_super_admin"] = False

        return await handler(event, data)
