import asyncio
import logging
# import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.models import init_db
from middlewares.role import RoleMiddleware
from handlers import user, it_staff, admin, journal, profile, export, ban, superadmin
from scheduler import scheduler_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    await init_db()

    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    dp.include_router(user.router)
    dp.include_router(it_staff.router)
    dp.include_router(admin.router)
    dp.include_router(journal.router)
    dp.include_router(profile.router)
    dp.include_router(export.router)
    dp.include_router(ban.router)
    dp.include_router(superadmin.router)

    # Запускаємо планувальник паралельно з ботом
    asyncio.create_task(scheduler_loop(bot))

    logger.info("Бот запущено.")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
