# bots/client_bot/handlers/search.py
import base64
import io
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
from bots.client_bot.poller import TRACK_BOOKINGS
from bots.client_bot.handlers.start import is_find_btn, kb_request_phone
from bots.shared.i18n import t, resolve_user_lang, SUPPORTED

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

def build_calendar(year: int, month: int, lang: str,
                   min_sel: date | None = None,
                   disable_to: date | None = None) -> InlineKeyboardMarkup:
    """
    Строим inline-календарь.
    min_sel      – нельзя выбрать дату раньше этой
    disable_to   – нельзя выбрать дату <= этой (для date_to не даём ту же дату)
    """
    cal = calendar.Calendar(firstweekday=0)
    rows = []

    prev_month = (date(year, month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(year, month, 28) + timedelta(days=7)).replace(day=1)

    rows.append([
        InlineKeyboardButton(text="◀️", callback_data=f"cal:nav:{prev_month.year}:{prev_month.month}"),
        InlineKeyboardButton(text=month_title(year, month, lang), callback_data="cal:noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:nav:{next_month.year}:{next_month.month}"),
    ])

    rows.append([
        InlineKeyboardButton(text=w, callback_data="cal:noop")
        for w in t(lang, "cal-weekdays").split(",")
    ])

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
                btns.append(
                    InlineKeyboardButton(
                        text=str(d.day),
                        callback_data=f"cal:pick:{d.isoformat()}",
                    )
                )
        rows.append(btns)

    today = date.today()
    rows.append([
        InlineKeyboardButton(
            text=t(lang, "cal-today"),
            callback_data=f"cal:pick:{today.isoformat()}"),
        InlineKeyboardButton(
            text=t(lang, "cal-tomorrow"),
            callback_data=f"cal:pick:{(today + timedelta(days=1)).isoformat()}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

# ---------- клавиатуры выбора класса/кнопок на карточках ----------
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
    """
    Кнопки под карточкой авто.
    В callback «pick» передаём только car_id,
    даты подтянем из FSM.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn-more"),  callback_data=f"more:{car_id}"),
        InlineKeyboardButton(text=t(lang, "btn-reviews"), callback_data=f"reviews:{car_id}")],
         [InlineKeyboardButton(text=t(lang, "btn-book"),    callback_data=f"pick:{car_id}")],
    ])

def kb_confirm_booking(lang: str) -> InlineKeyboardMarkup:
    """
    После того как пользователь нажал «Забронировать»,
    показываем превью и просим подтвердить («Отправить» / «Отмена»).
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "book-btn-confirm"), callback_data="bk:confirm"),
         InlineKeyboardButton(text=t(lang, "book-btn-cancel"),  callback_data="bk:cancel")],
    ])

# ---------- расчёт сметы ----------
def iter_days(start: datetime, end: datetime):
    for i in range((end - start).days):
        yield (start + timedelta(days=i)).date()

def estimate_quote(start: datetime, end: datetime,
                   price_weekday: float, price_weekend: float):
    """
    Возвращаем (total_sum:int, day_count:int)
    total_sum считает цену за каждый день отдельно:
      будни -> weekday_price
      выходные (сб/вс) -> weekend_price
    """
    total = 0.0
    days_cnt = 0
    for d in iter_days(start, end):
        days_cnt += 1
        if d.weekday() >= 5:
            total += float(price_weekend or price_weekday or 0)
        else:
            total += float(price_weekday or 0)
    return int(total), days_cnt

