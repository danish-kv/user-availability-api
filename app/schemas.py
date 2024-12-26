
from typing import List, Dict
from pydantic import BaseModel
from datetime import datetime

class TimeSlot(BaseModel):
    start: datetime
    end: datetime

class AvailabilityRequest(BaseModel):
    user_ids: List[int]
    date_range: List[datetime]  # [start_date, end_date]
    timezone: str

class AvailabilityResponse(BaseModel):
    availability: Dict[str, List[str]]