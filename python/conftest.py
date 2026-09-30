import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

from helpers import build_room

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

DEFAULT_TIMEOUT = 90

BASE_URL = os.getenv("BASE_URL", "https://automationintesting.online")
API_URL = os.getenv("API_URL", f"{BASE_URL}/api")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")


class TimeoutSession(requests.Session):
    """requests.Session that never waits forever for an answer."""

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        return super().request(*args, **kwargs)


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_url():
    return API_URL


@pytest.fixture()
def admin_api(api_url):
    """requests.Session authorised as admin (token is stored in Cookie header)."""
    s = TimeoutSession()
    r = s.post(f"{api_url}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    if token:
        s.headers.update({"Cookie": f"token={token}"})
    return s


@pytest.fixture()
def user_api():
    """requests.Session WITHOUT any credentials – behaves like a site visitor."""
    return TimeoutSession()


def _find_room(user_api, api_url, name):
    rooms = user_api.get(f"{api_url}/room").json()["rooms"]
    return next((r for r in rooms if r["roomName"] == name), None)


def _purge_bookings(admin_api, api_url, room_id):
    """Deletes every booking of the room.

    On the shared demo site bookings survive the deletion of their room and a new room can get
    an id that was used before, so leftovers of another test may show up for "our" room.
    """
    r = admin_api.get(f"{api_url}/booking", params={"roomid": room_id})
    if r.status_code != 200:
        return
    for booking in r.json().get("bookings", []):
        admin_api.delete(f"{api_url}/booking/{booking['bookingid']}")


@pytest.fixture()
def room(admin_api, user_api, api_url):
    """Creates a unique room via Admin API and deletes it (with its bookings) after the test."""
    payload = build_room()
    r = admin_api.post(f"{api_url}/room", json=payload)
    assert r.status_code in (200, 201), r.text
    created = _find_room(user_api, api_url, payload["roomName"])
    assert created, "created room not found in GET /api/room"
    _purge_bookings(admin_api, api_url, created["roomid"])
    yield created
    _purge_bookings(admin_api, api_url, created["roomid"])
    admin_api.delete(f"{api_url}/room/{created['roomid']}")
