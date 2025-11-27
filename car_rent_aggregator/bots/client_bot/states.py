from aiogram.fsm.state import StatesGroup, State

class SearchStates(StatesGroup):
    LANG = State()
    PHONE = State()
    FIRST_NAME = State()
    LAST_NAME = State()
    BIRTH_DATE = State()
    DRIVE_EXP = State()
    TERMS = State()

    DATE_FROM = State()
    DATE_TO = State()
    CLASS = State()
    GEARBOX = State()
    PRICE = State()
    RESULTS = State()

class BookingStates(StatesGroup):
    SELFIE = State()
    CONFIRM = State()


class PaymentStates(StatesGroup):
    AWAIT_METHOD = State()
    AWAIT_TYPE = State()
    AWAIT_PROVIDER = State()


