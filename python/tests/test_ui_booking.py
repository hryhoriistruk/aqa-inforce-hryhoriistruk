import re

import pytest
from playwright.sync_api import Page, expect

from helpers import BOOKING_DEFAULTS, build_booking, next_month_range
from pages.home_page import HomePage
from pages.reservation_page import ReservationPage


def admin_bookings(admin_api, api_url, room: dict) -> list:
    r = admin_api.get(f"{api_url}/booking", params={"roomid": room["roomid"]})
    assert r.status_code == 200, r.text
    return r.json()["bookings"]


@pytest.mark.ui
def test_room_can_be_booked_with_valid_data(page: Page, room, admin_api, api_url):
    dates = next_month_range(10, 3)
    reservation_page = ReservationPage(page)
    before = admin_bookings(admin_api, api_url, room)

    with page.expect_response(
        lambda r: r.url.endswith("/api/booking") and r.request.method == "POST"
    ) as resp:
        (
            reservation_page.visit(room["roomid"], dates)
            .open_booking_form()
            .fill_form(BOOKING_DEFAULTS)
            .submit()
        )

    response = resp.value
    assert response.status == 201
    body = response.request.post_data_json
    assert body["roomid"] == room["roomid"]
    assert body["firstname"] == BOOKING_DEFAULTS["firstname"]
    assert body["lastname"] == BOOKING_DEFAULTS["lastname"]
    assert body["email"] == BOOKING_DEFAULTS["email"]
    assert body["phone"] == BOOKING_DEFAULTS["phone"]
    assert body["bookingdates"] == dates

    reservation_page.assert_booking_confirmed(dates)

    bookings = admin_bookings(admin_api, api_url, room)
    assert len(bookings) == len(before) + 1
    ours = [b for b in bookings if b["bookingdates"] == dates]
    assert len(ours) == 1
    assert ours[0]["firstname"] == BOOKING_DEFAULTS["firstname"]


INVALID_CASES = [
    pytest.param(
        {"firstname": "", "lastname": "", "email": "", "phone": ""},
        re.compile(r".+"),
        id="TC-UI-02-all-empty",
    ),
    pytest.param(
        {"firstname": "Jo"},
        re.compile(r"size must be between 3 and 18", re.I),
        id="TC-UI-03-firstname-too-short",
    ),
    pytest.param(
        {"email": "not-an-email"},
        re.compile(r"email", re.I),
        id="TC-UI-04-invalid-email",
    ),
    pytest.param(
        {"phone": "123"},
        re.compile(r"size must be between 11 and 21", re.I),
        id="TC-UI-05-phone-too-short",
    ),
    pytest.param(
        {"lastname": ""},
        re.compile(r"lastname|size must be between 3 and 30", re.I),
        id="TC-UI-06-lastname-empty",
    ),
    pytest.param(
        {"email": "userexample.com"},
        re.compile(r"email", re.I),
        id="TC-UI-11-email-without-at",
    ),
    pytest.param(
        {"email": "user@"},
        re.compile(r"email", re.I),
        id="TC-UI-12-email-without-domain",
    ),
    pytest.param(
        {"phone": "0123456789012345678901"},
        re.compile(r"size must be between 11 and 21", re.I),
        id="TC-UI-13-phone-too-long",
    ),
    pytest.param(
        {"firstname": "JohnDoeSmithJonesAb"},
        re.compile(r"size must be between 3 and 18", re.I),
        id="TC-UI-14-firstname-too-long",
    ),
    pytest.param(
        {"lastname": "TesterSmithJonesBrownWhiteBlack"},
        re.compile(r"size must be between 3 and 30", re.I),
        id="TC-UI-15-lastname-too-long",
    ),
]


@pytest.mark.ui
@pytest.mark.parametrize("broken, error", INVALID_CASES)
def test_room_cannot_be_booked_with_invalid_data(
    page: Page, room, admin_api, api_url, broken, error
):
    dates = next_month_range(12, 2)
    reservation_page = ReservationPage(page)
    before = admin_bookings(admin_api, api_url, room)

    with page.expect_response(
        lambda r: r.url.endswith("/api/booking") and r.request.method == "POST"
    ) as resp:
        (
            reservation_page.visit(room["roomid"], dates)
            .open_booking_form()
            .fill_form({**BOOKING_DEFAULTS, **broken})
            .submit()
        )

    response = resp.value
    assert response.status == 400
    assert response.json()["errors"], "the API must return a list of validation errors"

    reservation_page.assert_validation_error(error)

    assert admin_bookings(admin_api, api_url, room) == before


