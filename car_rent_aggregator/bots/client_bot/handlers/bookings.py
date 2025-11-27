# bots/client_bot/handlers/bookings.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone as _tz

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
)

from bots.shared.api_client import ApiClient
from bots.shared.i18n import t, resolve_user_lang, SUPPORTED
from bots.client_bot.poller import PAYMENT_MSGS
from bots.client_bot.states import PaymentStates

from bots.client_bot.handlers.start import main_menu

router = Router()


# =====================================================================
# helpers
# =====================================================================

def _fmt_int(n) -> str:
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

def is_my_bookings_btn(text: str) -> bool:
    return any(text == t(lg, "menu-bookings") for lg in SUPPORTED)


def _human_status(lang: str, status_code: str) -> str:
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


# =====================================================================
# Контекстные клавиатуры для оплаты
# =====================================================================

def kb_pay_type(lang: str, full_amount: int | None = None, adv_amount: int | None = None):
    """
    Клавиатура выбора типа оплаты с подстановкой сумм.
    """
    # безопасно форматируем суммы
    full_amount = full_amount or 0
    adv_amount = adv_amount or 0

    full_text = t(lang, "pay-mode-full", amount=_fmt_int(full_amount))
    adv_text  = t(lang, "pay-mode-adv",  amount=_fmt_int(adv_amount))

    keyboard = [[KeyboardButton(text=full_text)]]
    # показываем аванс только если он > 0
    if adv_amount > 0:
        keyboard.append([KeyboardButton(text=adv_text)])

    keyboard.append([KeyboardButton(text=t(lang, "back"))])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )



def kb_pay_provider(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Payme"), KeyboardButton(text="Click")],
            [KeyboardButton(text=t(lang, "back"))],
        ],
        resize_keyboard=True
    )


# =====================================================================
# Мои брони
# =====================================================================

@router.message(F.text.func(is_my_bookings_btn))
async def my_bookings(m: Message, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()

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
    items = [b for b in items if (b.get("status") or "").lower() in ACTIVE]

    if not items:
        return await m.answer(t(lang, "my-no-items", menu_find=t(lang, "menu-find")))

    # выводим список
    lines = []
    for b in items[:20]:
        status_h = _human_status(lang, b["status"])
        lines.append(
            t(lang, "my-line",
              id=b["id"],
              title=b.get("car_title") or "",
              status=status_h,
              from_=b["date_from"][:10],
              to=b["date_to"][:10]
            )
        )

    await m.answer(t(lang, "my-head") + "\n\n" + "\n\n".join(lines))

    # ---- Блок неоплаченных броней с кнопками "Оплатить" ----
    now = datetime.now(_tz.utc)
    unpaid = []

    for b in items[:20]:
        st = (b.get("status") or "").lower()
        already_paid = (b.get("payment_marker") or "").lower() == "paid"

        if st != "confirmed" or already_paid:
            continue

        # ограничение по времени (20 минут от обновления)
        upd_iso = b.get("updated_at") or b.get("created_at")
        try:
            if upd_iso and upd_iso.endswith("Z"):
                upd_iso = upd_iso[:-1] + "+00:00"
            updated = datetime.fromisoformat(upd_iso)
        except Exception:
            updated = now

        minutes_left = max(0, 20 - int((now - updated).total_seconds() // 60))
        if minutes_left <= 0:
            # бронь уже протухла для оплаты
            continue

        # считаем примерную сумму аренды
        try:
            from_dt = datetime.fromisoformat(b["date_from"])
            to_dt = datetime.fromisoformat(b["date_to"])
            wd = float(b.get("price_weekday") or 0)
            we = float(b.get("price_weekend") or wd)
            days_total = (to_dt - from_dt).days
            approx_total = 0
            d_iter = from_dt
            for _ in range(days_total):
                approx_total += we if d_iter.weekday() >= 5 else wd
                d_iter += timedelta(days=1)
            approx_total = int(approx_total)
        except Exception:
            approx_total = 0

        adv_amount = int(float(b.get("advance_amount") or 0)) or None

        unpaid.append((b, approx_total, adv_amount, minutes_left))

    if not unpaid:
        # все брони либо оплачены, либо не подлежат оплате
        return

    # для каждой неоплаченной брони — своё сообщение + своя кнопка "Оплатить"
    for b, approx_total, adv_amount, minutes_left in unpaid:
        text_pay = t(
            lang,
            "pay-choose",
            id=b["id"],
            amount=_fmt_int(approx_total),
        )
        if minutes_left:
            text_pay += f" (⏳ {minutes_left} min)"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(lang, "menu-pay"),  # "Оплатить"
                        callback_data=f"pay:start:{b['id']}",
                    )
                ]
            ]
        )

        sent = await m.answer(text_pay, reply_markup=kb)
        PAYMENT_MSGS.setdefault(m.from_user.id, {}).setdefault(int(b["id"]), []).append(sent.message_id)

