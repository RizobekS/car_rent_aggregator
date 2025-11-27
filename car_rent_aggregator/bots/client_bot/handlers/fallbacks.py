from __future__ import annotations
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bots.shared.api_client import ApiClient
from bots.shared.i18n import t, resolve_user_lang
from bots.client_bot.states import SearchStates, BookingStates

from bots.client_bot.handlers.start import kb_request_phone, kb_legal_consent, kb_language_picker
from bots.client_bot.handlers.search import build_calendar, kb_class_with_back, kb_confirm_booking

router = Router()

# --------- Утилита: быстрый язык пользователя ---------
async def _lang_for(event_user_id: int, state: FSMContext) -> str:
    api = ApiClient()
    lang = await resolve_user_lang(api, event_user_id, await state.get_data())
    await api.close()
    return lang


# =========================
#   FALLBACKS ПО STATE
# =========================

# --- LANG: если прислали что-то вместо нажатия кнопки выбора языка ---
@router.message(SearchStates.LANG)
async def fb_lang_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    # Просто повторяем приглашение выбрать язык (клавиатуру покажет хендлер смены языка)
    await m.answer(t(lang, "start-pick-language"), reply_markup=kb_language_picker())

@router.callback_query(SearchStates.LANG)
async def fb_lang_cb(c: CallbackQuery, state: FSMContext):
    # Ничего особенного, пусть жмут одну из кнопок выбора языка
    lang = await _lang_for(c.from_user.id, state)
    await c.message.edit_text(t(lang, "start-pick-language"), reply_markup=kb_language_picker())
    await c.answer()


# --- PHONE: просим ещё раз отправить контакт/телефон ---
@router.message(SearchStates.PHONE)
async def fb_phone_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    await m.answer(t(lang, "phone-again"), reply_markup=kb_request_phone(lang))

@router.callback_query(SearchStates.PHONE)
async def fb_phone_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    await c.message.answer(t(lang, "phone-again"), reply_markup=kb_request_phone(lang))
    await c.answer()


# --- FIRST_NAME: просим ввести имя ещё раз ---
@router.message(SearchStates.FIRST_NAME)
async def fb_first_name_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    await m.answer(t(lang, "reg-ask-first"))

@router.callback_query(SearchStates.FIRST_NAME)
async def fb_first_name_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    await c.message.answer(t(lang, "reg-ask-first"))
    await c.answer()


# --- LAST_NAME: просим ввести фамилию ещё раз ---
@router.message(SearchStates.LAST_NAME)
async def fb_last_name_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    await m.answer(t(lang, "reg-ask-last"))

@router.callback_query(SearchStates.LAST_NAME)
async def fb_last_name_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    await c.message.answer(t(lang, "reg-ask-last"))
    await c.answer()

@router.message(SearchStates.BIRTH_DATE)
async def fb_birth_date_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    await m.answer(t(lang, "reg-ask-birth"))

@router.callback_query(SearchStates.BIRTH_DATE)
async def fb_birth_date_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    await c.message.answer(t(lang, "reg-ask-birth"))
    await c.answer()

@router.message(SearchStates.DRIVE_EXP)
async def fb_drive_exp_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    await m.answer(t(lang, "reg-ask-drive-exp"))

@router.callback_query(SearchStates.DRIVE_EXP)
async def fb_drive_exp_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    await c.message.answer(t(lang, "reg-ask-drive-exp"))
    await c.answer()


# --- TERMS: показываем ещё раз клавиатуру согласия/ознакомления ---
@router.message(SearchStates.TERMS)
async def fb_terms_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    await m.answer(t(lang, "legal-prompt"), reply_markup=kb_legal_consent(lang))

@router.callback_query(SearchStates.TERMS)
async def fb_terms_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    await c.message.edit_text(t(lang, "legal-prompt"), reply_markup=kb_legal_consent(lang))
    await c.answer()


# --- DATE_FROM: снова календарь на выбор начальной даты ---
@router.message(SearchStates.DATE_FROM)
async def fb_date_from_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    today = date.today()
    await m.answer(t(lang, "search-date-from"), reply_markup=build_calendar(today.year, today.month, lang, min_sel=today))

@router.callback_query(SearchStates.DATE_FROM)
async def fb_date_from_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    today = date.today()
    await c.message.edit_text(t(lang, "search-date-from"), reply_markup=build_calendar(today.year, today.month, lang, min_sel=today))
    await c.answer()


