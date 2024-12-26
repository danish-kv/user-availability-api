# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict
from .database import Base, engine, get_db
from .models import User, WeeklyAvailability, SpecificDateAvailability, Event
from .schemas import AvailabilityRequest, AvailabilityResponse, TimeSlot
from .utils import get_day_of_week, convert_to_timezone, get_time_slots, merge_time_slots

app = FastAPI(title="Availability API")

# Create database tables
Base.metadata.create_all(bind=engine)

@app.get('/')
def hello():
    return {'message': "Welcome to Availability API"}

@app.post("/availability", response_model=AvailabilityResponse)
def get_common_availability(
    request: AvailabilityRequest,
    db: Session = Depends(get_db),
):
    user_ids = request.user_ids
    start_date = request.date_range[0]
    end_date = request.date_range[1]
    timezone = request.timezone

    print(user_ids)

    # Validate users exist
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    if len(users) != len(user_ids):
        raise HTTPException(status_code=404, message="One or more users not found")

    availability = {}
    current_date = start_date

    while current_date <= end_date:
        day_of_week = get_day_of_week(current_date)
        all_user_slots = []

        for user in users:
            # Get weekly availability
            weekly_slots = db.query(WeeklyAvailability).filter(
                WeeklyAvailability.user_id == user.id,
                WeeklyAvailability.day_of_week == day_of_week
            ).all()

            print(weekly_slots)

            # Get specific date availability
            specific_slots = db.query(SpecificDateAvailability).filter(
                SpecificDateAvailability.user_id == user.id,
                SpecificDateAvailability.specific_date == current_date
            ).all()

            print('specific_slots ====',specific_slots)

            # Get events (conflicts)
            events = db.query(Event).filter(
                Event.user_id == user.id,
                Event.event_date == current_date
            ).all()

            # Convert all times to requested timezone
            available_slots = []
            
            # Process weekly slots
            for slot in weekly_slots:
                start = convert_to_timezone(
                    datetime.combine(current_date, slot.start_time),
                    user.timezone,
                    timezone
                )
                end = convert_to_timezone(
                    datetime.combine(current_date, slot.end_time),
                    user.timezone,
                    timezone
                )
                available_slots.append(TimeSlot(start=start, end=end))

            # Process specific date slots (override weekly slots)
            for slot in specific_slots:
                start = convert_to_timezone(
                    datetime.combine(current_date, slot.start_time),
                    user.timezone,
                    timezone
                )
                end = convert_to_timezone(
                    datetime.combine(current_date, slot.end_time),
                    user.timezone,
                    timezone
                )
                available_slots.append(TimeSlot(start=start, end=end))

            # Remove event conflicts
            for event in events:
                event_start = convert_to_timezone(
                    datetime.combine(current_date, event.start_time),
                    user.timezone,
                    timezone
                )
                event_end = convert_to_timezone(
                    datetime.combine(current_date, event.end_time),
                    user.timezone,
                    timezone
                )
                available_slots = [
                    slot for slot in available_slots
                    if not (event_start < slot.end and event_end > slot.start)
                ]

            all_user_slots.append(available_slots)

        # Find common slots among all users
        common_slots = []
        if all_user_slots:
            common_slots = all_user_slots[0]
            for user_slots in all_user_slots[1:]:
                common_slots = merge_time_slots(common_slots, user_slots)

        # Convert common slots to 30-minute intervals
        formatted_slots = []
        for slot in common_slots:
            formatted_slots.extend(get_time_slots(slot.start, slot.end))

        if formatted_slots:
            availability[current_date.strftime("%d-%m-%Y")] = formatted_slots

        current_date += timedelta(days=1)

    return {"availability": availability}

# Add these routes for testing and data management
@app.post("/users/")
def create_user(name: str, timezone: str, db: Session = Depends(get_db)):
    user = User(name=name, timezone=timezone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/weekly-availability/")
def create_weekly_availability(
    user_id: int,
    day_of_week: str,
    start_time: str,
    end_time: str,
    db: Session = Depends(get_db)
):
    availability = WeeklyAvailability(
        user_id=user_id,
        day_of_week=day_of_week,
        start_time=datetime.strptime(start_time, "%H:%M").time(),
        end_time=datetime.strptime(end_time, "%H:%M").time()
    )
    db.add(availability)
    db.commit()
    db.refresh(availability)
    return availability





@app.get("/users/", response_model=List[Dict[str, str]])
def get_users(user_id: int = None, db: Session = Depends(get_db)):
    if user_id:
        # Fetch a specific user by ID
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return [{"id": str(user.id), "name": user.name, "timezone": user.timezone}]
    else:
        # Fetch all users
        users = db.query(User).all()
        return [{"id": str(user.id), "name": user.name, "timezone": user.timezone} for user in users]
