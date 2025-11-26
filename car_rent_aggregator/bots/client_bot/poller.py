# bots/client_bot/poller.py
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bots.shared.api_client import ApiClient
from bots.shared.config import settings
from bots.shared.i18n import t, resolve_user_lang
from bots.shared.logger import setup_logging

log = setup_logging("client-poller")

# chat_id -> { booking_id -> [message_id, ...] }
PAYMENT_MSGS: Dict[int, Dict[int, List[int]]] = {}

# chat_id -> { booking_id -> last_status }
CLIENT_BOOKING_STATUS: Dict[int, Dict[int, str]] = {}

# Время жизни неподтверждённой/неоплаченной заявки (минуты)
HOLD_MINUTES = 20

# явно отслеживаемые только что созданные заявки пользователя
TRACK_BOOKINGS: Dict[int, set[int]] = {}

def _parse_dt(iso: str) -> Optional[datetime]:
    """
    Безопасный парсер ISO-дат, поддерживает 'Z' и offset.
    Если не получилось — None.
    """
    if not iso:
        return None
    s = iso
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _fmt_date(iso: str) -> str:
    """
    Красивый формат даты для пользователя: DD.MM.YYYY.
    Если дата кривая — возвращаем как есть.
    """
    dt = _parse_dt(iso)
    if not dt:
        return iso or "—"
    return dt.astimezone(timezone.utc).strftime("%d.%m.%Y")


def _fmt_int(n: Any) -> str:
    """Число с пробелами как разделителями тысяч."""
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

def kb_payment(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "menu-pay"))],
                  [KeyboardButton(text=t(lang, "menu-find"))]],
        resize_keyboard=True
    )



async def _send_suggestions(
    bot: Bot,
    chat_id: int,
    lang: str,
    *,
    date_from: str,
    date_to: str,
    car_class: Optional[str],
    partner_id: Optional[int],
) -> None:
    """
    Подбираем до 5 похожих авто в том же классе:
      1) сначала машины того же партнёра (если указан),
      2) затем другие партнёры.
    """
    api = ApiClient()
    try:
        params = {"date_from": date_from, "date_to": date_to}
        if car_class:
            params["car_class"] = car_class

        cars = await api.get("/cars/search/", params=params)
    except Exception:
        cars = []
    finally:
        await api.close()

    if not isinstance(cars, list) or not cars:
        await bot.send_message(
            chat_id,
            t(lang, "client-booking-suggest-empty"),
        )
        return

    same_partner: List[dict] = []
    other_partners: List[dict] = []

    for c in cars:
        try:
            if partner_id and int(c.get("partner")) == int(partner_id):
                same_partner.append(c)
            else:
                other_partners.append(c)
        except Exception:
            other_partners.append(c)

    ordered = (same_partner + other_partners)[:5]

    # Строим блок с вариантами
    lines: List[str] = []
    for c in ordered:
        title = c.get("title", "Car")
        wd_raw = c.get("price_weekday") or 0
        we_raw = c.get("price_weekend") or wd_raw

        lines.append(
            t(
                lang,
                "client-booking-suggest-item",
                title=title,
                price_weekday=_fmt_int(wd_raw),
                price_weekend=_fmt_int(we_raw),
            )
        )

    cars_block = "\n".join(lines)

    await bot.send_message(
        chat_id,
        t(
            lang,
            "client-booking-suggest-list",
            cars=cars_block,
        ),
    )


