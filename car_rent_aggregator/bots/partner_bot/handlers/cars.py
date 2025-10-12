from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text == "/cars")
async def my_cars(m: Message):
    await m.answer("«Мой автопарк» будет доступен через защищённые эндпоинты.\n"
                   "Пока редактируйте автопарк через Веб интерфейс.")
