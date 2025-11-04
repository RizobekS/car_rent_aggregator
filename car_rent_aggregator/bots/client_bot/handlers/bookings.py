# bots/client_bot/handlers/bookings.py
from __future__ import annotations

from datetime import timedelta, datetime, timezone as _tz
from decimal import Decimal

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bots.shared.api_client import ApiClient
from bots.shared.i18n import t, resolve_user_lang, SUPPORTED
from bots.client_bot.poller import PAYMENT_MSGS  # кеш сообщений с оплатой (используется в поллере)
from bots.client_bot.states import SearchStates, BookingStates

router = Router()


# ───────────────── helpers ─────────────────

def is_my_bookings_btn(text: str) -> bool:
    # локализованная кнопка "Мои брони"
    return any(text == t(lg, "menu-bookings") for lg in SUPPORTED)

def _fmt_int(n) -> str:
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

def _human_status(lang: str, status_code: str) -> str:
    """
    Маппим внутренние статусы брони ('pending', 'confirmed', ...) на локализованный текст.
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


# ───────────────── клавиатуры оплаты ─────────────────

def kb_pay_choice(lang: str, booking_id: int, approx_amount: int, adv_amount: int | None) -> InlineKeyboardMarkup:
    """
    Выбор режима оплаты: полная / аванс (если есть).
    """
    rows = []
    rows.append([
        InlineKeyboardButton(
            text=t(lang, "pay-mode-full"),
            callback_data=f"pay:full:{booking_id}",
        )
    ])
    if adv_amount and int(adv_amount) > 0:
        rows.append([
            InlineKeyboardButton(
                text=t(lang, "pay-mode-adv"),
                callback_data=f"pay:adv:{booking_id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_gateways(booking_id: int, mode: str, lang: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора провайдера оплаты (Payme / Click)
    mode: "full" | "adv"
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Payme", callback_data=f"paygw:payme:{mode}:{booking_id}"),
            InlineKeyboardButton(text="💰 Click",  callback_data=f"paygw:click:{mode}:{booking_id}"),
        ],
        [InlineKeyboardButton(text="« " + t(lang, "pay-back"),
                              callback_data=f"pay:back:{mode}:{booking_id}")]
    ])


# ───────────────── блок "Мои брони" ─────────────────

@router.message(F.text.func(is_my_bookings_btn))
async def my_bookings(m: Message, state: FSMContext):
    """
    Показываем ТОЛЬКО актуальные заявки, и статусы должны быть локализованы.
    Также предлагаем оплату только по неполностью оплаченным подтверждённым заявкам.
    """
    # определяем язык
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()

    # тянем брони с бэка
    api2 = ApiClient()
    try:
        items = await api2.get("/bookings/", params={"client_tg_user_id": m.from_user.id})
    except Exception as e:
        await m.answer(t(lang, "my-error", error=str(e)))
        await api2.close()
        return
    finally:
        await api2.close()

    ACTIVE = {"pending", "confirmed", "issued", "paid"}
    items = [b for b in (items or []) if (b.get("status") or "").lower() in ACTIVE]

    if not items:
        return await m.answer(t(lang, "my-no-items", menu_find=t(lang, "menu-find")))

    # строим список
    lines = []
    for b in items[:20]:
        status_h = _human_status(lang, b.get("status", ""))
        lines.append(
            t(lang, "my-line",
              id=b["id"],
              title=b.get("car_title", ""),
              status=status_h,
              from_=b["date_from"][:10],
              to=b["date_to"][:10]
            )
        )
    await m.answer(t(lang, "my-head") + "\n\n" + "\n\n".join(lines))

    # теперь предложим оплату ТОЛЬКО тем, кто в статусе confirmed и ещё не paid
    now = datetime.now(_tz.utc)
    for b in items[:20]:
        st = (b.get("status") or "").lower()
        already_paid = (b.get("payment_marker") or "").lower() == "paid"
        if st == "confirmed" and not already_paid:
            # сколько минут до истечения слота (20 минут с момента обновления)
            upd_iso = b.get("updated_at") or b.get("created_at")
            try:
                if upd_iso and upd_iso.endswith("Z"):
                    upd_iso = upd_iso[:-1] + "+00:00"
                updated = datetime.fromisoformat(upd_iso)
            except Exception:
                updated = now
            minutes_left = max(0, 20 - int((now - updated).total_seconds() // 60))

            # примерную сумму для текста:
            # считаем по будням/выходным от бэка (мы уже делали это в poller/pay)
            try:
                from_date = b["date_from"][:10]
                to_date   = b["date_to"][:10]
                from_dt = datetime.fromisoformat(b["date_from"])
                to_dt   = datetime.fromisoformat(b["date_to"])
                wd = float(b.get("price_weekday") or 0)
                we = float(b.get("price_weekend") or wd)
                days_total = (to_dt - from_dt).days
                approx_total = 0.0
                d_iter = from_dt
                for _ in range(days_total):
                    approx_total += we if d_iter.weekday() >= 5 else wd
                    d_iter += timedelta(days=1)
                approx_total = int(approx_total)
            except Exception:
                approx_total = 0
                days_total = 0

            adv_amount = int(float(b.get("advance_amount") or 0)) or None

            # текст "Выберите тип оплаты"
            pay_text = t(lang, "pay-choose", id=b["id"], amount=_fmt_int(approx_total))
            if minutes_left:
                pay_text += f" (⏳ {minutes_left} min)"

            sent = await m.answer(
                pay_text,
                reply_markup=kb_pay_choice(lang, int(b["id"]), approx_total, adv_amount)
            )
            # кешируем id сообщения, чтобы поллер мог потом редактировать/чистить
            try:
                PAYMENT_MSGS.setdefault(m.from_user.id, {}).setdefault(int(b["id"]), []).append(sent.message_id)
            except Exception:
                pass


# ───────────────── выбор режима оплаты (full/adv) ─────────────────

@router.callback_query(F.data.startswith("pay:full:"))
async def choose_full(c: CallbackQuery, state: FSMContext):
    bid = int(c.data.split(":")[2])
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    await c.message.edit_text(t(lang, "pay-choose-full"),
                              reply_markup=kb_gateways(bid, "full", lang))
    await c.answer()

@router.callback_query(F.data.startswith("pay:adv:"))
async def choose_adv(c: CallbackQuery, state: FSMContext):
    bid = int(c.data.split(":")[2])
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    await c.message.edit_text(t(lang, "pay-choose-adv"),
                              reply_markup=kb_gateways(bid, "adv", lang))
    await c.answer()

@router.callback_query(F.data.startswith("pay:back:"))
async def pay_back(c: CallbackQuery, state: FSMContext):
    """
    Пользователь нажал «Назад» из окна выбора провайдера.
    Просто убираем inline-кнопки, текст оставляем.
    """
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.answer(t(lang, "pay-back"))


# ───────────────── выбор платёжного провайдера ─────────────────

def _estimate_total(date_from_iso: str, date_to_iso: str, price_wd, price_we) -> int:
    """
    Считаем полную сумму аренды по каждому дню (будни vs выходные).
    """
    start = datetime.fromisoformat(date_from_iso)
    end   = datetime.fromisoformat(date_to_iso)
    total = Decimal("0")
    price_wd = Decimal(str(price_wd or 0))
    price_we = Decimal(str(price_we or price_wd or 0))
    d = start
    while d < end:
        total += price_we if d.weekday() >= 5 else price_wd
        d += timedelta(days=1)
    return int(total)

@router.callback_query(F.data.startswith("paygw:"))
async def pay_gateway(c: CallbackQuery, state: FSMContext):
    """
    Пользователь выбрал Payme / Click + режим (полная сумма / аванс).
    Создаём платёж на бэкенде, получаем ссылку и отправляем её.
    """
    _, gw, mode, bid = c.data.split(":")
    bid = int(bid)

    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    # (1) тянем бронь
    api = ApiClient()
    try:
        booking = await api.get(f"/bookings/{bid}/")
    except Exception as e:
        await c.message.answer(t(lang, "my-error", error=str(e)))
        await api.close()
        return await c.answer()
    finally:
        await api.close()

    # (2) считаем сумму
    try:
        if mode == "full":
            amount = _estimate_total(
                booking["date_from"], booking["date_to"],
                booking.get("price_weekday"), booking.get("price_weekend"),
            )
        else:
            amount = int(float(booking.get("advance_amount") or 0))
        if amount <= 0:
            raise ValueError("amount<=0")
    except Exception:
        await c.message.answer(t(lang, "my-error", error="Не удалось рассчитать сумму оплаты"))
        return await c.answer()

    # (3) создаём платёж на бэке
    payload = {"booking_id": bid, "provider": gw, "amount": amount, "currency": "UZS"}
    api = ApiClient()
    try:
        payment = await api.post("/payments/", json=payload)
    except Exception as e:
        await c.message.answer(t(lang, "my-error", error=str(e)))
        await api.close()
        return await c.answer()
    finally:
        await api.close()

    pay_url = (payment or {}).get("pay_url") or ""

    await c.message.answer(
        t(lang, "pay-gw-picked",
          gw=gw.upper(),
          mode=t(lang, "pay-mode-full") if mode == "full" else t(lang, "pay-mode-adv"),
          bid=str(bid))
    )

    if pay_url:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "pay-go"), url=pay_url)]
            ]
        )
        sent = await c.message.answer(t(lang, "pay-instruction"), reply_markup=kb)
        # кешируем отправленное платёжное сообщение
        PAYMENT_MSGS.setdefault(c.from_user.id, {}).setdefault(bid, []).append(sent.message_id)
    else:
        await c.message.answer(t(lang, "pay-no-link"))

    await c.answer()
