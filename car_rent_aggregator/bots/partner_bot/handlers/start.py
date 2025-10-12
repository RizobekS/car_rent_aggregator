# bots/partner_bot/handlers/start.py
from aiogram import Router, F
from aiogram.types import Message
from bots.shared.api_client import ApiClient
from bots.partner_bot.poller import subscribe_partner

router = Router()

@router.message(F.text == "/start")
async def cmd_start(m: Message):
    # Авто-подписка (если уже подписан — вернётся False и всё ок)
    subscribe_partner(m.bot, m.chat.id, m.from_user.username)
    await m.answer(
        "Партнёр-бот.\nКоманды:\n"
        "- /link — привязать аккаунт по username и включить уведомления\n"
        "- /requests — новые заявки\n"
        "- /subscribe — включить автоуведомления\n"
        "- /unsubscribe — выключить автоуведомления\n\n"
        "Автоуведомления активированы. Новые заявки будут приходить автоматически."
    )

@router.message(F.text == "/link")
async def link_account(m: Message):
    if not m.from_user.username:
        return await m.answer("У вас нет username в Telegram. Установите его в настройках и повторите /link.")

    api = ApiClient()
    try:
        payload = {"username": m.from_user.username, "tg_user_id": m.from_user.id}
        await api.post("/partners/link/", json=payload)
    except Exception as e:
        await m.answer(f"Не удалось привязать: {e}")
    else:
        subscribe_partner(m.bot, m.chat.id, m.from_user.username)
        await m.answer(
            "Аккаунт привязан ✅.\n"
            "Оповещения о новых заявках включены автоматически. "
            "Отключить: /unsubscribe\nПроверить заявки: /requests"
        )
    finally:
        await api.close()
