from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def kb_language():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Oʻzbekcha")],
                  [KeyboardButton(text="Русский")],
                  [KeyboardButton(text="English")]],
        resize_keyboard=True, one_time_keyboard=True
    )

def kb_main():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔎 Найти авто")],
                  [KeyboardButton(text="🧾 Мои брони"), KeyboardButton(text="ℹ️ Помощь")]],
        resize_keyboard=True
    )

def ikb_class():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Эконом", callback_data="class:eco")],
        [InlineKeyboardButton(text="Комфорт", callback_data="class:cmf")],
        [InlineKeyboardButton(text="SUV", callback_data="class:suv")],
        [InlineKeyboardButton(text="Минивэн", callback_data="class:van")],
    ])

def ikb_gearbox():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Автомат", callback_data="gbx:AT"),
         InlineKeyboardButton(text="Механика", callback_data="gbx:MT")],
    ])

def ikb_results(items: list[dict], page: int, total_pages: int):
    rows = []
    for it in items:
        rows.append([InlineKeyboardButton(text=f"{it['title']} • {int(float(it['price_weekday']))} UZS",
                                          callback_data=f"car:{it['id']}")])
    nav = []
    if page > 1: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page-1}"))
    if page < total_pages: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page+1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def ikb_confirm(booking_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{booking_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{booking_id}")]
    ])

def ikb_price_skip():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="price:skip")]
    ])
