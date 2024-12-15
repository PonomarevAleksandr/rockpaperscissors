from aiogram.filters.callback_data import CallbackData


class Confirm(CallbackData, prefix='confirm'):
    sender: int
    opponent: int
    time_send: float

class Cancel(CallbackData, prefix='cancel'):
    sender: int
    opponent: int
    time_sent: float