import asyncio
from aiogram import Bot, Dispatcher, F
from bots.shared.config import settings
from bots.shared.logger import setup_logging
from .handlers import start, requests, cars
from .poller import subscribe_partner, unsubscribe_partner

async def cmd_subscribe(m, bot):
    already = not subscribe_partner(bot, m.chat.id, m.from_user.username)
    if already:
        await m.answer("Вы уже подписаны на уведомления о новых заявках.")
    else:
        await m.answer("Подписка оформлена. Будем присылать новые заявки автоматически.")

async def cmd_unsubscribe(m):
    ok = unsubscribe_partner(m.chat.id)
    if ok:
        await m.answer("Подписка отключена.")
    else:
        await m.answer("Подписка уже была отключена.")

async def main():
    log = setup_logging("partner-bot")
    bot = Bot(settings.token_partner)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(requests.router)
    dp.include_router(cars.router)

    dp.message.register(lambda m: cmd_subscribe(m, bot), F.text == "/subscribe")
    dp.message.register(cmd_unsubscribe, F.text == "/unsubscribe")

    log.info("Partner bot started (polling)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
