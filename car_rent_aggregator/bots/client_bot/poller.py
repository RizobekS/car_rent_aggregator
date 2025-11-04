# bots/client_bot/poller.py
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from bots.shared.api_client import ApiClient
from bots.shared.config import settings
from bots.shared.i18n import t, resolve_user_lang

# chat_id -> { booking_id -> [message_id, ...] }
PAYMENT_MSGS: Dict[int, Dict[int, List[int]]] = {}

# антиспам статусов:
# chat_id -> { booking_id: "status|updated_at|payment_marker" }
_STATUS_CACHE: Dict[int, Dict[int, str]] = {}

# чтобы не слать старые pending/confirmed при старте бота
BOOT_CUTOFF: Dict[int, datetime] = {}

# явно отслеживаемые только что созданные заявки пользователя
TRACK_BOOKINGS: Dict[int, set[int]] = {}

POLL_INTERVAL_SEC = 20
HOLD_MINUTES = 20  # TTL ожидания оплаты после подтверждения


# ────────── утилиты времени/формата ──────────
def _parse_dt(iso: str) -> datetime:
    if not iso:
        return datetime.now(timezone.utc)
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(iso).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _fmt_date(iso: str, lang: str) -> str:
    dt = _parse_dt(iso)
    return dt.strftime("%Y-%m-%d") if lang == "en" else dt.strftime("%d.%m.%Y")


def _fmt_int(n: Any) -> str:
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except Exception:
        return str(n)


# ────────── расчёт суммы аренды (будни/выходные) ──────────
def _estimate_total(date_from_iso: str, date_to_iso: str, price_wd, price_we) -> int:
    start = _parse_dt(date_from_iso)
    end = _parse_dt(date_to_iso)
    wd = float(price_wd or 0)
    we = float(price_we or price_wd or 0)
    total = 0.0
    d = start
    while d < end:
        total += we if d.weekday() >= 5 else wd
        d += timedelta(days=1)
    return int(total)


