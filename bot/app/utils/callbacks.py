from aiogram.filters.callback_data import CallbackData


class Confirm(CallbackData, prefix='confirm'):
    request_id: str

class Cancel(CallbackData, prefix='cancel'):
    request_id: str

class Move(CallbackData, prefix='move'):
    choice: str
    duel_id: str