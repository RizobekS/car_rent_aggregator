from aiogram import Router, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, CallbackQuery
)
from aiogram.fsm.context import FSMContext
from bots.client_bot.states import SearchStates, BookingStates
from bots.client_bot.poller import ensure_client_subscription
from bots.shared.api_client import ApiClient
from bots.shared.i18n import t, resolve_user_lang, SUPPORTED
import re
from datetime import datetime, date
from pathlib import Path

router = Router()

# --------- Файлы оферты/политики ---------
CLIENT_ROOT = Path(__file__).resolve().parent.parent
LEGAL_DIR = CLIENT_ROOT / "assets" / "legal"
LEGAL_OFFER_FILE = LEGAL_DIR / "offer.pdf"
LEGAL_PRIVACY_FILE = LEGAL_DIR / "privacy.pdf"

# --------- Клавиатуры ---------
def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "menu-find"))],
            [KeyboardButton(text=t(lang, "menu-bookings")), KeyboardButton(text=t(lang, "menu-help"))],
            [KeyboardButton(text=t(lang, "menu-language"))],
        ],
        resize_keyboard=True
    )

def kb_request_phone(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "phone-send"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def kb_legal_consent(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "legal-offer"),   callback_data="legal:offer"),
            InlineKeyboardButton(text=t(lang, "legal-privacy"), callback_data="legal:privacy"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "legal-agree"),   callback_data="legal:agree"),
            InlineKeyboardButton(text=t(lang, "legal-decline"), callback_data="legal:decline"),
        ]
    ])

def kb_language_picker() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 Oʻzbekcha", callback_data="lang:set:uz"),
        InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="lang:set:ru"),
        InlineKeyboardButton(text="🇬🇧 English",   callback_data="lang:set:en"),
    ]])

# --------- Утилиты для матчей по локализованным кнопкам ---------
def is_find_btn(text: str) -> bool:
    return any(text == t(lg, "menu-find") for lg in SUPPORTED)

def is_my_bookings_btn(text: str) -> bool:
    return any(text == t(lg, "menu-bookings") for lg in SUPPORTED)

def is_help_btn(text: str) -> bool:
    return any(text == t(lg, "menu-help") for lg in SUPPORTED)

def is_lang_btn(text: str) -> bool:
    return any(text == t(lg, "menu-language") for lg in SUPPORTED)

# --------- /start ---------
@router.message(F.text == "/start")
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    ensure_client_subscription(m.bot, m.chat.id)

    api = ApiClient()
    try:
        resp = await api.get("/users/check/", params={"tg_user_id": m.from_user.id})
    except Exception:
        resp = {"exists": False}
    finally:
        await api.close()

    # язык для первичного ответа
    pref_api = ApiClient()
    lang = await resolve_user_lang(pref_api, m.from_user.id, await state.get_data())
    await pref_api.close()

    if not resp.get("exists"):
        await state.set_state(SearchStates.LANG)
        await m.answer(t(lang, "start-pick-language"), reply_markup=kb_language_picker())
        return

    await m.answer(t(lang, "start-welcome", menu_find=t(lang, "menu-find")), reply_markup=main_menu(lang))

# --------- Смена языка ---------
@router.message(F.text.func(is_lang_btn))
async def change_lang_menu(m: Message, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data()); await api.close()
    await m.answer(t(lang, "start-pick-language"), reply_markup=kb_language_picker())

@router.callback_query(F.data.startswith("lang:set:"))
async def set_language(c: CallbackQuery, state: FSMContext):
    lang = c.data.split(":")[2]  # uz|ru|en
    await state.update_data(selected_lang=lang)

    await c.message.answer(
        t(lang, "lang-set-ok", done=lang, menu_find=t(lang, "menu-find")),
        reply_markup=main_menu(lang)
    )
    await c.answer()

# ===== Регистрация =====

# 1) Телефон кнопкой
@router.message(SearchStates.PHONE, F.contact)
async def got_contact(m: Message, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, m.from_user.id, await state.get_data()); await api.close()
    phone = m.contact.phone_number.replace(" ", "")
    await state.update_data(phone=phone)
    await state.set_state(SearchStates.FIRST_NAME)
    await m.answer(t(lang, "reg-ask-first"))

# 1b) Телефон руками
PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{6,}$")

@router.message(SearchStates.PHONE, F.text.regexp(PHONE_RE.pattern))
async def got_phone_text(m: Message, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, m.from_user.id, await state.get_data()); await api.close()
    phone = m.text.replace(" ", "")
    await state.update_data(phone=phone)
    await state.set_state(SearchStates.FIRST_NAME)
    await m.answer(t(lang, "reg-ask-first"))

@router.message(SearchStates.PHONE)
async def ask_phone_again(m: Message, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, m.from_user.id, await state.get_data()); await api.close()
    await m.answer(t(lang, "phone-again"), reply_markup=kb_request_phone(lang))

# 2) Имя
@router.message(SearchStates.FIRST_NAME, F.text)
async def got_first_name(m: Message, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, m.from_user.id, await state.get_data()); await api.close()
    first = m.text.strip()
    if not first or len(first) < 2:
        return await m.answer(t(lang, "reg-first-short"))
    await state.update_data(first_name=first)
    await state.set_state(SearchStates.LAST_NAME)
    await m.answer(t(lang, "reg-ask-last"))

# 3) Фамилия -> оферта/политика
@router.message(SearchStates.LAST_NAME, F.text)
async def got_last_name_show_legal(m: Message, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, m.from_user.id, await state.get_data()); await api.close()
    last = m.text.strip()
    if not last or len(last) < 2:
        return await m.answer(t(lang, "reg-last-short"))
    await state.update_data(last_name=last)
    await state.set_state(SearchStates.BIRTH_DATE)
    await m.answer(t(lang, "reg-ask-birth"))

