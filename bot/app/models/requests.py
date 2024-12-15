from typing import Union

from pydantic import BaseModel


class Requests(BaseModel):
    request_id: str
    sender: int
    opponent: int
    group_id: int
    time_sent: float
    message_id: int
    chat_id: int