@router.callback_query(F.data.startswith("pay:start:"))
async def cb_start_payment(c: CallbackQuery, state: FSMContext):
    """
    Нажали на кнопку "Оплатить" под конкретной бронью.
    1) Достаём id брони из callback_data.
    2) Тянем бронь с бэка.
    3) Считаем полную сумму и аванс.
    4) Сохраняем в FSM и запускаем сценарий выбора типа оплаты.
    """
    try:
        booking_id = int(c.data.split(":")[2])
    except (IndexError, ValueError):
        await c.answer("Ошибка данных.", show_alert=True)
        return

    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())

    try:
        booking = await api.get(f"/bookings/{booking_id}/")
    except Exception as e:
        await api.close()
        await c.answer()
        await c.message.answer(t(lang, "pay-create-error", error=str(e)))
        return
    finally:
        await api.close()

    # статус и маркер оплаты ещё раз на всякий случай
    st = (booking.get("status") or "").lower()
    paid_marker = (booking.get("payment_marker") or "").lower()
    if st != "confirmed" or paid_marker == "paid":
        await c.answer()
        await c.message.answer(t(lang, "errors-missing-booking"))
        return

    full_amount = int(float(booking.get("price_quote") or 0))
    adv_amount  = int(float(booking.get("advance_amount") or 0))

    await state.update_data(
        pending_booking_id=booking_id,
        full_amount=full_amount,
        adv_amount=adv_amount,
    )

    await state.set_state(PaymentStates.AWAIT_TYPE)

    await c.answer()
    await c.message.answer(
        t(lang, "pay-choose-type"),
        reply_markup=kb_pay_type(lang, full_amount, adv_amount),
    )


# =====================================================================
# Новый механизм оплаты через ReplyKeyboard + FSM
# =====================================================================

# шаг 1: нажали "Оплатить"
@router.message(F.text.func(lambda txt: any(txt == t(lg, "menu-pay") for lg in SUPPORTED)))
async def start_payment(m: Message, state: FSMContext):
    """
    Пользователь нажал "Оплатить".
    Ищем его последнюю подтверждённую, но ещё не оплаченную бронь.
    Если нашли — сохраняем booking_id в FSM и запускаем сценарий выбора типа оплаты.
    """
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()

    api = ApiClient()
    try:
        items = await api.get("/bookings/", params={"client_tg_user_id": m.from_user.id})
    except Exception as e:
        await api.close()
        await m.answer(t(lang, "my-error", error=str(e)))
        return
    finally:
        await api.close()

    candidates = []
    for b in items:
        st = (b.get("status") or "").lower()
        paid_marker = (b.get("payment_marker") or "").lower()
        if st == "confirmed" and paid_marker != "paid":
            candidates.append(b)

    if not candidates:
        await m.answer(t(lang, "errors-missing-booking"), reply_markup=main_menu(lang))
        return

    # берём самую "свежую" по id
    booking = sorted(candidates, key=lambda x: x.get("id", 0))[-1]

    full_amount = int(float(booking.get("price_quote") or 0))
    adv_amount = int(float(booking.get("advance_amount") or 0))

    await state.update_data(
        pending_booking_id=booking["id"],
        full_amount=full_amount,
        adv_amount=adv_amount,
    )

    await state.set_state(PaymentStates.AWAIT_TYPE)
    await m.answer(
        t(lang, "pay-choose-type"),
        reply_markup=kb_pay_type(lang, full_amount, adv_amount),
    )



# шаг 2: полная / аванс
@router.message(PaymentStates.AWAIT_TYPE)
async def choose_payment_type(m: Message, state: FSMContext):
    txt = m.text or ""

    api = ApiClient()
    data = await state.get_data()
    lang = await resolve_user_lang(api, m.from_user.id, data)
    await api.close()

    full_amount = int(float(data.get("full_amount") or 0))
    adv_amount  = int(float(data.get("adv_amount") or 0))

    full_label = t(lang, "pay-mode-full", amount=_fmt_int(full_amount))
    adv_label  = t(lang, "pay-mode-adv",  amount=_fmt_int(adv_amount))

    if txt == full_label:
        await state.update_data(payment_type="full")
        await state.set_state(PaymentStates.AWAIT_PROVIDER)
        return await m.answer(
            t(lang, "pay-choose-provider"),
            reply_markup=kb_pay_provider(lang),
        )

    if txt == adv_label and adv_amount > 0:
        await state.update_data(payment_type="adv")
        await state.set_state(PaymentStates.AWAIT_PROVIDER)
        return await m.answer(
            t(lang, "pay-choose-provider"),
            reply_markup=kb_pay_provider(lang),
        )

    if txt == t(lang, "back"):
        # назад к кнопке "Оплатить"
        await state.clear()
        return await m.answer(
            t(lang, "pay-choose"),
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=t(lang, "menu-pay"))],
                    [KeyboardButton(text=t(lang, "menu-find"))],
                ],
                resize_keyboard=True,
            ),
        )

    return await m.answer(
        t(lang, "pay-choose-type"),
        reply_markup=kb_pay_type(lang, full_amount, adv_amount),
    )