async def client_notify_loop(bot: Bot, chat_id: int) -> None:
    """
    Каждые ~20 секунд:
      1) Подтягиваем брони клиента.
      2) Автоматически аннулируем старые pending (>= HOLD_MINUTES).
      3) Отлавливаем смену статуса и шлём уведомления:

         • pending  -> ничего не шлём.
         • confirmed -> "заявка подтверждена" (ОТДЕЛЬНО от оплаты).
         • paid      -> "оплата успешно прошла".
         • rejected  -> "заявка отклонена" + похожие авто.
         • expired / canceled -> "истёк срок / отменено" + похожие авто.

      Важно: на переходе в paid мы больше НЕ дублируем текст про подтверждение.
    """
    while True:
        try:
            api = ApiClient()
            try:
                lang = await resolve_user_lang(api, chat_id, {})
            except Exception:
                lang = "ru"
            try:
                items = await api.get("/bookings/", params={"client_tg_user_id": chat_id})
            finally:
                await api.close()

            known = CLIENT_BOOKING_STATUS.setdefault(chat_id, {})

            # 2) авто-аннуляция старых pending
            now_utc = datetime.now(timezone.utc)
            for b in items:
                if b.get("status") != "pending":
                    continue

                created = _parse_dt(b.get("created_at", ""))
                if not created:
                    continue

                created_utc = created.astimezone(timezone.utc)
                if now_utc - created_utc >= timedelta(minutes=HOLD_MINUTES):
                    # сервер переведёт бронь в canceled
                    try:
                        api2 = ApiClient()
                        await api2.post(
                            f"/bookings/{b['id']}/cancel/",
                            json={"client_tg_user_id": chat_id},
                        )
                        await api2.close()
                    except Exception:
                        # молчим, попробуем в следующий цикл
                        pass

            # 3) перечитываем, чтобы увидеть обновлённые статусы после авто-отмен
            api = ApiClient()
            items = await api.get("/bookings/", params={"client_tg_user_id": chat_id})
            await api.close()

            # 4) анализ смены статусов
            for b in items:
                bid = b.get("id")
                st = b.get("status")
                pm = (b.get("payment_marker") or "").lower()
                if bid is None or st is None:
                    continue

                state = f"{st}|{pm}"
                prev = known.get(bid)
                title = b.get("car_title") or b.get("car") or "—"
                dfrom_iso = b.get("date_from", "")
                dto_iso = b.get("date_to", "")
                dfrom = _fmt_date(dfrom_iso)
                dto = _fmt_date(dto_iso)
                car_class = b.get("car_class")
                partner_id = b.get("partner")

                partner_name = b.get("partner_name") or ""
                partner_phone = b.get("partner_phone") or ""
                partner_address = b.get("partner_address") or ""

                # первое появление брони в кеше
                if prev is None:
                    # запоминаем полное состояние: статус + маркер оплаты
                    known[bid] = state

                    if pm == "paid":
                        await bot.send_message(
                            chat_id,
                            t(
                                lang,
                                "client-booking-paid",
                                id=bid,
                                title=title,
                                date_from=dfrom,
                                date_to=dto,
                                partner_name=partner_name,
                                partner_phone=partner_phone,
                                partner_address=partner_address,
                            ),
                        )
                        log.info("Booking %s for chat %s initial state %s (marker=paid)", bid, chat_id, st)

                    elif st == "confirmed":
                        await bot.send_message(
                            chat_id,
                            t(
                                lang,
                                "client-booking-confirmed",
                                id=bid,
                                title=title,
                                date_from=dfrom,
                                date_to=dto,
                            ),
                            reply_markup=kb_payment(lang)
                        )
                        log.info("Booking %s for chat %s initial status confirmed", bid, chat_id)

                    elif st == "rejected":
                        await bot.send_message(
                            chat_id,
                            t(
                                lang,
                                "client-booking-rejected",
                                id=bid,
                                title=title,
                                date_from=dfrom,
                                date_to=dto,
                            ),
                        )
                        await _send_suggestions(
                            bot,
                            chat_id,
                            lang,
                            date_from=dfrom_iso,
                            date_to=dto_iso,
                            car_class=car_class,
                            partner_id=partner_id,
                        )
                        log.info("Booking %s for chat %s initial status rejected", bid, chat_id)

                    elif st in ("expired", "canceled"):
                        await bot.send_message(
                            chat_id,
                            t(
                                lang,
                                "client-booking-expired",
                                id=bid,
                                title=title,
                                date_from=dfrom,
                                date_to=dto,
                            ),
                        )
                        await _send_suggestions(
                            bot,
                            chat_id,
                            lang,
                            date_from=dfrom_iso,
                            date_to=dto_iso,
                            car_class=car_class,
                            partner_id=partner_id,
                        )
                        log.info("Booking %s for chat %s initial status %s", bid, chat_id, st)

                    continue

                # если состояние (status + payment_marker) не изменилось — ничего не шлём
                if prev == state:
                    continue

                # состояние изменилось
                known[bid] = state

                # 1) успешная оплата — реагируем на payment_marker
                if pm == "paid" and (prev is None or not prev.endswith("|paid")):
                    await bot.send_message(
                        chat_id,
                        t(
                            lang,
                            "client-booking-paid",
                            id=bid,
                            title=title,
                            date_from=dfrom,
                            date_to=dto,
                            partner_name=partner_name,
                            partner_phone=partner_phone,
                            partner_address=partner_address,
                        ),
                    )
                elif st == "confirmed":
                    await bot.send_message(
                        chat_id,
                        t(
                            lang,
                            "client-booking-confirmed",
                            id=bid,
                            title=title,
                            date_from=dfrom,
                            date_to=dto,
                        ),
                        reply_markup=kb_payment(lang)
                    )

                elif st == "rejected":
                    # ОТКЛОНЕНО ПАРТНЁРОМ
                    # client-booking-rejected + затем похожие варианты
                    await bot.send_message(
                        chat_id,
                        t(
                            lang,
                            "client-booking-rejected",
                            id=bid,
                            title=title,
                            date_from=dfrom,
                            date_to=dto,
                        ),
                    )
                    await _send_suggestions(
                        bot,
                        chat_id,
                        lang,
                        date_from=dfrom_iso,
                        date_to=dto_iso,
                        car_class=car_class,
                        partner_id=partner_id,
                    )

                elif st in ("expired", "canceled"):
                    # ИСТЁК СРОК ОЖИДАНИЯ / ОТМЕНЕНО
                    # client-booking-expired
                    await bot.send_message(
                        chat_id,
                        t(
                            lang,
                            "client-booking-expired",
                            id=bid,
                            title=title,
                            date_from=dfrom,
                            date_to=dto,
                        ),
                    )
                    await _send_suggestions(
                        bot,
                        chat_id,
                        lang,
                        date_from=dfrom_iso,
                        date_to=dto_iso,
                        car_class=car_class,
                        partner_id=partner_id,
                    )


        except Exception as e:

            # логируем любые ошибки в поллере, чтобы не отлавливать их по ощущениям

            log.exception("client_notify_loop error for chat_id=%s: %r", chat_id, e)

        await asyncio.sleep(20)


SUB_TASKS_CLIENT: Dict[int, asyncio.Task] = {}


def ensure_client_subscription(bot: Bot, chat_id: int) -> None:
    """
    Запускаем фоновую задачу уведомлений для клиента, если она ещё не запущена.
    Вызывается из /start.
    """
    t = SUB_TASKS_CLIENT.get(chat_id)
    if t and not t.done():
        return
    SUB_TASKS_CLIENT[chat_id] = asyncio.create_task(client_notify_loop(bot, chat_id))