# ---------- карточка машины ----------
def build_car_caption(car: dict, lang: str) -> str:
    """
    Красивый текст карточки, с иконками.
    Теперь показываем:
    - класс, привод, двигатель, расход
    - цены
    - депозит и аванс
    - лимит км и страховку
    - основные условия (возраст, стаж, паспорт)
    """
    title = car.get("title") or t(lang, "card-fallback", caption="")
    year_part = f" ({car['year']})" if car.get("year") else ""
    mileage_part = f" • {fmt_int(car['mileage_km'])} km" if car.get("mileage_km") else ""
    top = t(lang, "card-top", title=title, year_part=year_part, mileage_part=mileage_part)

    # строка с классом и приводом
    class_key = {
        "eco": "class-eco",
        "comfort": "class-comfort",
        "business": "class-business",
        "premium": "class-premium",
        "suv": "class-suv",
        "minivan": "class-minivan",
    }.get(str(car.get("car_class", "")).lower(), "")
    class_label = t(lang, class_key) if class_key else ""
    class_part = f" {t(lang, 'label-class', value=class_label)}" if class_label else ""
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
        class_part=class_part,
        drive_part=drive_part,
    )

    # третья строка: мощность, топливо, расход
    hp = car.get("horsepower_hp")
    fuel_key = {
        "petrol":   "fuel-petrol",
        "diesel":   "fuel-diesel",
        "gas":      "fuel-gas",
        "hybrid":   "fuel-hybrid",
        "electric": "fuel-electric",
    }.get(str(car.get("fuel_type", "")).lower(), "")
    fuel_label = t(lang, fuel_key) if fuel_key else ""
    cons = car.get("fuel_consumption_l_per_100km")

    parts = []
    if hp:
        parts.append(f"{fmt_int(hp)} hp")
    if fuel_label:
        parts.append(fuel_label)
    if cons:
        parts.append(f"{cons} L/100 km")
    line3 = ("⛽ " + " • ".join(parts)) if parts else ""

    # блок с ценой
    price_block = t(
        lang,
        "card-price",
        wd=fmt_int(car.get("price_weekday") or 0),
        we=fmt_int(car.get("price_weekend") or car.get("price_weekday") or 0),
    )

    # депозит и аванс
    deposit_val = car.get("deposit")
    advance_val = car.get("deposit_amount")

    deposit_txt = f"{fmt_int(deposit_val)} UZS" if deposit_val else t(lang, "deposit-none")
    advance_txt = f"{fmt_int(advance_val)} UZS" if advance_val else t(lang, "advance-none")

    limit = car.get("limit_km") or 0
    ins = t(lang, "ins-included") if car.get("insurance_included") else t(lang, "ins-excluded")

    # общий блок условий по машине (кратко)
    terms = t(
        lang,
        "card-terms",
        deposit=deposit_txt,
        advance=advance_txt,
        limit=fmt_int(limit),
        ins=ins,
    )

    # дополнительные опции
    opts = []
    if car.get("child_seat"):
        opts.append(t(lang, "card-option-child"))
    if car.get("delivery"):
        opts.append(t(lang, "card-option-delivery"))
    if car.get("car_with_driver"):
        opts.append(t(lang, "card-option-driver"))
    opts_block = (t(lang, "card-options-title") + "\n" + "\n".join(opts)) if opts else ""

    # базовые требования к клиенту
    req_parts = []
    age = car.get("age_access")
    if age:
        req_parts.append(t(lang, "card-age", age=age))
    exp = car.get("drive_exp")
    if exp:
        req_parts.append(t(lang, "card-drive-exp", years=exp))
    if car.get("passport"):
        req_parts.append(t(lang, "card-passport-required"))
    req_block = "\n".join(req_parts) if req_parts else ""

    blocks = [top, line2, line3, "", price_block, "", terms]
    if req_block:
        blocks.extend(["", req_block])
    if opts_block:
        blocks.extend(["", opts_block])

    return "\n".join([b for b in blocks if b]).strip()

# ---------- ПОИСК ----------

@router.message(F.text.func(is_find_btn))
async def start_search(m: Message, state: FSMContext):
    """
    Пользователь жмёт "🔎 Найти авто".
    Сбрасываем предыдущий поиск и показываем календарь "дата начала".
    """
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()

    await state.set_state(SearchStates.DATE_FROM)
    today = date.today()
    await state.update_data(date_from=None, date_to=None, results=None, pending_booking=None)

    await m.answer(
        t(lang, "search-date-from"),
        reply_markup=build_calendar(today.year, today.month, lang, min_sel=today),
    )