# шаг 3: выбор провайдера + создание платежа
@router.message(PaymentStates.AWAIT_PROVIDER)
async def choose_provider(m: Message, state: FSMContext):
    """
    Шаг 3: выбор провайдера и создание платежа.
    1) Определяем провайдера (payme/click).
    2) Берём из FSM booking_id и тип оплаты (full/adv).
    3) Тянем бронь с бэка, считаем сумму.
    4) Создаём Payment через POST /payments/.
    5) Отправляем пользователю ссылку на оплату.
    """
    # язык
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()

    raw = (m.text or "").strip()
    txt = raw.lower()

    if txt == "payme":
        provider = "payme"
    elif txt == "click":
        provider = "click"
    elif raw == t(lang, "back"):
        # ← сюда теперь действительно попадём по кнопке "⬅️ Назад"
        await state.set_state(PaymentStates.AWAIT_TYPE)

        # подставим сумму для нормального текста кнопок
        data = await state.get_data()
        booking_id = data.get("pending_booking_id")

        amount_full = amount_adv = None
        try:
            api2 = ApiClient()
            booking = await api2.get(f"/bookings/{booking_id}/")
            await api2.close()

            amount_full = int(float(booking.get("price_quote") or 0))
            amount_adv = int(float(booking.get("advance_amount") or 0))
        except Exception:
            pass

        text_full = t(lang, "pay-mode-full", amount=_fmt_int(amount_full or 0))
        text_adv = t(lang, "pay-mode-adv", amount=_fmt_int(amount_adv or 0))

        return await m.answer(
            t(lang, "pay-choose-type"),
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=text_full)],
                    [KeyboardButton(text=text_adv)],
                    [KeyboardButton(text=t(lang, "back"))],
                ],
                resize_keyboard=True,
            )
        )
    else:
        # непонятный ввод – повторяем вопрос
        return await m.answer(
            t(lang, "pay-choose-provider"),
            reply_markup=kb_pay_provider(lang),
        )

    data = await state.get_data()
    booking_id = data.get("pending_booking_id")
    payment_type = data.get("payment_type", "full")

    if not booking_id:
        await state.clear()
        return await m.answer(t(lang, "errors-missing-booking"), reply_markup=main_menu(lang))

    # 1) тянем бронь, чтобы узнать сумму
    api = ApiClient()
    try:
        booking = await api.get(f"/bookings/{booking_id}/")
    except Exception as e:
        await api.close()
        await state.clear()
        return await m.answer(t(lang, "pay-create-error", error=str(e)), reply_markup=main_menu(lang))

    # сумма за весь период
    full_amount = float(booking.get("price_quote") or 0)
    # сумма аванса (если есть)
    adv_amount = float(booking.get("advance_amount") or 0)

    if payment_type == "adv" and adv_amount > 0:
        amount = adv_amount
    else:
        # по умолчанию – полная сумма
        amount = full_amount

    if amount <= 0:
        await api.close()
        await state.clear()
        return await m.answer(t(lang, "pay-amount-zero"), reply_markup=main_menu(lang))

    # 2) создаём Payment через стандартный эндпоинт /payments/
    try:
        resp = await api.post("/payments/", json={
            "booking_id": booking_id,
            "provider": provider,   # 'payme' или 'click' – как в choices
            "amount": amount,
            "currency": "UZS",
        })
    except Exception as e:
        await api.close()
        await state.clear()
        return await m.answer(t(lang, "pay-create-error", error=str(e)), reply_markup=main_menu(lang))
    finally:
        await api.close()

    # 3) достаём ссылку
    pay_url = (
        resp.get("pay_url")
        or (resp.get("raw_meta") or {}).get("provider_url")
    )

    if not pay_url:
        await state.clear()
        return await m.answer(
            t(lang, "pay-create-error", error="missing pay_url"),
            reply_markup=main_menu(lang),
        )

    # очищаем состояние и возвращаем главное меню
    await state.clear()

    msg = t(lang, "pay-open-link") + f"\n\n👉 [💳 Оплатить]({pay_url})"
    await m.answer(msg, parse_mode="Markdown", reply_markup=main_menu(lang))


