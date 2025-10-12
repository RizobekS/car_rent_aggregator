import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from bots.shared.api_client import ApiClient
from bots.shared.config import settings
from bots.shared.i18n import t, resolve_user_lang

PAYMENT_MSGS: dict[int, dict[int, list[int]]] = {}
CLIENT_BOOKING_STATUS: dict[int, dict[int, str]] = {}
HOLD_MINUTES = 20

def _fmt_date(iso: str) -> str:
    try:
        return _parse_dt(iso).astimezone(timezone.utc).strftime("%d.%m.%Y")
    except Exception:
        try:
            return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
        except Exception:
            return iso or "—"

def _parse_dt(iso: str) -> datetime:
    if not iso:
        raise ValueError("empty")
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    return datetime.fromisoformat(iso)

def _fmt_int(n) -> str:
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

def _kb_card_actions(lang: str, car_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn-more"),  callback_data=f"more:{car_id}"),
         InlineKeyboardButton(text=t(lang, "btn-terms"), callback_data=f"terms:{car_id}")],
        [InlineKeyboardButton(text=t(lang, "btn-reviews"), callback_data=f"reviews:{car_id}"),
         InlineKeyboardButton(text=t(lang, "btn-book"),    callback_data=f"pick:{car_id}")],
    ])

def build_car_caption(car: dict, lang: str) -> str:
    title = car.get('title') or t(lang, "card-fallback", caption="")

    year_part = f" ({car['year']})" if car.get("year") else ""
    mileage_part = f" • {_fmt_int(car['mileage_km'])} km" if car.get("mileage_km") else ""
    top = t(lang, "card-top", title=title, year_part=year_part, mileage_part=mileage_part)

    cls = car.get("car_class") or ""
    class_label = t(lang, "label-class", value=cls) if cls else ""
    drive_key = {"fwd":"drive-fwd","rwd":"drive-rwd","awd":"drive-awd"}.get(str(car.get("drive_type","")).lower(), "")
    drive_label = t(lang, drive_key) if drive_key else ""
    drive_part = f" • {t(lang, 'label-drive', value=drive_label)}" if drive_label else ""
    line2 = t(lang, "card-line2", class_label=class_label, drive_part=drive_part)

    hp = car.get("horsepower_hp")
    fuel_key = {"petrol":"fuel-petrol","diesel":"fuel-diesel","gas":"fuel-gas","hybrid":"fuel-hybrid","electric":"fuel-electric"}.get(str(car.get("fuel_type","")).lower(),"")
    fuel_label = t(lang, fuel_key) if fuel_key else ""
    cons = car.get("fuel_consumption_l_per_100km")
    parts = []
    if hp: parts.append(f"{_fmt_int(hp)} hp")
    if fuel_label: parts.append(fuel_label)
    if cons: parts.append(f"{cons} L/100 km")
    line3 = ("⛽ " + " • ".join(parts)) if parts else ""

    price = t(lang, "card-price", wd=_fmt_int(car.get('price_weekday') or 0), we=_fmt_int(car.get('price_weekend') or car.get('price_weekday') or 0))
    dep_amt = car.get("deposit_amount")
    dep_band = str(car.get("deposit_band") or "none").lower()
    deposit = (f"{_fmt_int(dep_amt)} UZS") if dep_amt else t(lang, {"none":"deposit-none","low":"deposit-low","high":"deposit-high"}.get(dep_band, "deposit-low"))
    limit = car.get("limit_km") or 0
    ins = t(lang, "ins-included") if car.get("insurance_included") else t(lang, "ins-excluded")
    terms = t(lang, "card-terms", deposit=deposit, limit=_fmt_int(limit), ins=ins)

    opts = []
    if car.get("child_seat"): opts.append(t(lang, "card-option-child"))
    if car.get("delivery"):   opts.append(t(lang, "card-option-delivery"))
    opts_block = t(lang, "card-options-title") + "\n" + "\n".join(opts) if opts else ""

    blocks = [top, line2, line3, "", price, "", terms]
    if opts_block: blocks.extend(["", opts_block])
    return "\n".join([b for b in blocks if b]).strip()

