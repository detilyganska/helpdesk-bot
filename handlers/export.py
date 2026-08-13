import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import get_tickets_for_export

router = Router()

STATUS_UA = {
    "pending":     "Очікується",
    "in_progress": "В роботі",
    "done":        "Готово",
}


def build_excel(tickets: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Заявки"

    headers = [
        "№", "Заявник", "Username", "Енідеск", "Категорія",
        "Опис", "Контакт з ТТ", "Статус", "Виконавець",
        "Оцінка", "Створено", "Оновлено"
    ]

    header_fill = PatternFill("solid", fgColor="2F5496")
    header_font = Font(bold=True, color="FFFFFF")

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row, t in enumerate(tickets, 2):
        ws.cell(row=row, column=1,  value=t["id"])
        ws.cell(row=row, column=2,  value=t["user_name"])
        ws.cell(row=row, column=3,  value=f"@{t['username']}" if t["username"] else "—")
        ws.cell(row=row, column=4,  value=t["enddesk"])
        ws.cell(row=row, column=5,  value=t["category"])
        ws.cell(row=row, column=6,  value=t["description"])
        ws.cell(row=row, column=7,  value=t.get("contact_tt") or "—")
        ws.cell(row=row, column=8,  value=STATUS_UA.get(t["status"], t["status"]))
        ws.cell(row=row, column=9,  value=t["assignee"] or "—")
        ws.cell(row=row, column=10, value=t["rating"] or "—")
        ws.cell(row=row, column=11, value=t["created_at"].strftime("%d.%m.%Y %H:%M") if t["created_at"] else "—")
        ws.cell(row=row, column=12, value=t["updated_at"].strftime("%d.%m.%Y %H:%M") if t["updated_at"] else "—")

        if row % 2 == 0:
            for col in range(1, 13):
                ws.cell(row=row, column=col).fill = PatternFill("solid", fgColor="EEF2FF")

    # Ширина колонок
    widths = [6, 20, 16, 18, 20, 40, 20, 14, 20, 8, 18, 18]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.message(F.text == "📥 Експорт в Excel")
async def export_start(message: Message, role: str):
    if role != "admin":
        await message.answer("⛔ Тільки для адміністраторів.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Тиждень",  callback_data="export:week")
    builder.button(text="📅 Місяць",   callback_data="export:month")
    builder.button(text="📅 Рік",      callback_data="export:year")
    builder.button(text="📋 Всі",      callback_data="export:all")
    builder.adjust(2)

    await message.answer(
        "📥 <b>Експорт заявок в Excel</b>\n\nОберіть період:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("export:"))
async def export_generate(callback: CallbackQuery, role: str):
    if role != "admin":
        await callback.answer("⛔", show_alert=True)
        return

    period = callback.data.split(":")[1]
    period_ua = {"week": "тиждень", "month": "місяць", "year": "рік", "all": "весь час"}

    await callback.answer()
    await callback.message.answer("⏳ Генерую файл...")

    tickets = await get_tickets_for_export(period if period != "all" else None)

    if not tickets:
        await callback.message.answer("📭 Немає заявок за вибраний період.")
        return

    xlsx_bytes = build_excel(tickets)
    filename = f"tickets_{period}.xlsx"

    await callback.message.answer_document(
        document=BufferedInputFile(xlsx_bytes, filename=filename),
        caption=f"📊 Заявки за: <b>{period_ua[period]}</b> | Всього: <b>{len(tickets)}</b>",
        parse_mode="HTML"
    )
