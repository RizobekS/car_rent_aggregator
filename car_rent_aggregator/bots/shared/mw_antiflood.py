from __future__ import annotations
import time
from typing import Callable, Dict, Tuple, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

class AntiFloodMiddleware(BaseMiddleware):
    """
    Простая per-user защита от спама.
    - Разные cooldown для команд ("/start") и обычных сообщений.
    - Применяется и к Message, и к CallbackQuery.
    """
    def __init__(self, cooldown_message: float = 0.5, cooldown_command: float = 2.0, cooldown_callback: float = 0.2):
        self.cooldown_message = cooldown_message
        self.cooldown_command = cooldown_command
        self.cooldown_callback = cooldown_callback
        self._last: Dict[Tuple[int, str], float] = {}

    async def __call__(self, handler: Callable, event: Message | CallbackQuery, data: dict[str, Any]):
        now = time.monotonic()

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else 0
            is_command = bool(event.text and event.text.startswith("/"))
            kind = "command" if is_command else "message"
            cd = self.cooldown_command if is_command else self.cooldown_message

        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else 0
            kind = "callback"
            cd = self.cooldown_callback

        else:
            return await handler(event, data)

        key = (user_id, kind)
        last = self._last.get(key, 0.0)
        if now - last < cd:
            # тихо отбрасываем избыточные апдейты
            if isinstance(event, CallbackQuery):
                try: await event.answer()
                except Exception: pass
            return

        self._last[key] = now
        return await handler(event, data)
