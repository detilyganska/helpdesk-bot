import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

MAX_ATTEMPTS_BEFORE_BAN = 3

SUSPICIOUS_PATTERNS = [
    r"<[^>]+>",
    r"&[#\w]+;",
    r"(DROP|DELETE|INSERT|UPDATE|SELECT|UNION|ALTER|CREATE|EXEC|EXECUTE|CAST|CONVERT|DECLARE|XP_)\s",
    r"--",
    r"\u2013|\u2014",
    r"/\*.*?\*/",
    r"(javascript|vbscript|onload|onerror|onclick):",
    r"%(2[0-9a-fA-F]|3[0-9a-fA-F]|4[0-9a-fA-F])",
    r"&#[0-9]+;",
    r"\\x[0-9a-fA-F]{2}",
    r"'\s*(OR|AND)\s*'?\d",
    r"'\s*(OR|AND)\s+\d",
]

BLOCKED_CHARS_DEFAULT = r"[;'\"\\<>&|`~^*{}[\]%$@!?=]"
CONTACT_TT_PATTERN    = r"^[\w\s\+\-\(\)\.,:]+$"

MAX_LENGTHS = {
    "enddesk":     50,
    "description": 1000,
    "contact_tt":  100,
}

FIELD_NAMES = {
    "enddesk":     "Енідеск",
    "description": "Опис проблеми",
    "contact_tt":  "Контакт з ТТ",
}


def is_suspicious(text: str) -> bool:
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def validate_input(text: str, field: str) -> tuple[bool, str]:
    text = text.strip()

    if not text:
        return False, "❌ Поле не може бути порожнім."

    max_len = MAX_LENGTHS.get(field, 500)
    if len(text) > max_len:
        return False, f"❌ Занадто довгий текст. Максимум {max_len} символів."

    if is_suspicious(text):
        return False, "❌ Текст містить недозволені символи. Спробуйте ще раз."

    if field == "contact_tt":
        if not re.match(CONTACT_TT_PATTERN, text, re.UNICODE):
            return False, "❌ Контакт може містити лише літери, цифри, +, -, (, ), пробіл."
        return True, ""

    if re.search(BLOCKED_CHARS_DEFAULT, text):
        return False, "❌ Текст містить недозволені символи. Спробуйте ще раз."

    return True, ""


async def check_and_notify(text: str, field: str, user, bot) -> bool:
    if not is_suspicious(text):
        return False

    from config import ADMIN_IDS, SUPER_ADMIN_ID
    from database.queries import add_suspicious_attempt, ban_user, reset_suspicious_attempts

    field_name = FIELD_NAMES.get(field, field)
    username = f"@{user.username}" if user.username else "немає"
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    safe_text = text[:200].replace("<", "&lt;").replace(">", "&gt;")

    attempts = await add_suspicious_attempt(user.id)
    remaining = MAX_ATTEMPTS_BEFORE_BAN - attempts
    will_ban = attempts >= MAX_ATTEMPTS_BEFORE_BAN

    if will_ban:
        await ban_user(user.id, reason=f"Автобан: {attempts} підозрілих спроб")
        await reset_suspicious_attempts(user.id)
        status_text = "🔴 <b>Користувача АВТОМАТИЧНО ЗАБАНЕНО!</b>"
    else:
        status_text = f"⚠️ Спроба {attempts}/{MAX_ATTEMPTS_BEFORE_BAN} — до бану залишилось {remaining}"

    alert_text = (
        f"🚨 <b>Підозріла активність!</b>\n\n"
        f"👤 <b>Користувач:</b> {user.full_name}\n"
        f"📱 <b>Username:</b> {username}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"📝 <b>Поле:</b> {field_name}\n"
        f"💬 <b>Введено:</b> <code>{safe_text}</code>\n"
        f"🕐 <b>Час:</b> {now}\n\n"
        f"{status_text}"
    )

    notify_ids = set(ADMIN_IDS)
    notify_ids.add(SUPER_ADMIN_ID)

    for admin_id in notify_ids:
        try:
            await bot.send_message(admin_id, alert_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    logger.warning(f"Suspicious input attempt {attempts}/{MAX_ATTEMPTS_BEFORE_BAN} from {user.id}: {text[:100]}")
    return True
