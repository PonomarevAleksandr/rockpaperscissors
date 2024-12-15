from typing import Dict, Optional
from pydantic import BaseModel
from datetime import datetime


class Duels(BaseModel):
    duel_id: str
    group_id: int = 0
    opponent: int= 0
    sender: int = 0
    message_id: int = 0
    time_start: float = 0.0
    last_updated: float = 0.0
    sender_choice: Optional[str] = None
    opponent_choice: Optional[str] = None


