from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bots.shared.api_client import ApiClient

router = Router()

def ikb_request_actions(bid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"pconfirm:{bid}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"preject:{bid}")],
    ])

@router.message(F.text == "/requests")
async def list_requests(m: Message):
    api = ApiClient()
    params = {"status": "pending", "fresh_minutes": 60}
    if m.from_user.username:
        params["partner_username"] = m.from_user.username
    else:
        params["partner_tg_user_id"] = m.from_user.id

    try:
        items = await api.get("/bookings/", params=params)
    except Exception as e:
        await m.answer(f"Ошибка загрузки заявок: {e}")
        await api.close()
        return
    finally:
        await api.close()

    if not items:
        return await m.answer("Новых заявок пока нет. Обновить: /requests")

    # В списке клиента НЕ показываем (бэк уже маскирует, но и сами не печатаем)
    for b in items[:20]:
        text = (f"#{b['id']} • {b['car_title']}\n"
                f"{b['date_from'][:10]}→{b['date_to'][:10]}")
        await m.answer(text, reply_markup=ikb_request_actions(b["id"]))

@router.callback_query(F.data.startswith("pconfirm:"))
async def partner_confirm(c: CallbackQuery):
    bid = int(c.data.split(":")[1])
    api = ApiClient()
    payload = {"partner_username": c.from_user.username} if c.from_user.username else {"partner_tg_user_id": c.from_user.id}
    try:
        # 1) подтверждаем
        resp = await api.post(f"/bookings/{bid}/confirm/", json=payload)
        # 2) перезапрос сведений (на случай кэширования/контекста — добавим партнёрские параметры)
        details = await api.get(f"/bookings/{bid}/", params=payload)
    except Exception as e:
        await c.message.answer(f"Не удалось подтвердить: {e}")
        await api.close()
        await c.answer()
        return
    finally:
        await api.close()

    # После подтверждения клиент раскрыт — покажем ФИО/тел/юзернейм
    d = details
    client_info = []
    if d.get("client_first_name") or d.get("client_last_name"):
        client_info.append(f"{(d.get('client_first_name') or '')} {(d.get('client_last_name') or '')}".strip())
    if d.get("client_phone"):
        client_info.append(d["client_phone"])
    if d.get("client_username"):
        client_info.append(f"@{d['client_username']}")

    info_line = "\nКлиент: " + " • ".join([x for x in client_info if x]) if client_info else ""
    await c.message.edit_text(f"Подтверждено ✅\n#{d['id']} • {d['car_title']}\n"
                              f"{d['date_from'][:10]}→{d['date_to'][:10]}{info_line}")
    await c.answer()

@router.callback_query(F.data.startswith("preject:"))
async def partner_reject(c: CallbackQuery):
    bid = int(c.data.split(":")[1])
    api = ApiClient()
    payload = {"partner_username": c.from_user.username} if c.from_user.username else {"partner_tg_user_id": c.from_user.id}
    try:
        resp = await api.post(f"/bookings/{bid}/reject/", json=payload)
    except Exception as e:
        await c.message.answer(f"Не удалось отклонить: {e}")
    finally:
        await api.close()
    await c.message.edit_text("Отклонено ❌")
    await c.answer()
