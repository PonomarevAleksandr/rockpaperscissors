from typing import Dict
from pydantic import BaseModel
from datetime import datetime


class Stats(BaseModel):
    _id: int
    group_id: int
    user_id: int
    username: str
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    date_added: float