# шаг выбора первой даты
@router.callback_query(SearchStates.DATE_FROM, F.data.startswith("cal:nav:"))
async def cal_nav_from(c: CallbackQuery, state: FSMContext):
    _, _, y, mth = c.data.split(":")
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    await c.message.edit_text(
        t(lang, "search-date-from"),
        reply_markup=build_calendar(int(y), int(mth), lang, min_sel=date.today()),
    )
    await c.answer()

@router.callback_query(SearchStates.DATE_FROM, F.data.startswith("cal:pick:"))
async def cal_pick_from(c: CallbackQuery, state: FSMContext):
    picked = date.fromisoformat(c.data.split(":")[2])
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    if picked < date.today():
        return await c.answer(t(lang, "search-warn-past"), show_alert=True)

    start_iso = datetime(picked.year, picked.month, picked.day, 10, 0).isoformat()
    await state.update_data(date_from=start_iso)
    await state.set_state(SearchStates.DATE_TO)

    await c.message.edit_text(
        t(lang, "search-date-to", start=f"{picked:%d.%m.%Y}"),
        reply_markup=build_calendar(
            picked.year,
            picked.month,
            lang,
            min_sel=date.today(),
            disable_to=picked,
        ),
    )
    await c.answer()

# шаг выбора второй даты
@router.callback_query(SearchStates.DATE_TO, F.data.startswith("cal:nav:"))
async def cal_nav_to(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    start_date = datetime.fromisoformat(data["date_from"]).date()
    _, _, y, mth = c.data.split(":")

    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    await c.message.edit_text(
        t(lang, "search-date-to", start=f"{start_date:%d.%m.%Y}"),
        reply_markup=build_calendar(
            int(y),
            int(mth),
            lang,
            min_sel=date.today(),
            disable_to=start_date,
        ),
    )
    await c.answer()

@router.callback_query(SearchStates.DATE_TO, F.data.startswith("cal:pick:"))
async def cal_pick_to(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    start_date = datetime.fromisoformat(data["date_from"]).date()
    end_date = date.fromisoformat(c.data.split(":")[2])

    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    if end_date <= start_date:
        return await c.answer(t(lang, "search-warn-end-gt-start"), show_alert=True)

    end_iso = datetime(end_date.year, end_date.month, end_date.day, 10, 0).isoformat()
    await state.update_data(date_to=end_iso)
    await state.set_state(SearchStates.CLASS)

    await c.message.edit_text(
        t(lang, "search-period",
          start=f"{start_date:%d.%m.%Y}",
          end=f"{end_date:%d.%m.%Y}"),
        reply_markup=kb_class_with_back(lang),
    )
    await c.answer()

# кнопка "назад к датам"
@router.callback_query(F.data == "back:dates")
async def back_to_dates(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    start_iso = data.get("date_from")

    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    if not start_iso:
        # вернёмся на выбор первой даты
        await state.set_state(SearchStates.DATE_FROM)
        today = date.today()
        await c.message.edit_text(
            t(lang, "search-date-from"),
            reply_markup=build_calendar(today.year, today.month, lang, min_sel=today),
        )
        return await c.answer()

    start_date = datetime.fromisoformat(start_iso).date()
    await state.set_state(SearchStates.DATE_TO)
    await c.message.edit_text(
        t(lang, "search-date-to", start=f"{start_date:%d.%m.%Y}"),
        reply_markup=build_calendar(
            start_date.year,
            start_date.month,
            lang,
            min_sel=date.today(),
            disable_to=start_date,
        ),
    )
    await c.answer()

# выбор класса из экрана CLASS
@router.callback_query(SearchStates.CLASS, F.data.startswith("class:"))
async def set_class_from_class(c: CallbackQuery, state: FSMContext):
    await state.update_data(car_class=c.data.split(":")[1])
    await do_search(c.message, state, c.from_user.id)
    await c.answer()

# выбор класса уже после показа результатов (смена фильтра)
@router.callback_query(SearchStates.RESULTS, F.data.startswith("class:"))
async def set_class_from_results(c: CallbackQuery, state: FSMContext):
    await state.update_data(car_class=c.data.split(":")[1])
    await do_search(c.message, state, c.from_user.id)
    await c.answer()

# ---------- собственно выдача результатов ----------
async def do_search(msg: Message, state: FSMContext, user_id: int):
    data = await state.get_data()
    api = ApiClient()
    lang = await resolve_user_lang(api, user_id, await state.get_data())
    await api.close()

    params = {
        "date_from": data.get("date_from"),
        "date_to": data.get("date_to"),
    }
    if data.get("car_class"):
        params["car_class"] = data["car_class"]

    api = ApiClient()
    try:
        cars = await api.get("/cars/search/", params=params)
    finally:
        await api.close()

    items = cars if isinstance(cars, list) else []
    await state.update_data(results=items, page=1)

    if not items:
        await msg.answer(t(lang, "search-results-none"), reply_markup=kb_classes_inline_again(lang))
        await state.set_state(SearchStates.RESULTS)
        return

    extra = " " + t(lang, "showing-first-10") if len(items) > 10 else ""
    await msg.answer(t(lang, "search-results-head", count=len(items), extra=extra))

    root = Path(settings.media_root) if settings.media_root else None
    for car in items[:10]:
        caption = build_car_caption(car, lang)
        markup = kb_card_actions(lang, car["id"])

        sent_ok = False

        # 1) локальная фотка
        if root and car.get("images_rel"):
            fp = root / car["images_rel"][0]
            if fp.exists():
                try:
                    await msg.bot.send_photo(
                        chat_id=msg.chat.id,
                        photo=FSInputFile(str(fp)),
                        caption=caption,
                        reply_markup=markup,
                    )
                    sent_ok = True
                except Exception:
                    sent_ok = False

        # 2) абсолютный cover_url, если есть
        if (not sent_ok) and car.get("cover_url"):
            try:
                await msg.bot.send_photo(
                    chat_id=msg.chat.id,
                    photo=car["cover_url"],
                    caption=caption,
                    reply_markup=markup,
                )
                sent_ok = True
            except Exception:
                sent_ok = False

        # 3) без фото
        if not sent_ok:
            await msg.answer("📄 " + caption, reply_markup=markup)

    # после выдачи карточек даём человеку возможность сменить класс/дату
    await msg.answer(t(lang, "search-classes-head"), reply_markup=kb_classes_inline_again(lang))
    await state.set_state(SearchStates.RESULTS)

# ---------- кнопки под карточками ----------
@router.callback_query(SearchStates.RESULTS, F.data.startswith("more:"))
async def show_more_photos(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    car_id = int(c.data.split(":")[1])
    data = await state.get_data()
    car = next((x for x in data.get("results", []) if x["id"] == car_id), None)
    if not car:
        return await c.answer(t(lang, "terms-car-not-found"), show_alert=True)

    paths = (car.get("images_rel") or [])[1:]
    if not paths:
        return await c.answer(t(lang, "terms-no-more-photos"), show_alert=True)

    root = Path(settings.media_root) if settings.media_root else None
    if root:
        for rel in paths:
            fp = root / rel
            if fp.exists():
                try:
                    await c.message.bot.send_photo(c.message.chat.id, FSInputFile(str(fp)))
                except Exception:
                    pass
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

    # депозит и аванс
    deposit_val = car.get("deposit")
    advance_val = car.get("deposit_amount")

    deposit_txt = f"{fmt_int(deposit_val)} UZS" if deposit_val else t(lang, "deposit-none")
    advance_txt = f"{fmt_int(advance_val)} UZS" if advance_val else t(lang, "advance-none")

    limit_txt = fmt_int(car.get("limit_km") or 0)
    ins_txt = t(lang, "ins-included") if car.get("insurance_included") else t(lang, "ins-excluded")

    driver_txt = t(lang, "yes") if car.get("car_with_driver") else t(lang, "no")
    delivery_txt = t(lang, "yes") if car.get("delivery") else t(lang, "no")
    child_txt = t(lang, "yes") if car.get("child_seat") else t(lang, "no")

    age = car.get("age_access")
    drive_exp = car.get("drive_exp")
    passport_need = car.get("passport")

    lines = [
        t(lang, "terms-title", title=car["title"]),
        t(lang, "terms-deposit", deposit=deposit_txt),
        t(lang, "terms-advance", advance=advance_txt),
        t(lang, "terms-limit",   limit=limit_txt),
        t(lang, "terms-ins",     ins=ins_txt),
        t(lang, "terms-driver",  has=driver_txt),
        t(lang, "terms-delivery",has=delivery_txt),
        t(lang, "terms-child",   has=child_txt),
    ]

    if age:
        lines.append(t(lang, "terms-age", age=age))
    if drive_exp:
        lines.append(t(lang, "terms-drive-exp", years=drive_exp))
    lines.append(
        t(lang, "terms-passport", has=t(lang, "yes") if passport_need else t(lang, "no"))
    )

    txt = "\n".join(lines)
    await c.message.answer(txt)
    await c.answer()

@router.callback_query(SearchStates.RESULTS, F.data.startswith("reviews:"))
async def show_reviews(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    await c.message.answer(t(lang, "reviews-soon"))
    await c.answer()

# ---------- бронирование ----------
@router.callback_query(SearchStates.RESULTS, F.data.startswith("pick:"))
async def pick_car(c: CallbackQuery, state: FSMContext):
    """
    1. Юзер нажал «Забронировать».
    2. Сохраняем pending_booking в FSM.
    3. Просим отправить селфи (обязательный шаг).
    4. После селфи покажем превью и попросим подтвердить.
    """
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    parts = c.data.split(":")
    car_id = int(parts[1])

    data = await state.get_data()
    date_from_iso = data.get("date_from")
    date_to_iso   = data.get("date_to")
    if not (date_from_iso and date_to_iso):
        await c.message.answer(t(lang, "errors-missing-dates"))
        return await c.answer()

    # достаём объект авто из results, чтобы знать цены и имя
    car = next((x for x in data.get("results", []) if x["id"] == car_id), None)
    if not car:
        await c.message.answer(t(lang, "terms-car-not-found"))
        return await c.answer()

    # считаем примерную сумму и число дней
    start_dt = datetime.fromisoformat(date_from_iso)
    end_dt   = datetime.fromisoformat(date_to_iso)
    total_sum, days_cnt = estimate_quote(
        start_dt,
        end_dt,
        float(car.get("price_weekday") or 0),
        float(car.get("price_weekend") or (car.get("price_weekday") or 0)),
    )

    # готовим payload на будущее создание
    payload = {
        "car_id": car_id,
        "client_tg_user_id": c.from_user.id,
        "date_from": date_from_iso,
        "date_to": date_to_iso,
    }

    # сохраняем в state всё, что понадобится на следующем шаге
    await state.update_data(
        pending_booking=payload,
        pending_booking_title=car.get("title"),
        pending_booking_total=total_sum,
        pending_booking_days=days_cnt,
    )

    # просим селфи
    await c.message.answer(t(lang, "selfie-ask"))
    await state.set_state(BookingStates.SELFIE)
    await c.answer()

@router.message(BookingStates.SELFIE)
async def got_selfie(m: Message, state: FSMContext):
    """
    Принимаем селфи:
    - только photo или document с image/*
    - скачиваем файл с Telegram
    - шлём base64 на бэкенд (/users/selfie/)
    - показываем превью брони + кнопки Подтвердить/Отмена
    """
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()

    file_id = None

    if m.photo:
        file_id = m.photo[-1].file_id
    elif m.document and m.document.mime_type and m.document.mime_type.startswith("image/"):
        file_id = m.document.file_id

    if not file_id:
        await m.answer(t(lang, "selfie-invalid"))
        return

    # кладём file_id в FSM (на будущее, если пригодится)
    await state.update_data(selfie_file_id=file_id)

    # 🔽 качаем файл из Telegram
    try:
        tg_file = await m.bot.get_file(file_id)
        buf = io.BytesIO()
        await m.bot.download_file(tg_file.file_path, buf)
        raw = buf.getvalue()
        image_b64 = base64.b64encode(raw).decode("ascii")
    except Exception as e:
        await m.answer(t(lang, "selfie-save-fail", error=str(e)))
        return

    # 🔽 сохраняем/обновляем селфи на бэке
    api = ApiClient()
    try:
        await api.post("/users/selfie/", json={
            "tg_user_id": m.from_user.id,
            "selfie_file_id": file_id,
            "image_b64": image_b64,
        })
    except Exception as e:
        await m.answer(t(lang, "selfie-save-fail", error=str(e)))
    finally:
        await api.close()

    data = await state.get_data()
    payload = data.get("pending_booking")
    if not payload:
        await m.answer(t(lang, "errors-missing-dates"))
        await state.clear()
        return

    # собираем превью
    start_dt = datetime.fromisoformat(payload["date_from"])
    end_dt   = datetime.fromisoformat(payload["date_to"])
    title    = data.get("pending_booking_title", "")
    total_sum = data.get("pending_booking_total", 0)
    days_cnt  = data.get("pending_booking_days", 0)

    preview_head = t(
        lang,
        "book-preview-head",
        title=title,
        start=start_dt.strftime("%d.%m.%Y"),
        end=end_dt.strftime("%d.%m.%Y"),
    )
    preview_sum = t(
        lang,
        "book-preview-sum",
        sum=fmt_int(total_sum),
        days=days_cnt,
    )
    preview_ask = t(lang, "book-preview-ask")

    await m.answer(
        f"{preview_head}\n{preview_sum}\n\n{preview_ask}",
        reply_markup=kb_confirm_booking(lang)
    )

    await state.set_state(BookingStates.CONFIRM)

# подтверждение брони
@router.callback_query(BookingStates.CONFIRM, F.data == "bk:confirm")
async def booking_confirm(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, data)
    await api.close()

    payload = data.get("pending_booking")
    if not payload:
        await c.message.edit_text(t(lang, "errors-missing-dates"))
        await state.clear()
        return await c.answer()

    api = ApiClient()
    try:
        booking = await api.post("/bookings/", json=payload)
    except Exception as e:
        await api.close()
        text_error = str(e)

        # 🔥 если бэкенд сказал, что пользователь не заполнен
        if "user_incomplete" in text_error:
            # готовим данные для "отложенной" брони через регистрацию
            pb = payload
            await state.update_data(
                selected_car_id=pb.get("car_id"),
                selected_car_title=data.get("pending_booking_title"),
                date_from=pb.get("date_from"),
                date_to=pb.get("date_to"),
            )
            # переводим в состояние ввода телефона
            await state.set_state(SearchStates.PHONE)

            # сообщаем, что нужно зарегистрироваться
            await c.message.edit_text(
                t(lang, "reg-before-booking")
            )
            await c.message.answer(
                t(lang, "phone-again"),
                reply_markup=kb_request_phone(lang)
            )
            await c.answer()
            return

        # все остальные ошибки — как раньше
        await c.message.edit_text(
            t(lang, "book-create-error", error=text_error)
        )
        await state.clear()
        await c.answer()
        return
    finally:
        await api.close()

    # если дошли сюда — бронь создана успешно (как и раньше)
    try:
        TRACK_BOOKINGS.setdefault(c.from_user.id, set()).add(int(booking["id"]))
    except Exception:
        pass

    title = booking.get("car_title") or data.get("pending_booking_title", "")
    dfrom = (booking.get("date_from") or payload["date_from"])[:10]
    dto   = (booking.get("date_to")   or payload["date_to"])[:10]

    await c.message.edit_text(
        t(lang, "book-sent", title=title, start=dfrom, end=dto),
        reply_markup=None
    )

    await state.clear()
    await c.answer()


# отмена брони до отправки
@router.callback_query(BookingStates.CONFIRM, F.data == "bk:cancel")
async def booking_cancel(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    await state.clear()
    await c.message.edit_text(t(lang, "book-cancelled"))
    await c.answer()
