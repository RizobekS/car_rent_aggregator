import asyncio
from aiogram import Bot
from bots.shared.api_client import ApiClient

SEEN: dict[int, set[int]] = {}  # chat_id -> set(booking_ids)

async def notify_loop(bot: Bot, chat_id: int, username: str | None):
    """
    Каждые 20 сек подтягиваем pending-заявки партнёра и шлём новые.
    """
    while True:
        try:
            api = ApiClient()
            params = {"status": "pending"}  # без fresh_minutes, сами отфильтруем SEEN
            if username: params["partner_username"] = username
            else: params["partner_tg_user_id"] = chat_id
            items = await api.get("/bookings/", params=params)
            await api.close()

            seen = SEEN.setdefault(chat_id, set())
            for b in items:
                bid = b["id"]
                if bid in seen:
                    continue
                seen.add(bid)
                text = (f"🆕 Новая заявка #{bid} • {b['car_title']}\n"
                        f"{b['date_from'][:10]}→{b['date_to'][:10]}\n"
                        "Откройте /requests для подтверждения/отклонения.")
                await bot.send_message(chat_id, text)
        except Exception:
            pass
        await asyncio.sleep(20)

SUB_TASKS: dict[int, asyncio.Task] = {}

def subscribe_partner(bot: Bot, chat_id: int, username: str | None):
    t = SUB_TASKS.get(chat_id)
    if t and not t.done():
        return False  # уже подписан
    SUB_TASKS[chat_id] = asyncio.create_task(notify_loop(bot, chat_id, username))
    return True

def unsubscribe_partner(chat_id: int):
    t = SUB_TASKS.get(chat_id)
    if t and not t.done():
        t.cancel()
        return True
    return False
