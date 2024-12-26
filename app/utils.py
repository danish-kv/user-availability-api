from datetime import datetime, timedelta
from typing import List
import pytz
from .schemas import TimeSlot

def get_day_of_week(date: datetime) -> str:
    return date.strftime("%A")

def convert_to_timezone(time: datetime, from_tz: str, to_tz: str) -> datetime:
    from_zone = pytz.timezone(from_tz)
    to_zone = pytz.timezone(to_tz)
    localized_time = from_zone.localize(time)
    return localized_time.astimezone(to_zone)

def get_time_slots(start_time: datetime, end_time: datetime, slot_duration: int = 30) -> List[str]:
    slots = []
    current = start_time
    while current < end_time:
        slot_end = current + timedelta(minutes=slot_duration)
        if slot_end > end_time:
            break
        slots.append(f"{current.strftime('%I:%M%p').lower()}-{slot_end.strftime('%I:%M%p').lower()}")
        current = slot_end
    return slots

def merge_time_slots(slots1: List[TimeSlot], slots2: List[TimeSlot]) -> List[TimeSlot]:
    """Find common time slots between two lists of time slots"""
    result = []
    for slot1 in slots1:
        for slot2 in slots2:
            if slot1.start < slot2.end and slot2.start < slot1.end:
                result.append(TimeSlot(
                    start=max(slot1.start, slot2.start),
                    end=min(slot1.end, slot2.end)
                ))
    return result
