import random
from datetime import date


def unique_room_name() -> str:
    return f"AQA{random.randint(1000, 9999)}"


def build_room(**overrides) -> dict:
    room = {
        "roomName": unique_room_name(),
        "type": "Double",
        "accessible": True,
        "description": "Automated test room with a nice view and a comfortable bed.",
        "image": "https://www.mwtestconsultancy.co.uk/img/room1.jpg",
        "roomPrice": 150,
        "features": ["WiFi", "Safe"],
    }
    room.update(overrides)
    return room


BOOKING_DEFAULTS = {
    "firstname": "John",
    "lastname": "Tester",
    "email": "john.tester@example.com",
    "phone": "01234567890",
}


def next_month_range(start_day: int = 20, nights: int = 2) -> dict:
    """Date range inside NEXT calendar month (always in the future)."""
    today = date.today()
    year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    start = date(year, month, start_day)
    end = date.fromordinal(start.toordinal() + nights)
    return {"checkin": start.isoformat(), "checkout": end.isoformat()}


def build_booking(room_id: int, dates: dict, **overrides) -> dict:
    booking = {
        "roomid": room_id,
        **BOOKING_DEFAULTS,
        "depositpaid": False,
        "bookingdates": dates,
    }
    booking.update(overrides)
    return booking