def _iter_days(start: datetime, end: datetime):
    for i in range((end - start).days):
        yield (start + timedelta(days=i)).date()

def _estimate_total(start_iso: str, end_iso: str, price_wd, price_we) -> int:
    start = _parse_dt(start_iso); end = _parse_dt(end_iso)
    total = 0.0
    for d in _iter_days(start, end):
        is_weekend = d.weekday() >= 5
        total += float(price_we or price_wd or 0) if is_weekend else float(price_wd or 0)
    return int(total)

def _kb_payment_choice(lang: str, booking_id: int, total: int, advance: int | None) -> InlineKeyboardMarkup:
    rows = []
    rows.append([InlineKeyboardButton(text=t(lang, "pay-full-btn", total=_fmt_int(total)), callback_data=f"pay:full:{booking_id}")])
    if advance and int(float(advance)) > 0:
        rows.append([InlineKeyboardButton(text=t(lang, "pay-adv-btn", adv=_fmt_int(advance)), callback_data=f"pay:adv:{booking_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def _send_suggestions(bot: Bot, chat_id: int, lang: str, *, date_from: str, date_to: str, car_class: str | None, partner_id: int | None):
    api = ApiClient()
    try:
        params = {"date_from": date_from, "date_to": date_to}
        if car_class: params["car_class"] = car_class
        cars = await api.get("/cars/search/", params=params)
    except Exception:
        cars = []
    finally:
        await api.close()

    if not isinstance(cars, list) or not cars:
        await bot.send_message(chat_id, t(lang, "suggest-none"))
        return

    same_partner, other_partners = [], []
    for c in cars:
        try:
            if partner_id and int(c.get("partner")) == int(partner_id): same_partner.append(c)
            else: other_partners.append(c)
        except Exception:
            other_partners.append(c)

    ordered = (same_partner + other_partners)[:5]
    await bot.send_message(chat_id, t(lang, "suggest-head"))

    root = Path(settings.media_root) if settings.media_root else None
    for car in ordered:
        caption = build_car_caption(car, lang)
        markup = _kb_card_actions(lang, int(car["id"]))
        sent = False
        if root and car.get("images_rel"):
            fp = root / car["images_rel"][0]
            if fp.exists():
                try:
                    await bot.send_photo(chat_id=chat_id, photo=FSInputFile(str(fp)), caption=caption, reply_markup=markup)
                    sent = True
                except Exception: sent = False
        if not sent and car.get("cover_url"):
            try:
                await bot.send_photo(chat_id=chat_id, photo=car["cover_url"], caption=caption, reply_markup=markup)
                sent = True
            except Exception: sent = False
        if not sent:
            await bot.send_message(chat_id, "📄 " + caption, reply_markup=markup)

    await bot.send_message(chat_id, t(lang, "suggest-tail", menu_find=t(lang, "menu-find")))

async def client_notify_loop(bot: Bot, chat_id: int):
    while True:
        try:
            api = ApiClient(); lang = await resolve_user_lang(api, chat_id); await api.close()

            api = ApiClient()
            items = await api.get("/bookings/", params={"client_tg_user_id": chat_id})
            await api.close()

            known = CLIENT_BOOKING_STATUS.setdefault(chat_id, {})

            now_utc = datetime.now(timezone.utc)
            for b in items:
                if b.get("status") != "pending": continue
                try:
                    created = _parse_dt(b.get("created_at", "")).astimezone(timezone.utc)
                except Exception:
                    continue
                if now_utc - created >= timedelta(minutes=HOLD_MINUTES):
                    try:
                        api2 = ApiClient()
                        await api2.post(f"/bookings/{b['id']}/cancel/", json={"client_tg_user_id": chat_id})
                        await api2.close()
                    except Exception:
                        pass

            # истёк TTL оплаты после подтверждения
            for b in list(items):
                try:
                    if b.get("status") != "confirmed":
                        continue
                    if (b.get("payment_marker") or "").lower() == "paid":
                        continue
                    upd = b.get("updated_at") or b.get("created_at")
                    if upd and upd.endswith("Z"): upd = upd[:-1] + "+00:00"
                    updated = _parse_dt(upd).astimezone(timezone.utc)
                    if now_utc - updated >= timedelta(minutes=HOLD_MINUTES):
                        try:
                            api2 = ApiClient()
                            await api2.post(f"/bookings/{b['id']}/cancel/", json={"client_tg_user_id": chat_id})
                            await api2.close()
                        except Exception:
                            pass
                except Exception:
                    pass

            api = ApiClient()
            items = await api.get("/bookings/", params={"client_tg_user_id": chat_id})
            await api.close()

            for b in items:
                bid = b.get("id"); st = b.get("status")
                if bid is None or st is None: continue
                prev = known.get(bid)

                title = b.get("car_title") or b.get("car") or ""
                dfrom = _fmt_date(b.get("date_from", "")); dto = _fmt_date(b.get("date_to", ""))

                car_class   = b.get("car_class")
                partner_id  = b.get("partner")
                price_wd    = b.get("price_weekday")
                price_we    = b.get("price_weekend")
                advance_amt = b.get("advance_amount")

                if prev is None:
                    known[bid] = st
                    if st in ("confirmed", "rejected", "expired", "canceled"):
                        if st == "confirmed":
                            total = _estimate_total(b["date_from"], b["date_to"], price_wd, price_we)
                            await bot.send_message(
                                chat_id,
                                t(lang, "notify-confirmed", id=bid, title=title, start=dfrom, end=dto),
                                reply_markup=_kb_payment_choice(lang, bid, total, advance_amt)
                            )
                        elif st == "rejected":
                            await bot.send_message(chat_id, t(lang, "notify-rejected", id=bid, title=title, start=dfrom, end=dto))
                            await _send_suggestions(bot, chat_id, lang, date_from=b.get("date_from",""), date_to=b.get("date_to",""), car_class=car_class, partner_id=partner_id)
                        else:
                            await bot.send_message(chat_id, t(lang, "notify-expired", id=bid, title=title, start=dfrom, end=dto))
                            await _send_suggestions(bot, chat_id, lang, date_from=b.get("date_from",""), date_to=b.get("date_to",""), car_class=car_class, partner_id=partner_id)
                    continue

                if prev != st:
                    known[bid] = st
                    if st == "confirmed":
                        total = _estimate_total(b["date_from"], b["date_to"], price_wd, price_we)
                        await bot.send_message(
                            chat_id,
                            t(lang, "notify-confirmed", id=bid, title=title, start=dfrom, end=dto),
                            reply_markup=_kb_payment_choice(lang, bid, total, advance_amt)
                        )
                    elif st == "rejected":
                        await bot.send_message(chat_id, t(lang, "notify-rejected", id=bid, title=title, start=dfrom, end=dto))
                        await _send_suggestions(bot, chat_id, lang, date_from=b.get("date_from",""), date_to=b.get("date_to",""), car_class=car_class, partner_id=partner_id)
                    elif st in ("expired", "canceled"):
                        await bot.send_message(chat_id, t(lang, "notify-expired", id=bid, title=title, start=dfrom, end=dto))
                        await _send_suggestions(bot, chat_id, lang, date_from=b.get("date_from",""), date_to=b.get("date_to",""), car_class=car_class, partner_id=partner_id)

                paid_now = (b.get("payment_marker") or "").lower() == "paid"

                # если оплата прошла — удаляем сохранённые сообщения с кнопками
                if paid_now:
                    try:
                        msg_ids = (PAYMENT_MSGS.get(chat_id) or {}).pop(bid, [])
                        for mid in msg_ids:
                            try:
                                await bot.delete_message(chat_id, mid)
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass

        await asyncio.sleep(20)

SUB_TASKS_CLIENT: dict[int, asyncio.Task] = {}
def ensure_client_subscription(bot: Bot, chat_id: int):
    tsk = SUB_TASKS_CLIENT.get(chat_id)
    if tsk and not tsk.done(): return
    SUB_TASKS_CLIENT[chat_id] = asyncio.create_task(client_notify_loop(bot, chat_id))
