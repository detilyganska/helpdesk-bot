from aiogram import Router, F
from aiogram.types import Message
from database.queries import get_it_staff_profile

router = Router()


def stars(avg: float | None) -> str:
    if avg is None:
        return "немає оцінок"
    full = int(avg)
    half = 1 if (avg - full) >= 0.5 else 0
    empty = 5 - full - half
    return "⭐" * full + "✨" * half + "☆" * empty + f" ({avg})"


@router.message(F.text == "👤 Мій профіль")
async def my_profile(message: Message, role: str):
    if role not in ("it", "admin"):
        await message.answer("⛔ Доступ заборонено.")
        return

    profile = await get_it_staff_profile(message.from_user.id)
    if not profile:
        await message.answer("❌ Профіль не знайдено.")
        return

    added = profile["added_at"].strftime("%d.%m.%Y") if profile["added_at"] else "—"
    username = f"@{profile['username']}" if profile["username"] else "—"

    await message.answer(
        f"👤 <b>Мій профіль</b>\n\n"
        f"🏷 <b>Ім'я:</b> {profile['full_name']}\n"
        f"📱 <b>Username:</b> {username}\n"
        f"📅 <b>В команді з:</b> {added}\n\n"
        f"✅ <b>Виконано заявок:</b> {profile['total_done']}\n"
        f"⭐ <b>Рейтинг:</b> {stars(profile['avg_rating'])}",
        parse_mode="HTML"
    )


@router.message(F.text == "👥 Профілі ІТ відділу")
async def all_profiles(message: Message, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return

    from database.queries import get_all_it_staff_profiles
    profiles = await get_all_it_staff_profiles()

    if not profiles:
        await message.answer("📭 ІТ відділ порожній.")
        return

    lines = ["👥 <b>Профілі ІТ відділу:</b>\n"]
    for i, p in enumerate(profiles, 1):
        username = f"@{p['username']}" if p["username"] else "—"
        rating = stars(p["avg_rating"])
        added = p["added_at"].strftime("%d.%m.%Y") if p["added_at"] else "—"
        lines.append(
            f"{i}. <b>{p['full_name']}</b> ({username})\n"
            f"   ✅ Виконано: {p['total_done']} | ⭐ {rating}\n"
            f"   📅 В команді з: {added}\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")
