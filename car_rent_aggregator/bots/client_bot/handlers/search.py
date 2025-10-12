# bots/client_bot/handlers/search.py
from pathlib import Path
from datetime import datetime, date, timedelta
import calendar

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, FSInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from bots.shared.api_client import ApiClient
from bots.shared.config import settings
from bots.client_bot.states import SearchStates, BookingStates
from bots.client_bot.handlers.start import is_find_btn, kb_request_phone
from bots.shared.i18n import t, resolve_user_lang
from bots.client_bot.poller import ensure_client_subscription

router = Router()

# ---------- служебные форматтеры ----------
def fmt_int(n) -> str:
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

# ---------- календарь ----------
def month_title(y: int, m: int, lang: str) -> str:
    return f"{y}-{m:02d}"

def build_calendar(year: int, month: int, lang: str, min_sel: date | None = None, disable_to: date | None = None) -> InlineKeyboardMarkup:
    cal = calendar.Calendar(firstweekday=0)
    rows = []
    prev_month = (date(year, month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(year, month, 28) + timedelta(days=7)).replace(day=1)
    rows.append([
        InlineKeyboardButton(text="◀️", callback_data=f"cal:nav:{prev_month.year}:{prev_month.month}"),
        InlineKeyboardButton(text=month_title(year, month, lang), callback_data="cal:noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:nav:{next_month.year}:{next_month.month}"),
    ])
    rows.append([InlineKeyboardButton(text=w, callback_data="cal:noop")
                 for w in t(lang, "cal-weekdays").split(",")])
    for week in cal.monthdatescalendar(year, month):
        btns = []
        for d in week:
            if d.month != month:
                btns.append(InlineKeyboardButton(text=" ", callback_data="cal:noop"))
                continue
            blocked = (min_sel and d < min_sel) or (disable_to and d <= disable_to)
            if blocked:
                btns.append(InlineKeyboardButton(text=f"·{d.day}", callback_data="cal:noop"))
            else:
                btns.append(InlineKeyboardButton(text=str(d.day), callback_data=f"cal:pick:{d.isoformat()}"))
        rows.append(btns)
    today = date.today()
    rows.append([
        InlineKeyboardButton(text=t(lang, "cal-today"),    callback_data=f"cal:pick:{today.isoformat()}"),
        InlineKeyboardButton(text=t(lang, "cal-tomorrow"), callback_data=f"cal:pick:{(today + timedelta(days=1)).isoformat()}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ---------- инлайн-клавиатуры ----------
def kb_class_with_back(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t(lang, "class-eco"),     callback_data="class:eco")],
        [InlineKeyboardButton(text=t(lang, "class-comfort"), callback_data="class:comfort")],
        [InlineKeyboardButton(text=t(lang, "class-business"),callback_data="class:business")],
        [InlineKeyboardButton(text=t(lang, "class-premium"), callback_data="class:premium")],
        [InlineKeyboardButton(text=t(lang, "class-suv"),     callback_data="class:suv")],
        [InlineKeyboardButton(text=t(lang, "class-minivan"), callback_data="class:minivan")],
        [InlineKeyboardButton(text=t(lang, "back-to-dates"), callback_data="back:dates")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_classes_inline_again(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t(lang, "class-eco"),     callback_data="class:eco"),
         InlineKeyboardButton(text=t(lang, "class-comfort"), callback_data="class:comfort")],
        [InlineKeyboardButton(text=t(lang, "class-business"),callback_data="class:business"),
         InlineKeyboardButton(text=t(lang, "class-premium"), callback_data="class:premium")],
        [InlineKeyboardButton(text=t(lang, "class-suv"),     callback_data="class:suv"),
         InlineKeyboardButton(text=t(lang, "class-minivan"), callback_data="class:minivan")],
        [InlineKeyboardButton(text=t(lang, "back-to-dates"), callback_data="back:dates")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_card_actions(lang: str, car_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn-more"),  callback_data=f"more:{car_id}"),
         InlineKeyboardButton(text=t(lang, "btn-terms"), callback_data=f"terms:{car_id}")],
        [InlineKeyboardButton(text=t(lang, "btn-reviews"), callback_data=f"reviews:{car_id}"),
         InlineKeyboardButton(text=t(lang, "btn-book"),    callback_data=f"pick:{car_id}")],
    ])

def kb_confirm_booking(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "book-btn-confirm"), callback_data="bk:confirm"),
         InlineKeyboardButton(text=t(lang, "book-btn-cancel"),  callback_data="bk:cancel")]
    ])