# ────────── клавиатура для рекомендованных машин ──────────
def _kb_reco(lang: str, car_id: int, date_from: str, date_to: str) -> InlineKeyboardMarkup:
    """
    Это клавиатура под рекомендацией, которую мы шлём если бронь
    отклонена или истекла.
    Раньше тут был небольшой баг по структуре inline_keyboard.
    Aiogram ожидает список списков кнопок.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn-more"),
                    callback_data=f"sug:more:{car_id}"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn-terms"),
                    callback_data=f"sug:terms:{car_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn-reviews"),
                    callback_data=f"reviews:{car_id}"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn-book"),
                    callback_data=f"sug:book:{car_id}:{date_from}:{date_to}"
                ),
            ],
        ]
    )


def _car_caption(lang: str, car: dict) -> str:
    """
    Текст карточки для рекомендаций:
    тот же стиль, что и в поиске (иконки, тех.инфа, цены).
    """
    title = car.get("title") or t(lang, "card-fallback", caption="")
    year_part = f" ({car['year']})" if car.get("year") else ""
    mileage_part = f" • {_fmt_int(car['mileage_km'])} km" if car.get("mileage_km") else ""
    top = t(lang, "card-top", title=title, year_part=year_part, mileage_part=mileage_part)

    # класс / привод
    cls = car.get("car_class") or ""
    class_label = t(lang, "label-class", value=cls) if cls else ""
    drive_key = {
        "fwd": "drive-fwd",
        "rwd": "drive-rwd",
        "awd": "drive-awd",
    }.get(str(car.get("drive_type", "")).lower(), "")
    drive_label = t(lang, drive_key) if drive_key else ""
    drive_part = f" • {t(lang, 'label-drive', value=drive_label)}" if drive_label else ""

    line2 = t(
        lang,
        "card-line2",
        class_label=class_label,
        drive_part=drive_part,
    )

    # мощность / топливо / расход
    hp = car.get("horsepower_hp")
    fuel_key = {
        "petrol": "fuel-petrol",
        "diesel": "fuel-diesel",
        "gas": "fuel-gas",
        "hybrid": "fuel-hybrid",
        "electric": "fuel-electric",
    }.get(str(car.get("fuel_type", "")).lower(), "")
    fuel_label = t(lang, fuel_key) if fuel_key else ""
    cons = car.get("fuel_consumption_l_per_100km")

    parts = []
    if hp:
        parts.append(f"{_fmt_int(hp)} hp")
    if fuel_label:
        parts.append(fuel_label)
    if cons:
        parts.append(f"{cons} L/100 km")
    line3 = ("⛽ " + " • ".join(parts)) if parts else ""

    # цены
    price_block = t(
        lang,
        "card-price",
        wd=_fmt_int(car.get("price_weekday") or 0),
        we=_fmt_int(car.get("price_weekend") or car.get("price_weekday") or 0),
    )

    # аванс / лимит / страховка
    dep_amt = car.get("advance_amount") or car.get("deposit_amount")
    dep_text = f"{_fmt_int(dep_amt)} UZS" if dep_amt else t(lang, "deposit-none")

    limit = car.get("limit_km") or 0
    ins = t(lang, "ins-included") if car.get("insurance_included") else t(lang, "ins-excluded")
    terms = t(
        lang,
        "card-terms",
        deposit=dep_text,
        limit=_fmt_int(limit),
        ins=ins,
    )

    # опции
    opts = []
    if car.get("child_seat"):
        opts.append(t(lang, "card-option-child"))
    if car.get("delivery"):
        opts.append(t(lang, "card-option-delivery"))
    opts_block = (t(lang, "card-options-title") + "\n" + "\n".join(opts)) if opts else ""

    blocks = [top, line2, line3, "", price_block, "", terms]
    if opts_block:
        blocks.extend(["", opts_block])

    return "\n".join([b for b in blocks if b]).strip()


async def _api_get_bookings(chat_id: int) -> list[dict]:
    api = ApiClient()
    try:
        data = await api.get("/bookings/", params={"client_tg_user_id": chat_id})
        return data if isinstance(data, list) else []
    finally:
        await api.close()


async def _api_search_reco(date_from: str, date_to: str, car_class: str | None) -> list[dict]:
    """
    Ищем альтернативные машины:
    - те же даты
    - тот же класс, если есть
    - не фильтруем по партнёру (по запросу заказчика!)
    - максимум 5 штук отдадим дальше
    """
    api = ApiClient()
    try:
        params: dict[str, Any] = {"date_from": date_from, "date_to": date_to}
        if car_class:
            params["car_class"] = car_class
        items = await api.get("/cars/search/", params=params)
        return items if isinstance(items, list) else []
    finally:
        await api.close()


async def _send_recommendations(bot: Bot, chat_id: int, lang: str, *, date_from: str, date_to: str, car_class: str | None):
    """
    Шлём клиенту похожие машины после отклонения/истечения.
    Если машин нет — уведомляем, что нет альтернатив.
    """
    cars = (await _api_search_reco(date_from, date_to, car_class))[:5]

    if not cars:
        try:
            await bot.send_message(chat_id, t(lang, "suggest-none"))
        except Exception:
            pass
        return

    # заголовок блока рекомендаций
    try:
        await bot.send_message(chat_id, t(lang, "suggest-head"))
    except Exception:
        pass

    media_root = Path(settings.media_root) if getattr(settings, "media_root", None) else None

    for car in cars:
        caption = _car_caption(lang, car)
        kb = _kb_reco(lang, int(car["id"]), date_from, date_to)

        sent = False

        # сначала пробуем локальную картинку
        if media_root and car.get("images_rel"):
            fp = media_root / car["images_rel"][0]
            if fp.exists():
                try:
                    await bot.send_photo(
                        chat_id,
                        FSInputFile(str(fp)),
                        caption=caption,
                        reply_markup=kb,
                    )
                    sent = True
                except Exception:
                    sent = False

        # если не получилось — пробуем cover_url
        if not sent and car.get("cover_url"):
            try:
                await bot.send_photo(
                    chat_id,
                    car["cover_url"],
                    caption=caption,
                    reply_markup=kb,
                )
                sent = True
            except Exception:
                sent = False

        # если вообще без фото
        if not sent:
            try:
                await bot.send_message(
                    chat_id,
                    "📄 " + caption,
                    reply_markup=kb,
                )
            except Exception:
                pass


# ────────── кнопки выбора типа оплаты ──────────
def _kb_pay_choice(lang: str, booking_id: int, adv_amount: int | None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t(lang, "pay-mode-full"),
                callback_data=f"pay:full:{booking_id}",
            )
        ]
    ]
    if adv_amount and int(adv_amount) > 0:
        rows.append([
            InlineKeyboardButton(
                text=t(lang, "pay-mode-adv"),
                callback_data=f"pay:adv:{booking_id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _remove_payment_kb(bot: Bot, chat_id: int, bid: int):
    """
    Убираем inline-кнопки «Оплатить», чтобы после оплаты
    клиент не мог повторно нажимать.
    """
    try:
        ids = PAYMENT_MSGS.get(chat_id, {}).get(bid, [])
        for mid in ids:
            try:
                await bot.edit_message_reply_markup(chat_id, mid, reply_markup=None)
            except Exception:
                pass
        if ids:
            PAYMENT_MSGS.get(chat_id, {}).pop(bid, None)
    except Exception:
        pass


# ────────── основной цикл уведомлений клиента ──────────
async def _client_loop(bot: Bot, chat_id: int):
    """
    Логика:
    - следим за статусами всех броней клиента;
    - отправляем уведомление только 1 раз на (статус|updated_at|payment_marker);
    - при confirmed -> предлагаем оплату, если ещё не оплачено;
    - при rejected/expired -> отправляем рекомендации (исправили клавиатуру);
    - при paid -> благодарим и чистим кнопки оплаты.
    Не трогаем старые брони до запуска (BOOT_CUTOFF),
    кроме важных статусов и заявок из TRACK_BOOKINGS.
    """

    BOOT_CUTOFF[chat_id] = datetime.now(timezone.utc)
    cache = _STATUS_CACHE.setdefault(chat_id, {})
    track = TRACK_BOOKINGS.setdefault(chat_id, set())

    # пробуем заранее получить язык
    api_lang = ApiClient()
    lang = await resolve_user_lang(api_lang, chat_id)
    await api_lang.close()

    while True:
        try:
            items = await _api_get_bookings(chat_id)
            now_utc = datetime.now(timezone.utc)

            for b in items:
                bid = int(b.get("id"))
                status = (b.get("status") or "").lower()
                updated = _parse_dt(b.get("updated_at") or b.get("created_at") or "")
                pmark = (b.get("payment_marker") or "").lower()

                # подтягиваем актуальный язык каждый цикл
                api_l = ApiClient()
                lang = await resolve_user_lang(api_l, chat_id)
                await api_l.close()

                # ключ антиспама
                version = f"{status}|{updated.isoformat()}|{pmark}"

                if cache.get(bid) == version:
                    # мы уже уведомляли об этом состоянии
                    continue

                is_old = updated <= BOOT_CUTOFF.get(chat_id, now_utc)
                is_tracked = bid in track
                important_status = status in ("confirmed", "rejected", "expired", "paid")

                # не шлём старый мусор (например старые pending),
                # но зафиксируем, чтобы в будущем не всплыло
                if is_old and (not is_tracked) and (not important_status):
                    cache.setdefault(bid, version)
                    continue

                # теперь точно будем уведомлять -> фиксируем версию сразу
                cache[bid] = version

                title = b.get("car_title") or ""
                dfrom = _fmt_date(b.get("date_from", ""), lang)
                dto = _fmt_date(b.get("date_to", ""), lang)

                # ====== РАЗВЕТВЛЕНИЕ ПО СТАТУСАМ ======

                if status == "confirmed":
                    # 1. Сообщаем, что партнёр подтвердил
                    try:
                        await bot.send_message(
                            chat_id,
                            t(lang, "notify-confirmed",
                              id=bid, title=title, start=dfrom, end=dto)
                        )
                    except Exception:
                        pass

                    # 2. Если ещё не оплачено — предлагаем оплату
                    if pmark != "paid":
                        adv_amount = int(float(b.get("advance_amount") or 0)) or None
                        total = _estimate_total(
                            b.get("date_from", ""),
                            b.get("date_to", ""),
                            b.get("price_weekday"),
                            b.get("price_weekend"),
                        )
                        pay_text = (
                            t(lang, "pay-choose", id=bid)
                            + f"\n≈ {_fmt_int(total)} UZS"
                        )
                        kb = _kb_pay_choice(lang, bid, adv_amount)
                        sent_msg = await bot.send_message(chat_id, pay_text, reply_markup=kb)
                        PAYMENT_MSGS.setdefault(chat_id, {}).setdefault(bid, []).append(sent_msg.message_id)

                elif status == "rejected":
                    # 1. Сообщаем отказ
                    try:
                        await bot.send_message(
                            chat_id,
                            t(lang, "notify-rejected",
                              id=bid, title=title, start=dfrom, end=dto)
                        )
                    except Exception:
                        pass

                    # 2. Убираем кнопки оплаты на всякий случай
                    await _remove_payment_kb(bot, chat_id, bid)

                    # 3. Присылаем похожие варианты (фикс клавиатуры)
                    await _send_recommendations(
                        bot,
                        chat_id,
                        lang,
                        date_from=b.get("date_from", ""),
                        date_to=b.get("date_to", ""),
                        car_class=b.get("car_class"),
                    )

                    # 4. больше не трекаем эту бронь
                    track.discard(bid)

                elif status == "expired":
                    # 1. Сообщаем клиенту, что время истекло
                    try:
                        await bot.send_message(
                            chat_id,
                            t(lang, "notify-expired",
                              id=bid, title=title, start=dfrom, end=dto)
                        )
                    except Exception:
                        pass

                    # 2. Убираем кнопки оплаты
                    await _remove_payment_kb(bot, chat_id, bid)

                    # 3. Похожие машины
                    await _send_recommendations(
                        bot,
                        chat_id,
                        lang,
                        date_from=b.get("date_from", ""),
                        date_to=b.get("date_to", ""),
                        car_class=b.get("car_class"),
                    )

                    track.discard(bid)

                elif status == "paid":
                    # клиент уже оплатил (аванс или полную)
                    try:
                        await bot.send_message(
                            chat_id,
                            t(lang, "status-paid",
                              id=bid, title=title)
                        )
                    except Exception:
                        pass

                    # прячем кнопки оплаты
                    await _remove_payment_kb(bot, chat_id, bid)
                    track.discard(bid)

                # авто-отмена неподтверждённой оплаты
                if status == "confirmed" and pmark != "paid":
                    minutes_passed = int((now_utc - updated).total_seconds() // 60)
                    if minutes_passed >= HOLD_MINUTES:
                        # отменяем бронь через API (как раньше)
                        try:
                            api = ApiClient()
                            await api.post(
                                f"/bookings/{bid}/cancel/",
                                json={"client_tg_user_id": chat_id},
                            )
                            await api.close()
                        except Exception:
                            pass

        except Exception:
            # не валим цикл из-за исключения
            pass

        await asyncio.sleep(POLL_INTERVAL_SEC)


# ────────── публичный интерфейс для запуска фонового цикла ──────────
SUB_TASKS_CLIENT: Dict[int, asyncio.Task] = {}


def ensure_client_subscription(bot: Bot, chat_id: int):
    """
    Запускаем (или не дублируем) фонового воркера по уведомлениям клиента.
    """
    task = SUB_TASKS_CLIENT.get(chat_id)
    if task and not task.done():
        return
    BOOT_CUTOFF[chat_id] = datetime.now(timezone.utc)
    TRACK_BOOKINGS.setdefault(chat_id, set())
    SUB_TASKS_CLIENT[chat_id] = asyncio.create_task(_client_loop(bot, chat_id))
