from __future__ import annotations

import asyncio
from datetime import datetime, timezone as _tz
import aiohttp
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from bots.shared.api_client import ApiClient
from bots.shared.i18n import t

HOLD_MINUTES = 20

# какие заявки уже анонсировали партнёру как pending
SEEN_PENDING: dict[int, set[int]] = {}   # chat_id -> set(booking_ids)
# какие оплаты уже анонсировали как paid
SEEN_PAID: dict[int, set[int]] = {}      # chat_id -> set(booking_ids)


def _resolve_partner_lang() -> str:
    # пока жёстко RU, если надо — можно сделать хранение языка партнёра в БД
    return "ru"


def _fmt_date(iso: str) -> str:
    try:
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except Exception:
        return iso[:10]


def _left_minutes(created_iso: str | None) -> int | None:
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


def _kb_request_actions(bid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"rq:confirm:{bid}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"rq:reject:{bid}",
                ),
            ]
        ]
    )


async def _send_selfie_from_url(bot: Bot, chat_id: int, selfie_url: str) -> bool:
    """
    Качаем картинку по URL и отправляем её как файл.
    Используется в автопуллере для новых заявок.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(selfie_url) as resp:
                if resp.status != 200:
                    return False
                raw = await resp.read()
    except Exception:
        return False

    try:
        file = BufferedInputFile(raw, filename="selfie.jpg")
        await bot.send_photo(chat_id=chat_id, photo=file)
        return True
    except Exception:
        return False


async def _fetch_bookings(username: str | None, chat_id: int, status: str | None = None) -> list[dict]:
    """
    Универсальный helper:
      - если status задан -> фильтрация по статусу
      - если None -> без фильтра по статусу
    """
    api = ApiClient()
    params: dict[str, str | int] = {}
    if status:
        params["status"] = status

    if username:
        params["partner_username"] = username
    else:
        params["partner_tg_user_id"] = chat_id

    try:
        return await api.get("/bookings/", params=params)
    finally:
        await api.close()


async def _fetch_paid_bookings(username: str | None, chat_id: int) -> list[dict]:
    """
    Получаем брони партнёра, у которых payment_marker = 'paid'.
    Статус брони (confirmed/completed/...) неважен.
    """
    items = await _fetch_bookings(username, chat_id, status=None)
    result: list[dict] = []
    for b in items:
        pm = (b.get("payment_marker") or "").lower()
        if pm == "paid":
            result.append(b)
    return result


async def notify_loop(bot: Bot, chat_id: int, username: str | None):
    """
    Каждые 20 сек:
      • новые pending заявки -> карточка с кнопками ✅/❌
      • новые оплаченные заявки (payment_marker=paid) -> уведомление об оплате
    """
    lang = _resolve_partner_lang()

    while True:
        try:
            # ---- pending заявки
            pendings = await _fetch_bookings(username, chat_id, status="pending")
            seen_p = SEEN_PENDING.setdefault(chat_id, set())
            for b in pendings:
                bid = b["id"]
                if bid in seen_p:
                    continue
                seen_p.add(bid)

                car = b.get("car_title") or f"#{b.get('car')}"
                df = _fmt_date(b.get("date_from", ""))
                dt = _fmt_date(b.get("date_to", ""))

                left_min = _left_minutes(b.get("created_at"))
                ttl_line = ""
                if left_min is not None:
                    ttl_line = f"\n⏳ Осталось ~{left_min} мин."

                age = b.get("client_age_years")
                drive_exp = b.get("client_drive_exp")

                client_line = ""
                parts = []
                if age:
                    parts.append(f"Возраст клиента: {age}")
                if drive_exp:
                    parts.append(f"Стаж вождения: {drive_exp} лет")
                if parts:
                    client_line = "\n" + " | ".join(parts)

                text = (
                    f"🆕 Новая заявка #{bid}\n"
                    f"Авто: {car}\n"
                    f"{df}–{dt}"
                    f"{ttl_line}"
                    f"{client_line}"
                )

                # 🧠 сначала пробуем отправить селфи клиента, если есть
                selfie_url = b.get("client_selfie_url")
                if selfie_url:
                    await _send_selfie_from_url(bot, chat_id, selfie_url)

                # затем сама карточка заявки
                await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=_kb_request_actions(bid),
                )

            # ---- оплаченные заявки (payment_marker=paid)
            paids = await _fetch_paid_bookings(username, chat_id)
            seen_paid = SEEN_PAID.setdefault(chat_id, set())
            for b in paids:
                bid = b["id"]
                if bid in seen_paid:
                    continue
                seen_paid.add(bid)

                car = b.get("car_title") or f"#{b.get('car')}"
                df = _fmt_date(b.get("date_from", ""))
                dt = _fmt_date(b.get("date_to", ""))
                mode = (b.get("payment_mode") or "").lower()
                if mode == "adv":
                    mode_txt = "аванс"
                else:
                    mode_txt = "полная оплата"

                await bot.send_message(
                    chat_id,
                    f"💸 Клиент оплатил заявку #{bid}\n"
                    f"Авто: {car}\n"
                    f"{df}–{dt}"
                )

        except Exception:
            # не убиваем цикл даже при ошибках
            pass

        await asyncio.sleep(20)


SUB_TASKS: dict[int, asyncio.Task] = {}


def subscribe_partner(bot: Bot, chat_id: int, username: str | None):
    """
    Включаем фоновые уведомления. Если задача уже есть — ничего не делаем.
    """
    tsk = SUB_TASKS.get(chat_id)
    if tsk and not tsk.done():
        return False
    SUB_TASKS[chat_id] = asyncio.create_task(notify_loop(bot, chat_id, username))
    return True


def unsubscribe_partner(chat_id: int):
    tsk = SUB_TASKS.get(chat_id)
    if tsk and not tsk.done():
        tsk.cancel()
        return True
    return False
