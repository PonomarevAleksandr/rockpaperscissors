from typing import Dict
from pydantic import BaseModel
from datetime import datetime


class Duels(BaseModel):
    duel_id: str
    group_id: int
    opponent: int
    sender: int
    time_start: float
    last_updated: float
    opponent_choice: str = None
    sender_choice: str = None