# ---------- смета ----------
def iter_days(start: datetime, end: datetime):
    for i in range((end - start).days):
        yield (start + timedelta(days=i)).date()

def estimate_quote(start: datetime, end: datetime, price_weekday: float, price_weekend: float) -> int:
    total = 0.0
    for d in iter_days(start, end):
        total += float(price_weekend or price_weekday or 0) if d.weekday() >= 5 else float(price_weekday or 0)
    return int(total)

# ==============
# ⛳ HELPERS
# ==============
async def _user_profile_status(tg_user_id: int) -> tuple[bool, bool]:
    """
    Возвращает (exists, is_complete) по /users/check/.
    Никаких исключений наружу не кидаем.
    """
    api = ApiClient()
    try:
        data = await api.get("/users/check/", params={"tg_user_id": tg_user_id})
        return bool(data.get("exists")), bool(data.get("is_complete"))
    except Exception:
        return False, False
    finally:
        await api.close()

# ---------- хэндлеры поиска ----------
@router.message(F.text.func(is_find_btn))
async def start_search(m: Message, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()
    await state.set_state(SearchStates.DATE_FROM)
    today = date.today()
    await state.update_data(date_from=None, date_to=None, results=None)
    await m.answer(t(lang, "search-date-from"), reply_markup=build_calendar(today.year, today.month, lang, min_sel=today))

@router.callback_query(SearchStates.DATE_FROM, F.data.startswith("cal:nav:"))
async def cal_nav_from(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    _, _, y, mth = c.data.split(":")
    await c.message.edit_text(t(lang, "search-date-from"),
                              reply_markup=build_calendar(int(y), int(mth), lang, min_sel=date.today()))
    await c.answer()

@router.callback_query(SearchStates.DATE_FROM, F.data.startswith("cal:pick:"))
async def cal_pick_from(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    d = date.fromisoformat(c.data.split(":")[2])
    if d < date.today():
        return await c.answer(t(lang, "search-warn-past"), show_alert=True)
    await state.update_data(date_from=datetime(d.year, d.month, d.day, 10, 0).isoformat())
    await state.set_state(SearchStates.DATE_TO)
    await c.message.edit_text(
        t(lang, "search-date-to", start=f"{d:%d.%m.%Y}"),
        reply_markup=build_calendar(d.year, d.month, lang, min_sel=date.today(), disable_to=d)
    )
    await c.answer()

@router.callback_query(SearchStates.DATE_TO, F.data.startswith("cal:nav:"))
async def cal_nav_to(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    start_date = datetime.fromisoformat(data["date_from"]).date()
    _, _, y, mth = c.data.split(":")
    await c.message.edit_text(
        t(lang, "search-date-to", start=f"{start_date:%d.%m.%Y}"),
        reply_markup=build_calendar(int(y), int(mth), lang, min_sel=date.today(), disable_to=start_date)
    )
    await c.answer()

@router.callback_query(SearchStates.DATE_TO, F.data.startswith("cal:pick:"))
async def cal_pick_to(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    start_date = datetime.fromisoformat(data["date_from"]).date()
    end_date = date.fromisoformat(c.data.split(":")[2])
    if end_date <= start_date:
        return await c.answer(t(lang, "search-warn-end-gt-start"), show_alert=True)
    await state.update_data(date_to=datetime(end_date.year, end_date.month, end_date.day, 10, 0).isoformat())
    await state.set_state(SearchStates.CLASS)
    await c.message.edit_text(
        t(lang, "search-period", start=f"{start_date:%d.%m.%Y}", end=f"{end_date:%d.%m.%Y}"),
        reply_markup=kb_class_with_back(lang)
    )
    await c.answer()

@router.callback_query(F.data == "back:dates")
async def back_to_dates(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    start_date_iso = data.get("date_from")
    if not start_date_iso:
        await state.set_state(SearchStates.DATE_FROM)
        today = date.today()
        await c.message.edit_text(t(lang, "search-date-from"),
                                  reply_markup=build_calendar(today.year, today.month, lang, min_sel=today))
        return await c.answer()
    start_date = datetime.fromisoformat(start_date_iso).date()
    await state.set_state(SearchStates.DATE_TO)
    await c.message.edit_text(
        t(lang, "search-date-to", start=f"{start_date:%d.%m.%Y}"),
        reply_markup=build_calendar(start_date.year, start_date.month, lang, min_sel=date.today(), disable_to=start_date)
    )
    await c.answer()

@router.callback_query(SearchStates.CLASS, F.data.startswith("class:"))
async def set_class_cb_from_class(c: CallbackQuery, state: FSMContext):
    await state.update_data(car_class=c.data.split(":")[1])
    await do_search(c.message, state, c.from_user.id)
    await c.answer()

@router.callback_query(SearchStates.RESULTS, F.data.startswith("class:"))
async def set_class_cb_from_results(c: CallbackQuery, state: FSMContext):
    await state.update_data(car_class=c.data.split(":")[1])
    await do_search(c.message, state, c.from_user.id)
    await c.answer()

# ---------- карточки ----------
def build_car_caption(car: dict, lang: str) -> str:
    title = car.get('title') or t(lang, "card-fallback", caption="")

    year_part = f" ({car['year']})" if car.get("year") else ""
    mileage_part = f" • {fmt_int(car['mileage_km'])} km" if car.get("mileage_km") else ""
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
    if hp: parts.append(f"{fmt_int(hp)} hp")
    if fuel_label: parts.append(fuel_label)
    if cons: parts.append(f"{cons} L/100 km")
    line3 = ("⛽ " + " • ".join(parts)) if parts else ""

    price = t(lang, "card-price", wd=fmt_int(car.get('price_weekday') or 0), we=fmt_int(car.get('price_weekend') or car.get('price_weekday') or 0))
    dep_amt = car.get("deposit_amount")
    dep_band = str(car.get("deposit_band") or "none").lower()
    deposit = (f"{fmt_int(dep_amt)} UZS") if dep_amt else t(lang, {"none":"deposit-none","low":"deposit-low","high":"deposit-high"}.get(dep_band, "deposit-low"))
    limit = car.get("limit_km") or 0
    ins = t(lang, "ins-included") if car.get("insurance_included") else t(lang, "ins-excluded")
    terms = t(lang, "card-terms", deposit=deposit, limit=fmt_int(limit), ins=ins)

    opts = []
    if car.get("child_seat"): opts.append(t(lang, "card-option-child"))
    if car.get("delivery"):   opts.append(t(lang, "card-option-delivery"))
    opts_block = t(lang, "card-options-title") + "\n" + "\n".join(opts) if opts else ""

    blocks = [top, line2, line3, "", price, "", terms]
    if opts_block: blocks.extend(["", opts_block])
    return "\n".join([b for b in blocks if b]).strip()

# ---------- поиск ----------
async def do_search(msg: Message, state: FSMContext, user_id: int):
    data = await state.get_data()
    api = ApiClient()
    lang = await resolve_user_lang(api, user_id, await state.get_data())
    await api.close()

    params = {"date_from": data.get("date_from"), "date_to": data.get("date_to")}
    if data.get("car_class"): params["car_class"] = data["car_class"]

    api = ApiClient()
    try:
        cars = await api.get("/cars/search/", params=params)
    finally:
        await api.close()
    items = cars if isinstance(cars, list) else []
    await state.update_data(results=items, page=1)

    if not items:
        await msg.answer(t(lang, "search-results-none"), reply_markup=kb_classes_inline_again(lang))
        return

    extra = " " + t(lang, "showing-first-10") if len(items) > 10 else ""
    await msg.answer(t(lang, "search-results-head", count=len(items), extra=extra))

    root = Path(settings.media_root) if settings.media_root else None
    for car in items[:10]:
        caption = build_car_caption(car, lang)
        markup = kb_card_actions(lang, car["id"])
        sent = False
        if root and car.get("images_rel"):
            fp = root / car["images_rel"][0]
            if fp.exists():
                try:
                    await msg.bot.send_photo(chat_id=msg.chat.id, photo=FSInputFile(str(fp)), caption=caption, reply_markup=markup)
                    sent = True
                except Exception:
                    sent = False
        if not sent and car.get("cover_url"):
            try:
                await msg.bot.send_photo(chat_id=msg.chat.id, photo=car["cover_url"], caption=caption, reply_markup=markup)
                sent = True
            except Exception:
                sent = False
        if not sent:
            await msg.answer("📄 " + caption, reply_markup=markup)

    await msg.answer(t(lang, "search-classes-head"), reply_markup=kb_classes_inline_again(lang))
    await state.set_state(SearchStates.RESULTS)

# ---------- кнопки под карточкой ----------
@router.callback_query(SearchStates.RESULTS, F.data.startswith("more:"))
async def show_more_photos(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    car_id = int(c.data.split(":")[1])
    data = await state.get_data()
    car = next((x for x in data.get("results", []) if x["id"] == car_id), None)
    if not car: return await c.answer(t(lang, "terms-car-not-found"), show_alert=True)
    paths = (car.get("images_rel") or [])[1:]
    if not paths: return await c.answer(t(lang, "terms-no-more-photos"), show_alert=True)
    root = Path(settings.media_root) if settings.media_root else None
    if root:
        for rel in paths:
            fp = root / rel
            if fp.exists():
                try: await c.message.bot.send_photo(c.message.chat.id, FSInputFile(str(fp)))
                except Exception: pass
    await c.answer()

@router.callback_query(SearchStates.RESULTS, F.data.startswith("terms:"))
async def show_terms(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    car_id = int(c.data.split(":")[1])
    data = await state.get_data()
    car = next((x for x in data.get("results", []) if x["id"] == car_id), None)
    if not car:
        return await c.answer(t(lang, "terms-car-not-found"), show_alert=True)

    dep_amt = car.get("deposit_amount")
    dep_band = str(car.get("deposit_band") or "none").lower()
    dep_txt = f"{fmt_int(dep_amt)} UZS" if dep_amt else t(lang, {
        "none":"deposit-none","low":"deposit-low","high":"deposit-high"
    }.get(dep_band, "deposit-low"))
    text = (
        t(lang, "terms-title", title=car['title']) + "\n" +
        t(lang, "terms-deposit", deposit=dep_txt) + "\n" +
        t(lang, "terms-limit",   limit=fmt_int(car.get('limit_km') or 0)) + "\n" +
        t(lang, "terms-ins",     ins=t(lang, "ins-included") if car.get('insurance_included') else t(lang, "ins-excluded")) + "\n" +
        t(lang, "terms-driver",  has="yes" if car.get('car_with_driver') else "no") + "\n" +
        t(lang, "terms-delivery",has="yes" if car.get('delivery') else "no") + "\n" +
        t(lang, "terms-child",   has="yes" if car.get('child_seat') else "no")
    )
    await c.message.answer(text)
    await c.answer()

@router.callback_query(SearchStates.RESULTS, F.data.startswith("reviews:"))
async def show_reviews(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    await c.message.answer(t(lang, "reviews-soon")); await c.answer()

# ---------- бронирование ----------
@router.callback_query(SearchStates.RESULTS, F.data.startswith("pick:"))
async def pick_car(c: CallbackQuery, state: FSMContext):
    """
    Пытаемся создать бронь. Если backend возвращает, что пользователь
    не зарегистрирован/анкета неполная, — запускаем регистрацию.
    """
    car_id = int(c.data.split(":")[1])
    data = await state.get_data()

    date_from = data.get("date_from")
    date_to   = data.get("date_to")
    results   = data.get("results") or []
    car = next((x for x in results if x["id"] == car_id), None)

    if not (date_from and date_to and car):
        return await c.answer("Не хватает данных для бронирования. Повторите поиск.", show_alert=True)

    payload = {
        "car_id": car_id,
        "client_tg_user_id": c.from_user.id,
        "date_from": date_from,
        "date_to": date_to,
    }

    api = ApiClient()
    try:
        # пробуем создать бронь
        booking = await api.post("/bookings/", json=payload)
        await c.message.answer(
            f"Заявка на аренду машины «{car['title']}» с {date_from[:10]} до {date_to[:10]} отправлена партнёру. "
            f"Статус: На проверке.\nВы получите уведомление при подтверждении/отклонении."
        )
        ensure_client_subscription(c.bot, c.from_user.id)
        return await c.answer()
    except Exception:
        # ✅ FIX: независимо от текста ошибки уточняем статус профиля
        exists, is_complete = await _user_profile_status(c.from_user.id)
        if (not exists) or (not is_complete):
            await state.update_data(
                selected_car_id=car_id,
                selected_car_title=car.get("title"),
                date_from=date_from,
                date_to=date_to,
            )
            api2 = ApiClient()
            lang = await resolve_user_lang(api2, c.from_user.id, await state.get_data())
            await api2.close()
            await state.set_state(SearchStates.PHONE)
            await c.message.answer(
                f"Вы выбрали {car.get('title')}, {date_from[:10]}–{date_to[:10]}.\n"
                f"Оставьте контакты для связи:",
                reply_markup=kb_request_phone(lang)
            )
            return await c.answer()
        # если профиль ок — действительно ошибка сервера
        await c.message.answer("Не удалось создать заявку. Попробуйте позже.")
        return await c.answer()
    finally:
        await api.close()

# ---------- подтверждение/отмена брони ----------
@router.callback_query(BookingStates.CONFIRM, F.data == "bk:cancel")
async def booking_cancel(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.message.answer(t(lang, "book-canceled"))
    await state.clear()
    await c.answer()

@router.callback_query(BookingStates.CONFIRM, F.data == "bk:confirm")
async def booking_confirm(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, data)
    await api.close()

    car_id    = data.get("selected_car_id")
    car_title = data.get("selected_car_title")
    date_from = data.get("date_from")
    date_to   = data.get("date_to")

    if not (car_id and date_from and date_to):
        await c.message.answer(t(lang, "errors-car-not-found"))
        await state.clear()
        return await c.answer()

    api2 = ApiClient()
    try:
        await api2.post("/bookings/", json={
            "client_tg_user_id": c.from_user.id,
            "car_id": int(car_id),
            "date_from": date_from,
            "date_to":   date_to,
        })
        await c.message.answer(
            t(lang, "book-created",
              title=car_title,
              start=datetime.fromisoformat(date_from).strftime("%d.%m.%Y"),
              end=datetime.fromisoformat(date_to).strftime("%d.%m.%Y"))
        )
    except Exception as e:
        await c.message.answer(t(lang, "book-create-fail", error=str(e)))
    finally:
        await api2.close()

    await state.clear()
    await c.answer()