@router.message(SearchStates.BIRTH_DATE, F.text)
async def reg_birth_date(m: Message, state: FSMContext):
    api_lang = await resolve_user_lang(ApiClient(), m.from_user.id, await state.get_data())
    lang = api_lang  # коротко

    raw = (m.text or "").strip()

    # пробуем распарсить DD.MM.YYYY
    try:
        bdate = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await m.answer(
            t(lang, "reg-birth-invalid")
        )
        return

    # считаем возраст
    today = date.today()
    age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))

    if age < 18:
        await m.answer(
            t(lang, "reg-birth-too-young")
        )
        await state.clear()
        return

    await state.update_data(birth_date=raw)

    # идём на стаж
    await state.set_state(SearchStates.DRIVE_EXP)
    await m.answer(
        t(lang, "reg-ask-drive-exp")
    )

@router.message(SearchStates.DRIVE_EXP, F.text)
async def reg_drive_exp(m: Message, state: FSMContext):
    api = ApiClient()
    lang = await resolve_user_lang(api, m.from_user.id, await state.get_data())
    await api.close()

    raw = (m.text or "").strip()

    if not raw.isdigit():
        await m.answer(
            t(lang, "reg-drive-exp-invalid")
        )
        return

    years = int(raw)
    if years <= 0:
        await m.answer(
            t(lang, "reg-drive-exp-invalid")
        )
        return

    await state.update_data(drive_exp=years)

    if LEGAL_OFFER_FILE.exists():
        try:
            await m.answer_document(FSInputFile(str(LEGAL_OFFER_FILE)), caption=t(lang, "legal-offer"))
        except Exception:
            pass
    if LEGAL_PRIVACY_FILE.exists():
        try:
            await m.answer_document(FSInputFile(str(LEGAL_PRIVACY_FILE)), caption=t(lang, "legal-privacy"))
        except Exception:
            pass

    await state.set_state(SearchStates.TERMS)
    await m.answer(t(lang, "legal-prompt"), reply_markup=kb_legal_consent(lang))

# 4) Файлы/согласие/отмена
@router.callback_query(SearchStates.TERMS, F.data == "legal:offer")
async def send_offer(c: CallbackQuery, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, c.from_user.id, await state.get_data()); await api.close()
    if LEGAL_OFFER_FILE.exists():
        try:
            await c.message.answer_document(FSInputFile(str(LEGAL_OFFER_FILE)), caption=t(lang, "legal-offer"))
        except Exception:
            await c.message.answer(t(lang, "legal-send-offer-fail"))
    else:
        await c.message.answer(t(lang, "legal-offer-missing"))
    await c.answer()

@router.callback_query(SearchStates.TERMS, F.data == "legal:privacy")
async def send_privacy(c: CallbackQuery, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, c.from_user.id, await state.get_data()); await api.close()
    if LEGAL_PRIVACY_FILE.exists():
        try:
            await c.message.answer_document(FSInputFile(str(LEGAL_PRIVACY_FILE)), caption=t(lang, "legal-privacy"))
        except Exception:
            await c.message.answer(t(lang, "legal-send-privacy-fail"))
    else:
        await c.message.answer(t(lang, "legal-privacy-missing"))
    await c.answer()

@router.callback_query(SearchStates.TERMS, F.data == "legal:decline")
async def legal_decline(c: CallbackQuery, state: FSMContext):
    api = ApiClient(); lang = await resolve_user_lang(api, c.from_user.id, await state.get_data()); await api.close()
    await state.clear()
    await c.message.edit_text(t(lang, "legal-declined"))
    await c.message.answer(t(lang, "menu-title"), reply_markup=main_menu(lang))
    await c.answer()

@router.callback_query(SearchStates.TERMS, F.data == "legal:agree")
async def legal_agree_and_register(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    api = ApiClient(); lang = await resolve_user_lang(api, c.from_user.id, await state.get_data()); await api.close()

    payload = {
        "tg_user_id": c.from_user.id,
        "username": (c.from_user.username or None),
        "first_name": data.get("first_name"),
        "last_name":  data.get("last_name"),
        "phone":      data.get("phone"),
        "language":   lang,
        "birth_date": data.get("birth_date"),
        "drive_exp": data.get("drive_exp"),
    }

    api = ApiClient()
    try:
        await api.post("/users/register/", json=payload)
    except Exception as e:
        await c.message.edit_text(t(lang, "reg-fail", error=str(e)))
        await api.close()
        await c.answer()
        return

    # отложенная бронь
    car_id    = data.get("selected_car_id")
    car_title = data.get("selected_car_title")
    date_from = data.get("date_from")
    date_to   = data.get("date_to")

    if car_id and date_from and date_to:
        try:
            await api.post("/bookings/", json={
                "client_tg_user_id": c.from_user.id,
                "car_id": int(car_id),
                "date_from": date_from,
                "date_to":   date_to,
            })
            await c.message.edit_text(
                t(lang, "book-created", title=car_title,
                  start=datetime.fromisoformat(date_from).strftime("%d.%m.%Y"),
                  end=datetime.fromisoformat(date_to).strftime("%d.%m.%Y"))
            )
        except Exception as e:
            await c.message.edit_text(t(lang, "book-create-fail", error=str(e)))
        finally:
            await api.close()
            ensure_client_subscription(c.bot, c.message.chat.id)
            await state.clear()
            await c.answer()
        return

    await api.close()
    await c.message.edit_text(t(lang, "reg-ok"))
    ensure_client_subscription(c.bot, c.message.chat.id)
    await state.clear()
    await c.message.answer(t(lang, "menu-title"), reply_markup=main_menu(lang))
    await c.answer()
