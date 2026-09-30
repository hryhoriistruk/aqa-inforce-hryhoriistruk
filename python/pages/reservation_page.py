from playwright.sync_api import Page, expect


class ReservationPage:
    def __init__(self, page: Page):
        self.page = page
        self.reserve_button = page.locator("#doReservation")
        self.submit_button = page.locator('button:has-text("Reserve Now"):not(#doReservation)')
        self.firstname_input = page.locator('input[name="firstname"]')
        self.lastname_input = page.locator('input[name="lastname"]')
        self.email_input = page.locator('input[name="email"]')
        self.phone_input = page.locator('input[name="phone"]')
        self.booking_confirmed = page.locator("h2", has_text="Booking Confirmed")
        self.alert_danger = page.locator(".alert.alert-danger")
        self.next_month_button = page.locator(".rbc-toolbar button", has_text="Next")
        self.calendar_event = page.locator(".rbc-month-view .rbc-event")

    def visit(self, room_id: int, dates: dict):
        query = f"checkin={dates['checkin']}&checkout={dates['checkout']}"
        self.page.goto(f"/reservation/{room_id}?{query}")
        self.reserve_button.wait_for(state="visible")
        return self

    def open_booking_form(self):
        self.reserve_button.click()
        self.firstname_input.wait_for(state="visible")
        return self

    def fill_form(self, data: dict):
        fields = {
            "firstname": self.firstname_input,
            "lastname": self.lastname_input,
            "email": self.email_input,
            "phone": self.phone_input,
        }
        for name, locator in fields.items():
            locator.fill(data.get(name, ""))
        return self

    def submit(self):
        self.submit_button.click()
        return self

    def assert_booking_confirmed(self, dates: dict):
        self.booking_confirmed.wait_for(state="visible")
        period = f"{dates['checkin']} - {dates['checkout']}"
        self.page.locator("strong", has_text=period).wait_for(state="visible")
        return self

    def assert_validation_error(self, error_pattern):
        expect(self.alert_danger).to_be_visible()
        expect(self.alert_danger.locator("li").first).to_be_visible()
        expect(self.alert_danger).to_contain_text(error_pattern)
        expect(self.page.get_by_text("Booking Confirmed")).to_have_count(0)
        expect(self.firstname_input).to_be_visible()
        return self

    def go_to_next_month(self):
        self.next_month_button.click()
        return self

    def assert_calendar_has_event(self, text: str, timeout: int = 5000):
        self.calendar_event.filter(has_text=text).first.wait_for(state="visible", timeout=timeout)
        return self
