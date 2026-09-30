import pytest

from helpers import build_booking, build_room, next_month_range

pytestmark = pytest.mark.api

AUTH_ERRORS = (401, 403)


def get_rooms(user_api, api_url):
    r = user_api.get(f"{api_url}/room")
    assert r.status_code == 200
    return r.json()["rooms"]


def find_room(user_api, api_url, room_id):
    return next((r for r in get_rooms(user_api, api_url) if r["roomid"] == room_id), None)


def admin_bookings(admin_api, api_url, room_id):
    r = admin_api.get(f"{api_url}/booking", params={"roomid": room_id})
    assert r.status_code == 200, r.text
    return r.json()["bookings"]


def test_create_room_admin_visible_for_user(room, user_api, api_url):
    found = find_room(user_api, api_url, room["roomid"])
    assert found is not None
    assert found["roomName"] == room["roomName"]
    assert found["type"] == "Double"
    assert found["accessible"] is True
    assert found["roomPrice"] == 150
    assert found["description"] == room["description"]
    assert sorted(found["features"]) == ["Safe", "WiFi"]


def test_book_room_user_visible_for_admin(room, admin_api, user_api, api_url):
    dates = next_month_range(10, 2)
    r = user_api.post(f"{api_url}/booking", json=build_booking(room["roomid"], dates))
    assert r.status_code == 201, r.text

    bookings = admin_bookings(admin_api, api_url, room["roomid"])
    assert len(bookings) == 1
    assert bookings[0]["firstname"] == "John"
    assert bookings[0]["lastname"] == "Tester"
    assert bookings[0]["bookingdates"] == dates

    report = user_api.get(f"{api_url}/report/room/{room['roomid']}")
    assert report.status_code == 200
    body = report.json()
    entries = body["report"] if isinstance(body, dict) else body
    assert len(entries) == 1
    assert entries[0]["title"] == "Unavailable"
    assert entries[0]["start"] == dates["checkin"]
    assert entries[0]["end"] == dates["checkout"]


def test_edit_room_admin_visible_for_user(room, admin_api, user_api, api_url):
    updated = build_room(
        roomName=room["roomName"],
        type="Suite",
        roomPrice=275,
        accessible=False,
        description="Updated description of the automated test room, long enough.",
        features=["Views", "TV"],
    )
    r = admin_api.put(
        f"{api_url}/room/{room['roomid']}", json={"roomid": room["roomid"], **updated}
    )
    assert r.status_code in (200, 202), r.text

    found = find_room(user_api, api_url, room["roomid"])
    assert found["type"] == "Suite"
    assert found["roomPrice"] == 275
    assert found["accessible"] is False
    assert found["description"] == updated["description"]
    assert sorted(found["features"]) == ["TV", "Views"]


def test_delete_room_admin_removed_for_user(room, admin_api, user_api, api_url):
    r = admin_api.delete(f"{api_url}/room/{room['roomid']}")
    assert r.status_code in (200, 202, 204)

    assert find_room(user_api, api_url, room["roomid"]) is None


def test_room_create_edit_delete_without_auth_is_rejected(room, user_api, api_url):
    room_id = room["roomid"]

    r = user_api.post(f"{api_url}/room", json=build_room())
    assert r.status_code in AUTH_ERRORS

    changed = build_room(roomName=room["roomName"], roomPrice=999)
    r = user_api.put(f"{api_url}/room/{room_id}", json={"roomid": room_id, **changed})
    assert r.status_code in AUTH_ERRORS

    r = user_api.delete(f"{api_url}/room/{room_id}")
    assert r.status_code in AUTH_ERRORS

    found = find_room(user_api, api_url, room_id)
    assert found is not None
    assert found["roomPrice"] == 150


INVALID_BOOKINGS = [
    pytest.param({"email": "invalid"}, (400,), id="invalid-email"),
    pytest.param({"firstname": "Jo"}, (400,), id="firstname-too-short"),
    pytest.param({"lastname": ""}, (400,), id="lastname-empty"),
    pytest.param({"phone": "123"}, (400,), id="phone-too-short"),
    pytest.param({"bookingdates": None}, (400, 409, 500), id="no-dates"),
]


@pytest.mark.parametrize("overrides, expected", INVALID_BOOKINGS)
def test_booking_with_invalid_data_is_rejected(
    room, admin_api, user_api, api_url, overrides, expected
):
    dates = next_month_range(5, 2)
    body = build_booking(room["roomid"], dates, **overrides)
    if overrides.get("bookingdates", True) is None:
        body.pop("bookingdates")
    r = user_api.post(f"{api_url}/booking", json=body)
    assert r.status_code in expected, r.text
    if r.status_code in (400, 500):
        assert r.json()["errors"], "the API must return a list of errors"

    assert admin_bookings(admin_api, api_url, room["roomid"]) == []


def test_home_page_loads_rooms_from_api(room, user_api, api_url):
    r = user_api.get(f"{api_url}/room")
    assert r.status_code == 200
    assert r.json()["rooms"]
    assert room["roomid"] in [x["roomid"] for x in r.json()["rooms"]]


def test_same_dates_cannot_be_booked_twice(room, admin_api, user_api, api_url):
    dates = next_month_range(14, 3)

    r = user_api.post(f"{api_url}/booking", json=build_booking(room["roomid"], dates))
    assert r.status_code == 201

    r = user_api.post(f"{api_url}/booking", json=build_booking(room["roomid"], dates))
    assert r.status_code == 409

    overlapping = next_month_range(15, 3)
    r = user_api.post(f"{api_url}/booking", json=build_booking(room["roomid"], overlapping))
    assert r.status_code == 409

    assert len(admin_bookings(admin_api, api_url, room["roomid"])) == 1


def test_wrong_credentials_and_anonymous_access_are_rejected(room, user_api, api_url):
    r = user_api.post(
        f"{api_url}/auth/login",
        json={"username": "admin", "password": "definitely-wrong"},
    )
    assert r.status_code in AUTH_ERRORS

    r = user_api.get(f"{api_url}/booking", params={"roomid": room["roomid"]})
    assert r.status_code in AUTH_ERRORS
