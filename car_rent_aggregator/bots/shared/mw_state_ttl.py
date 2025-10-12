from __future__ import annotations
import time
from typing import Callable, Any, Optional
from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

DEFAULT_TTL_SEC = 10 * 60  # 10 минут

class StateTTLMiddleware(BaseMiddleware):
    """
    Если пользователь «замолчал» в середине сценария дольше TTL,
    очищаем состояние и отправляем дружелюбное сообщение.
    """
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SEC):
        self.ttl = max(30, int(ttl_seconds))  # минимум 30 сек, чтобы не мешать

    async def __call__(self, handler: Callable, event: Message | CallbackQuery, data: dict[str, Any]):
        state: Optional[FSMContext] = data.get("state")
        bot = data.get("bot")

        if not state:
            return await handler(event, data)

        # определяем chat_id для ответа
        chat_id = None
        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = event.message.chat.id

        # проверяем таймаут только если есть активное состояние
        try:
            cur_state = await state.get_state()
            if cur_state is None:
                # нет активного сценария — просто записываем "активность"
                await state.update_data(_last_activity=time.time())
                return await handler(event, data)

            data_now = await state.get_data()
            last = float(data_now.get("_last_activity", 0.0))
            now = time.time()

            if last and (now - last) > self.ttl:
                # истек таймаут — сбрасываем и мягко уведомляем
                selected_lang = (data_now.get("selected_lang") or "ru").lower()
                await state.clear()
                if bot and chat_id:
                    # короткое нейтральное уведомление (без i18n: язык берём из state)
                    txt = {
                        "ru": "⏳ Сессия истекла. Давайте начнём заново: нажмите «Главное меню» → «Найти авто».",
                        "uz": "⏳ Sessiya muddati tugadi. Qaytadan boshlaymiz: «Asosiy menyu» → «Mashina topish».",
                        "en": "⏳ Session expired. Please start again: Main menu → Find a car.",
                    }.get(selected_lang, "⏳ Session expired.")
                    try:
                        await bot.send_message(chat_id, txt)
                    except Exception:
                        pass
                # После очистки — продолжаем пайплайн уже без состояния
                return await handler(event, data)

            # если не истёк, просто обновим "последнюю активность"
            await state.update_data(_last_activity=now)

        except Exception:
            # на всякий случай не роняем цепочку
            pass

        return await handler(event, data)
