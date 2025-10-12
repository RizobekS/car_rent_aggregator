import asyncio
from aiogram import Bot, Dispatcher
from bots.shared.mw_antiflood import AntiFloodMiddleware
from bots.shared.mw_state_ttl import StateTTLMiddleware
from bots.shared.config import settings
from bots.shared.logger import setup_logging
from .handlers import start, search, bookings, fallbacks

# после создания dp/dispatcher
dp = Dispatcher()

# Global middlewares
dp.message.middleware(AntiFloodMiddleware(
    cooldown_message=0.5,  # обычные сообщения
    cooldown_command=2.0,  # команды /start и т.п.
    cooldown_callback=0.2  # инлайн-кнопки
))
dp.callback_query.middleware(AntiFloodMiddleware(
    cooldown_message=0.5,
    cooldown_command=2.0,
    cooldown_callback=0.2
))

dp.message.middleware(StateTTLMiddleware(ttl_seconds=10 * 60))      # 10 минут
dp.callback_query.middleware(StateTTLMiddleware(ttl_seconds=10 * 60))

async def main():
    log = setup_logging("client-bot")
    bot = Bot(settings.token_client)
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(search.router)
    dp.include_router(bookings.router)
    dp.include_router(fallbacks.router)
    log.info("Client bot started (polling)")
    try:
        await dp.start_polling(bot)
    except (asyncio.CancelledError, KeyboardInterrupt):
        log.info("Client bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