# --- DATE_TO: снова календарь на выбор конечной даты ---
@router.message(SearchStates.DATE_TO)
async def fb_date_to_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    data = await state.get_data()
    start_iso = data.get("date_from")
    if start_iso:
        from datetime import datetime as _dt
        start = _dt.fromisoformat(start_iso).date()
        await m.answer(
            t(lang, "search-date-to", start=f"{start:%d.%m.%Y}"),
            reply_markup=build_calendar(start.year, start.month, lang, min_sel=date.today(), disable_to=start)
        )
    else:
        # если почему-то нет стартовой даты — вернёмся на первый шаг
        today = date.today()
        await m.answer(t(lang, "search-date-from"), reply_markup=build_calendar(today.year, today.month, lang, min_sel=today))

@router.callback_query(SearchStates.DATE_TO)
async def fb_date_to_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    data = await state.get_data()
    start_iso = data.get("date_from")
    if start_iso:
        from datetime import datetime as _dt
        start = _dt.fromisoformat(start_iso).date()
        await c.message.edit_text(
            t(lang, "search-date-to", start=f"{start:%d.%m.%Y}"),
            reply_markup=build_calendar(start.year, start.month, lang, min_sel=date.today(), disable_to=start)
        )
    else:
        today = date.today()
        await c.message.edit_text(t(lang, "search-date-from"), reply_markup=build_calendar(today.year, today.month, lang, min_sel=today))
    await c.answer()


# --- CLASS: повторно просим выбрать класс ---
@router.message(SearchStates.CLASS)
async def fb_class_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    await m.answer(t(lang, "search-classes-head"), reply_markup=kb_class_with_back(lang))

@router.callback_query(SearchStates.CLASS)
async def fb_class_cb(c: CallbackQuery, state: FSMContext):
    lang = await _lang_for(c.from_user.id, state)
    await c.message.edit_text(t(lang, "search-classes-head"), reply_markup=kb_class_with_back(lang))
    await c.answer()


# --- RESULTS: если пользователь пишет текст — подскажем действия ---
@router.message(SearchStates.RESULTS)
async def fb_results_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    # краткая подсказка: «используйте кнопки под карточками»
    hint = {
        "ru": "Используйте кнопки под карточками: «Подробнее», «Условия», «Отзывы», «Забронировать».",
        "uz": "Kartochkalar ostidagi tugmalardan foydalaning: “Batafsil”, “Shartlar”, “Sharhlar”, “Bron qilish”.",
        "en": "Use buttons under cards: “More”, “Terms”, “Reviews”, “Book”.",
    }.get(lang, "Use buttons under cards.")
    await m.answer(hint)

@router.callback_query(SearchStates.RESULTS)
async def fb_results_cb(c: CallbackQuery, state: FSMContext):
    # Сюда попадают нестандартные callback-и; просто закроем «часики».
    try:
        await c.answer()
    except Exception:
        pass


# --- BOOKING CONFIRM: если прислали что-то, кроме нажатия confirm/cancel ---
@router.message(BookingStates.CONFIRM)
async def fb_booking_confirm_msg(m: Message, state: FSMContext):
    lang = await _lang_for(m.from_user.id, state)
    # мягко напомним юзеру нажать кнопку
    await m.answer(
        t(lang, "book-preview-ask"),
        reply_markup=kb_confirm_booking(lang)
    )

@router.callback_query(BookingStates.CONFIRM)
async def fb_booking_confirm_cb(c: CallbackQuery, state: FSMContext):
    # если прилетел левый callback, просто гасим "часики"
    try:
        await c.answer()
    except Exception:
        pass


@router.callback_query()
async def any_other_callback(c: CallbackQuery, state: FSMContext):
    """
    Ловим клики по старым/просроченным инлайн-кнопкам, когда FSM уже ушёл
    в другое состояние или вообще стейт пустой. Вместо того чтобы "зависать",
    вежливо просим пройти поиск заново.
    """
    data = await state.get_data()
    lang = await _lang_for(c.from_user.id, state)

    # Если стейт ещё валидный (RESULTS/CONFIRM), значит это не наш случай.
    current_state = await state.get_state()
    if current_state in (SearchStates.RESULTS.state, BookingStates.CONFIRM.state):
        # ничего не делаем — это значит, что конкретный callback просто не сматчился
        try:
            await c.answer()
        except Exception:
            pass
        return

    # state пустой/устарел -> подсказка
    try:
        await c.message.answer(
            t(lang, "session-expired", menu_find=t(lang, "menu-find"))
        )
    except Exception:
        pass

    try:
        await c.answer()
    except Exception:
        pass
