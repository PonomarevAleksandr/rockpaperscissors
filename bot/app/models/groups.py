from typing import Dict
from pydantic import BaseModel
from datetime import datetime


class Groups(BaseModel):
    group_id: int
    group_name: str
    date_added: float

