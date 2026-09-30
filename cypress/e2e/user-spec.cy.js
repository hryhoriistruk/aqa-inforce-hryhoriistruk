import { buildRoom, buildBooking, nextMonthRange } from '../support/utils';

const BOOK_NOW_HREF = /^\/reservation\/\d+\?checkin=\d{4}-\d{2}-\d{2}&checkout=\d{4}-\d{2}-\d{2}$/;

describe('User UI – room booking', () => {
  let room;
  let bookingData;

  before(() => {
    cy.fixture('booking').then((b) => (bookingData = b));
  });

  beforeEach(() => {
    cy.fixture('room').then((base) =>
      cy.adminCreateRoom(buildRoom(base)).then((r) => (room = r))
    );
    cy.intercept('POST', '**/api/booking').as('createBooking');
  });

  afterEach(() => {
    if (room) cy.adminDeleteRoom(room.roomid);
  });

  it('TC-UI-01: books a room with valid data', () => {
    const dates = nextMonthRange(10, 3);
    cy.visitReservation(room.roomid, dates);
    cy.openBookingForm();
    cy.fillBookingForm(bookingData);
    cy.submitBooking();

    cy.wait('@createBooking').then(({ request, response }) => {
      expect(response.statusCode).to.eq(201);
      expect(request.body).to.include({
        firstname: bookingData.firstname,
        lastname: bookingData.lastname,
        email: bookingData.email,
        phone: bookingData.phone,
      });
      expect(Number(request.body.roomid)).to.eq(room.roomid);
      expect(request.body.bookingdates).to.deep.equal(dates);
    });
    cy.contains('h2', 'Booking Confirmed').should('be.visible');
    cy.contains('strong', `${dates.checkin} - ${dates.checkout}`).should('be.visible');

    cy.adminGetBookings(room.roomid).then((bookings) => {
      const ours = bookings.filter((b) => b.bookingdates.checkin === dates.checkin);
      expect(ours).to.have.length(1);
      expect(ours[0].bookingdates.checkout).to.eq(dates.checkout);
      expect(ours[0].firstname).to.eq(bookingData.firstname);
      expect(ours[0].lastname).to.eq(bookingData.lastname);
    });
  });

  const invalidCases = [
    {
      id: 'TC-UI-02',
      title: 'all fields empty',
      data: { firstname: '', lastname: '', email: '', phone: '' },
      error: /.+/,
    },
    {
      id: 'TC-UI-03',
      title: 'firstname too short',
      data: { firstname: 'Jo' },
      error: /size must be between 3 and 18/i,
    },
    {
      id: 'TC-UI-04',
      title: 'invalid email format',
      data: { email: 'not-an-email' },
      error: /email/i,
    },
    {
      id: 'TC-UI-05',
      title: 'phone too short',
      data: { phone: '123' },
      error: /size must be between 11 and 21/i,
    },
    {
      id: 'TC-UI-06',
      title: 'lastname empty',
      data: { lastname: '' },
      error: /lastname|size must be between 3 and 30/i,
    },
    {
      id: 'TC-UI-11',
      title: 'email without @',
      data: { email: 'userexample.com' },
      error: /email/i,
    },
    {
      id: 'TC-UI-12',
      title: 'email without domain',
      data: { email: 'user@' },
      error: /email/i,
    },
    {
      id: 'TC-UI-13',
      title: 'phone too long (22 chars)',
      data: { phone: '0123456789012345678901' },
      error: /size must be between 11 and 21/i,
    },
    {
      id: 'TC-UI-14',
      title: 'firstname too long (19 chars)',
      data: { firstname: 'JohnDoeSmithJonesAb' },
      error: /size must be between 3 and 18/i,
    },
    {
      id: 'TC-UI-15',
      title: 'lastname too long (31 chars)',
      data: { lastname: 'TesterSmithJonesBrownWhiteBlack' },
      error: /size must be between 3 and 30/i,
    },
  ];

  invalidCases.forEach(({ id, title, data, error }) => {
    it(`${id}: does not book a room – ${title}`, () => {
      const dates = nextMonthRange(12, 2);
      cy.visitReservation(room.roomid, dates);
      cy.adminGetBookings(room.roomid).then((before) => {
        cy.openBookingForm();
        cy.fillBookingForm({ ...bookingData, ...data });
        cy.submitBooking();

        cy.wait('@createBooking').then(({ response }) => {
          expect(response.statusCode).to.eq(400);
          expect(response.body.errors, 'validation errors').to.be.an('array').and.not.be.empty;
        });
        cy.get('.alert.alert-danger').should('be.visible').invoke('text').should('match', error);
        cy.get('.alert.alert-danger li').should('have.length.greaterThan', 0);
        cy.get('input[name="firstname"]').should('be.visible');
        cy.contains('Booking Confirmed').should('not.exist');

        cy.adminGetBookings(room.roomid).should('deep.equal', before);
      });
    });
  });

  it('TC-UI-07: booking form cannot be reached without selecting dates', () => {
    cy.visit(`/reservation/${room.roomid}`);
    cy.contains('h1', `${room.type} Room`).should('be.visible');
    cy.get('.booking-card .spinner-border').should('be.visible');
    cy.get('#doReservation').should('not.exist');
    cy.get('input[name="firstname"]').should('not.exist');
    cy.contains('Booking Confirmed').should('not.exist');
    cy.adminGetBookings(room.roomid).should('have.length', 0);
  });

  it('TC-UI-08: calendar feed reports earlier booked dates as Unavailable', () => {
    const booked = nextMonthRange(20, 2);
    const other = nextMonthRange(5, 2);
    cy.userBookRoom(buildBooking(bookingData, room.roomid, booked))
      .its('status')
      .should('eq', 201);

    cy.intercept('GET', `**/api/report/room/${room.roomid}`).as('getReport');
    cy.visitReservation(room.roomid, other);
    cy.wait('@getReport').then(({ response }) => {
      expect(response.statusCode).to.eq(200);
      const body = response.body;
      const entries = Array.isArray(body) ? body : body.report;
      expect(entries).to.have.length(1);
      expect(entries[0]).to.include({
        title: 'Unavailable',
        start: booked.checkin,
        end: booked.checkout,
      });
    });

    cy.contains('.rbc-toolbar button', 'Next').click();
    cy.get('.rbc-month-view .rbc-event').should('contain.text', 'Selected');
  });

  const knownBug = Cypress.env('RUN_KNOWN_BUGS') ? it : it.skip;
  knownBug('TC-UI-08: calendar draws earlier booked dates as Unavailable (BUG-03)', () => {
    cy.userBookRoom(buildBooking(bookingData, room.roomid, nextMonthRange(20, 2)))
      .its('status')
      .should('eq', 201);

    cy.visitReservation(room.roomid, nextMonthRange(5, 2));
    cy.contains('.rbc-toolbar button', 'Next').click();
    cy.get('.rbc-month-view .rbc-event').should('contain.text', 'Unavailable');
  });

  it('TC-UI-08: earlier booked dates cannot be booked again through the UI', () => {
    cy.on('uncaught:exception', () => false);

    const dates = nextMonthRange(20, 2);
    cy.userBookRoom(buildBooking(bookingData, room.roomid, dates)).its('status').should('eq', 201);

    cy.visitReservation(room.roomid, dates);
    cy.openBookingForm();
    cy.fillBookingForm(bookingData);
    cy.submitBooking();

    cy.wait('@createBooking').its('response.statusCode').should('eq', 409);
    cy.contains('Booking Confirmed').should('not.exist');
    cy.adminGetBookings(room.roomid).should('have.length', 1);
  });

  it('TC-UI-10: "Book now" on the home page opens the reservation page', () => {
    cy.intercept('GET', '**/api/room').as('getRooms');
    cy.visit('/');
    cy.wait('@getRooms').its('response.statusCode').should('eq', 200);

    const bookNow = "a.btn[href^='/reservation/']";
    cy.contains(bookNow, 'Book now').should('have.attr', 'href').and('match', BOOK_NOW_HREF);
    cy.contains(bookNow, 'Book now').click();
    cy.location('pathname').should('match', /^\/reservation\/\d+$/);
    cy.get('#doReservation').should('be.visible');
  });
});
