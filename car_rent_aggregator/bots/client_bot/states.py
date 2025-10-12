from aiogram.fsm.state import StatesGroup, State

class SearchStates(StatesGroup):
    LANG = State()
    PHONE = State()
    FIRST_NAME = State()
    LAST_NAME = State()
    TERMS = State()

    DATE_FROM = State()
    DATE_TO = State()
    CLASS = State()
    GEARBOX = State()
    PRICE = State()
    RESULTS = State()

class BookingStates(StatesGroup):
    CONFIRM = State()

