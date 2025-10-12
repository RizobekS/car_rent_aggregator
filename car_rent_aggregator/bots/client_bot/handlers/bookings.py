from datetime import timedelta, datetime
from decimal import Decimal
from datetime import timezone as _tz

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bots.shared.api_client import ApiClient
from bots.shared.i18n import t, resolve_user_lang, SUPPORTED
from bots.client_bot.poller import PAYMENT_MSGS

router = Router()

def is_my_bookings_btn(text: str) -> bool:
    return any(text == t(lg, "menu-bookings") for lg in SUPPORTED)

def kb_gateways(booking_id: int, mode: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Payme", callback_data=f"paygw:payme:{mode}:{booking_id}"),
         InlineKeyboardButton(text="Click",  callback_data=f"paygw:click:{mode}:{booking_id}")],
        [InlineKeyboardButton(text="« "+t(lang, "pay-back"), callback_data=f"pay:back:{mode}:{booking_id}")]
    ])

def kb_pay_choice(lang: str, booking_id: int, adv_amount: int | None) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(text=t(lang, "pay-mode-full"), callback_data=f"pay:full:{booking_id}")
    ]]
    if adv_amount and int(adv_amount) > 0:
        rows.append([InlineKeyboardButton(text=t(lang, "pay-mode-adv"), callback_data=f"pay:adv:{booking_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.message(F.text.func(is_my_bookings_btn))
async def my_bookings(m: Message):
    api = ApiClient(); lang = await resolve_user_lang(api, m.from_user.id); await api.close()
    api2 = ApiClient()
    try:
        items = await api2.get("/bookings/", params={"client_tg_user_id": m.from_user.id})
    except Exception as e:
        await m.answer(t(lang, "my-error", error=str(e))); await api2.close(); return
    finally:
        await api2.close()

    if not items:
        return await m.answer(t(lang, "my-no-items", menu_find=t(lang, "menu-find")))

    # 1) компактный список
    lines = []
    for b in items[:20]:
        lines.append(
            t(lang, "my-line",
              id=b['id'], title=b['car_title'], status=b['status'],
              from_=b['date_from'][:10], to=b['date_to'][:10]).replace("from_", "from")
        )
    await m.answer(t(lang, "my-head") + "\n\n" + "\n\n".join(lines))

    # 2) единичная реплика с выбором режима оплаты (если нужно)
    now = datetime.now(_tz.utc)
    for b in items[:20]:
        if (b.get("status") == "confirmed") and ((b.get("payment_marker") or "").lower() != "paid"):
            try:
                upd = b.get("updated_at") or b.get("created_at")
                if upd and upd.endswith("Z"): upd = upd[:-1] + "+00:00"
                updated = datetime.fromisoformat(upd)
            except Exception:
                updated = now
            minutes_left = max(0, 20 - int((now - updated).total_seconds() // 60))
            adv = int(float(b.get("advance_amount") or 0)) or None
            text = t(lang, "pay-choose", id=b["id"]) + (f" (⏳ {minutes_left} min)" if minutes_left else "")
            sent = await m.answer(text, reply_markup=kb_pay_choice(lang, int(b["id"]), adv))
            try:
                d = PAYMENT_MSGS.setdefault(m.from_user.id, {})
                d.setdefault(int(b["id"]), []).append(sent.message_id)
            except Exception:
                pass

@router.callback_query(F.data.startswith("pay:full:"))
async def choose_full(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    bid = int(c.data.split(":")[2])
    await c.message.edit_text(t(lang, "pay-choose-full"), reply_markup=kb_gateways(bid, "full", lang))
    await c.answer()

@router.callback_query(F.data.startswith("pay:adv:"))
async def choose_adv(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    bid = int(c.data.split(":")[2])
    await c.message.edit_text(t(lang, "pay-choose-adv"), reply_markup=kb_gateways(bid, "adv", lang))
    await c.answer()

@router.callback_query(F.data.startswith("pay:back:"))
async def pay_back(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()
    await c.message.edit_reply_markup(reply_markup=None)
    await c.answer(t(lang, "pay-back"))

def _estimate_total(date_from_iso: str, date_to_iso: str, price_wd, price_we) -> int:
    start = datetime.fromisoformat(date_from_iso)
    end   = datetime.fromisoformat(date_to_iso)
    total = Decimal("0")
    d = start
    price_wd = Decimal(str(price_wd or 0))
    price_we = Decimal(str(price_we or price_wd or 0))
    while d < end:
        total += price_we if d.weekday() >= 5 else price_wd
        d = d.replace(day=d.day) + timedelta(days=1)
    return int(total)

@router.callback_query(F.data.startswith("paygw:"))
async def pay_gateway(c: CallbackQuery, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, c.from_user.id, await state.get_data())
    await api.close()

    _, gw, mode, bid = c.data.split(":")
    bid = int(bid)

    # 1) Получаем бронь
    api = ApiClient()
    try:
        booking = await api.get(f"/bookings/{bid}/")
    except Exception as e:
        await c.message.answer(t(lang, "my-error", error=str(e)))
        await api.close()
        return await c.answer()
    finally:
        await api.close()

    # 2) Сумма
    try:
        if mode == "full":
            amount = _estimate_total(
                booking["date_from"], booking["date_to"],
                booking.get("price_weekday"), booking.get("price_weekend")
            )
        else:
            adv = booking.get("advance_amount") or 0
            amount = int(float(adv))
        if amount <= 0:
            raise ValueError("amount <= 0")
    except Exception:
        await c.message.answer(t(lang, "my-error", error="Не удалось рассчитать сумму оплаты"))
        return await c.answer()

    # 3) Платёж
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
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "pay-go"), url=pay_url)]])
        sent = await c.message.answer(t(lang, "pay-instruction"), reply_markup=kb)
        try:
            d = PAYMENT_MSGS.setdefault(c.from_user.id, {})
            d.setdefault(bid, []).append(sent.message_id)
        except Exception:
            pass
    else:
        await c.message.answer(t(lang, "pay-no-link"))
    await c.answer()