@pytest.mark.ui
def test_room_cannot_be_booked_without_dates(page: Page, room, admin_api, api_url):
    before = admin_bookings(admin_api, api_url, room)
    page.goto(f"/reservation/{room['roomid']}")
    expect(page.locator("h1", has_text=f"{room['type']} Room")).to_be_visible()

    expect(page.locator(".booking-card .spinner-border")).to_be_visible()
    expect(page.locator("#doReservation")).to_have_count(0)
    expect(page.locator('input[name="firstname"]')).to_have_count(0)
    expect(page.get_by_text("Booking Confirmed")).to_have_count(0)

    assert admin_bookings(admin_api, api_url, room) == before


@pytest.mark.ui
def test_calendar_feed_reports_earlier_booked_dates_as_unavailable(
    page: Page, room, user_api, api_url
):
    booked = next_month_range(20, 2)
    r = user_api.post(f"{api_url}/booking", json=build_booking(room["roomid"], booked))
    assert r.status_code == 201, r.text

    other = next_month_range(5, 2)
    with page.expect_response(lambda x: "/api/report/room/" in x.url) as resp:
        query = f"checkin={other['checkin']}&checkout={other['checkout']}"
        page.goto(f"/reservation/{room['roomid']}?{query}")
    assert resp.value.status == 200
    body = resp.value.json()
    entries = body["report"] if isinstance(body, dict) else body
    assert len(entries) == 1
    assert entries[0]["title"] == "Unavailable"
    assert entries[0]["start"] == booked["checkin"]
    assert entries[0]["end"] == booked["checkout"]

    expect(page.locator("#doReservation")).to_be_visible()
    page.locator(".rbc-toolbar button", has_text="Next").click()
    expect(page.locator(".rbc-month-view .rbc-event", has_text="Selected")).to_be_visible()


@pytest.mark.ui
@pytest.mark.xfail(reason="BUG-03: calendar does not draw earlier booked dates", strict=False)
def test_calendar_shows_earlier_booked_dates_as_unavailable(page: Page, room, user_api, api_url):
    booked = next_month_range(20, 2)
    r = user_api.post(f"{api_url}/booking", json=build_booking(room["roomid"], booked))
    assert r.status_code == 201, r.text

    reservation_page = ReservationPage(page).visit(room["roomid"], next_month_range(5, 2))
    reservation_page.go_to_next_month()
    reservation_page.assert_calendar_has_event("Unavailable")


@pytest.mark.ui
def test_earlier_booked_dates_cannot_be_booked_again(
    page: Page, room, admin_api, user_api, api_url
):
    dates = next_month_range(20, 2)
    r = user_api.post(f"{api_url}/booking", json=build_booking(room["roomid"], dates))
    assert r.status_code == 201, r.text
    before = admin_bookings(admin_api, api_url, room)

    reservation_page = ReservationPage(page)
    with page.expect_response(
        lambda x: x.url.endswith("/api/booking") and x.request.method == "POST"
    ) as resp:
        (
            reservation_page.visit(room["roomid"], dates)
            .open_booking_form()
            .fill_form(BOOKING_DEFAULTS)
            .submit()
        )

    assert resp.value.status == 409
    expect(page.get_by_text("Booking Confirmed")).to_have_count(0)
    assert admin_bookings(admin_api, api_url, room) == before


@pytest.mark.ui
def test_book_now_on_home_page_opens_reservation_with_dates(page: Page):
    home_page = HomePage(page)

    with page.expect_response(
        lambda r: r.url.endswith("/api/room") and r.request.method == "GET"
    ) as resp:
        home_page.visit()
    assert resp.value.status == 200

    home_page.assert_book_now_link_has_dates()
    home_page.click_book_now()

    expect(page).to_have_url(re.compile(r"/reservation/\d+"))
    expect(page.locator("#doReservation")).to_be_visible()
