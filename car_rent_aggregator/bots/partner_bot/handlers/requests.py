# bots/partner_bot/handlers/requests.py
from __future__ import annotations

from datetime import datetime, timezone as _tz

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from bots.shared.api_client import ApiClient
from bots.shared.i18n import t

router = Router()

HOLD_MINUTES = 20  # дедлайн на подтверждение/отклонение


# ---------- helpers ----------

def _resolve_partner_lang() -> str:
    # пока только ru, в будущем можно хранить язык партнёра
    return "ru"

def _fmt_dt_short(iso: str) -> str:
    """
    "2025-10-25T10:00:00+05:00" -> "25.10.2025"
    """
    try:
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return iso[:10]

def _left_minutes(created_iso: str | None) -> int | None:
    """
    Сколько минут осталось до истечения HOLD_MINUTES.
    """
    if not created_iso:
        return None
    try:
        iso = created_iso
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        created = datetime.fromisoformat(iso).astimezone(_tz.utc)
    except Exception:
        return None

    now = datetime.now(_tz.utc)
    used_min = int((now - created).total_seconds() // 60)
    left = HOLD_MINUTES - used_min
    if left < 0:
        left = 0
    return left

def _human_status(lang: str, status_code: str) -> str:
    """
    Маппим статус -> локализованный текст.
    Ключи должны уже быть в твоих bot.ftl (status-pending, ...).
    """
    code = (status_code or "").lower()
    key = {
        "pending": "status-pending",
        "confirmed": "status-confirmed",
        "issued": "status-issued",
        "paid": "status-paid",
        "canceled": "status-canceled",
        "rejected": "status-rejected",
        "expired": "status-expired",
    }.get(code, code)
    return t(lang, key) if key else code

def _kb_request_actions(booking_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки "✅ Принять / ❌ Отклонить" для каждой заявки.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"rq:confirm:{booking_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"rq:reject:{booking_id}",
                ),
            ]
        ]
    )


# ---------- /requests команда ----------

@router.message(F.text == "/requests")
async def list_requests(m: Message, state: FSMContext):
    """
    Показываем партнёру pending-заявки с дедлайном.
    Каждую заявку отсылаем отдельным меседжем с кнопками.
    """
    lang = _resolve_partner_lang()

    if not m.from_user.username:
        return await m.answer("У вас не установлен username в Telegram.")

    api = ApiClient()
    try:
        items = await api.get(
            "/bookings/",
            params={
                "partner_username": m.from_user.username,
                "status": "pending",
            },
        )
    except Exception as e:
        await m.answer(f"Ошибка запроса: {e}")
        await api.close()
        return
    finally:
        await api.close()

    items = items or []
    if not items:
        return await m.answer("Новых заявок пока нет. Обновить: /requests")

    # сортируем свежие сверху
    items.sort(key=lambda b: b.get("created_at") or "", reverse=True)

    await m.answer("Новые заявки:")

    for b in items[:20]:
        bid = b["id"]
        car = b.get("car_title") or f"#{b.get('car')}"
        df = _fmt_dt_short(b.get("date_from", ""))
        dt = _fmt_dt_short(b.get("date_to", ""))
        status_txt = _human_status(lang, b.get("status", ""))

        left_min = _left_minutes(b.get("created_at"))
        ttl_line = f"\n⏳ Осталось примерно {left_min} мин. для ответа." if left_min is not None else ""

        text = (
            f"🆕 Заявка #{bid}\n"
            f"Авто: {car}\n"
            f"Период: {df}–{dt}\n"
            f"Статус: {status_txt}"
            f"{ttl_line}"
        )

        await m.answer(
            text,
            reply_markup=_kb_request_actions(bid),
        )


# ---------- confirm / reject callbacks ----------

@router.callback_query(F.data.startswith("rq:confirm:"))
async def cb_confirm(c: CallbackQuery, state: FSMContext):
    """
    Партнёр нажал "Принять".
    1) Делаем POST /bookings/{id}/confirm/
    2) Ответ уже содержит раскрытые данные клиента.
    3) Отдаём партнёру эти данные.
    """
    lang = _resolve_partner_lang()

    parts = c.data.split(":")
    booking_id = int(parts[2])

    api = ApiClient()
    try:
        payload = {}
        if c.from_user.username:
            payload["partner_username"] = c.from_user.username
        else:
            payload["partner_tg_user_id"] = c.from_user.id

        booking = await api.post(f"/bookings/{booking_id}/confirm/", json=payload)
    except Exception:
        await c.answer("Ошибка подтверждения", show_alert=True)
        await api.close()
        return
    finally:
        await api.close()

    car_title = booking.get("car_title") or f"#{booking.get('car')}"
    df = _fmt_dt_short(booking.get("date_from", ""))
    dt = _fmt_dt_short(booking.get("date_to", ""))

    # ДАННЫЕ КЛИЕНТА (теперь после confirm они должны быть раскрыты на бэке):
    fn = booking.get("client_first_name") or ""
    ln = booking.get("client_last_name") or ""
    un = booking.get("client_username") or ""
    ph = booking.get("client_phone") or ""

    client_block = (
        "👤 Клиент:\n"
        f"{fn} {ln}\n"
        f"@{un}\n"
        f"{ph}\n"
    ).strip()

    text = (
        f"✅ Заявка #{booking_id} подтверждена.\n"
        f"{car_title}\n"
        f"{df}–{dt}\n\n"
        f"{client_block}"
    )

    # пробуем отредактировать исходное сообщение (где были кнопки),
    # если не получится — шлём новое
    try:
        await c.message.edit_text(text, reply_markup=None)
    except Exception:
        await c.message.answer(text)

    await c.answer("Подтверждено ✅")


@router.callback_query(F.data.startswith("rq:reject:"))
async def cb_reject(c: CallbackQuery, state: FSMContext):
    """
    Партнёр нажал "Отклонить".
    1) POST /bookings/{id}/reject/
    2) Клиент НЕ раскрывается (и не должен раскрываться).
    """
    parts = c.data.split(":")
    booking_id = int(parts[2])

    api = ApiClient()
    try:
        payload = {}
        if c.from_user.username:
            payload["partner_username"] = c.from_user.username
        else:
            payload["partner_tg_user_id"] = c.from_user.id

        booking = await api.post(f"/bookings/{booking_id}/reject/", json=payload)
    except Exception:
        await c.answer("Ошибка отклонения", show_alert=True)
        await api.close()
        return
    finally:
        await api.close()

    car_title = booking.get("car_title") or f"#{booking.get('car')}"
    df = _fmt_dt_short(booking.get("date_from", ""))
    dt = _fmt_dt_short(booking.get("date_to", ""))

    text = (
        f"❌ Заявка #{booking_id} отклонена.\n"
        f"{car_title}\n"
        f"{df}–{dt}"
    )

    try:
        await c.message.edit_text(text, reply_markup=None)
    except Exception:
        await c.message.answer(text)

    await c.answer("Отклонено ❌")
