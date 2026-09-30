import { buildRoom, buildBooking, nextMonthRange } from '../support/utils';

const AUTH_ERRORS = [401, 403];

describe('API – Admin & User flows for rooms', () => {
  let roomBase;
  let bookingBase;
  const createdRoomIds = [];

  before(() => {
    cy.fixture('room').then((r) => (roomBase = r));
    cy.fixture('booking').then((b) => (bookingBase = b));
  });

  afterEach(() => {
    createdRoomIds.splice(0).forEach((id) => cy.adminDeleteRoom(id));
  });

  it('TC-API-01: creates a room via Admin API and sees it via User API', () => {
    const room = buildRoom(roomBase);
    cy.adminCreateRoom(room).then((created) => {
      createdRoomIds.push(created.roomid);
      cy.userGetRooms().then((rooms) => {
        const found = rooms.find((r) => r.roomid === created.roomid);
        expect(found).to.include({
          roomName: room.roomName,
          type: room.type,
          accessible: room.accessible,
          roomPrice: room.roomPrice,
          description: room.description,
        });
        expect(found.features).to.have.members(room.features);
      });
    });
  });

  it('TC-API-02: books a room via User API and sees the booking via Admin API', () => {
    cy.adminCreateRoom(buildRoom(roomBase)).then((room) => {
      createdRoomIds.push(room.roomid);
      const dates = nextMonthRange(10, 2);

      cy.userBookRoom(buildBooking(bookingBase, room.roomid, dates)).then((res) => {
        expect(res.status).to.eq(201);
      });

      cy.adminGetBookings(room.roomid).then((bookings) => {
        expect(bookings).to.have.length(1);
        expect(bookings[0]).to.include({
          firstname: bookingBase.firstname,
          lastname: bookingBase.lastname,
        });
        expect(bookings[0].bookingdates.checkin).to.eq(dates.checkin);
        expect(bookings[0].bookingdates.checkout).to.eq(dates.checkout);
      });

      cy.userGetRoomReport(room.roomid).then((report) => {
        expect(report).to.have.length(1);
        expect(report[0]).to.include({
          title: 'Unavailable',
          start: dates.checkin,
          end: dates.checkout,
        });
      });
    });
  });

  it('TC-API-03: edits a room via Admin API and sees changes via User API', () => {
    cy.adminCreateRoom(buildRoom(roomBase)).then((room) => {
      createdRoomIds.push(room.roomid);
      const updated = {
        ...roomBase,
        roomName: room.roomName,
        type: 'Suite',
        roomPrice: 275,
        accessible: false,
        description: 'Updated description of the automated test room, long enough.',
        features: ['Views', 'TV'],
      };

      cy.adminUpdateRoom(room.roomid, updated).then((res) => {
        expect([200, 202]).to.include(res.status);
      });

      cy.userGetRooms().then((rooms) => {
        const found = rooms.find((r) => r.roomid === room.roomid);
        expect(found).to.include({ type: 'Suite', roomPrice: 275, accessible: false });
        expect(found.description).to.eq(updated.description);
        expect(found.features).to.have.members(['Views', 'TV']);
      });
    });
  });

  it('TC-API-04: deletes a room via Admin API and it disappears for the User API', () => {
    cy.adminCreateRoom(buildRoom(roomBase)).then((room) => {
      cy.adminDeleteRoom(room.roomid).then((res) => {
        expect([200, 202, 204]).to.include(res.status);
      });

      cy.userGetRooms().then((rooms) => {
        expect(rooms.map((r) => r.roomid)).to.not.include(room.roomid);
      });
    });
  });

  it('TC-API-05: rejects room create / edit / delete without authorisation', () => {
    cy.adminCreateRoom(buildRoom(roomBase)).then((room) => {
      createdRoomIds.push(room.roomid);
      cy.clearCookies();

      const call = (method, url, body) =>
        cy.request({
          method,
          url: `${Cypress.env('apiUrl')}${url}`,
          body,
          failOnStatusCode: false,
        });

      call('POST', '/room', buildRoom(roomBase)).then((res) => {
        expect(AUTH_ERRORS).to.include(res.status);
      });
      call('PUT', `/room/${room.roomid}`, {
        ...roomBase,
        roomid: room.roomid,
        roomName: room.roomName,
        roomPrice: 999,
      }).then((res) => {
        expect(AUTH_ERRORS).to.include(res.status);
      });
      call('DELETE', `/room/${room.roomid}`).then((res) => {
        expect(AUTH_ERRORS).to.include(res.status);
      });


      cy.userGetRooms().then((rooms) => {
        const found = rooms.find((r) => r.roomid === room.roomid);
        expect(found, 'room still exists').to.exist;
        expect(found.roomPrice).to.eq(roomBase.roomPrice);
      });
    });
  });

  it('TC-API-06: rejects bookings with invalid data', () => {
    cy.adminCreateRoom(buildRoom(roomBase)).then((room) => {
      createdRoomIds.push(room.roomid);
      const dates = nextMonthRange(5, 2);

      const invalid = [
        { overrides: { email: 'invalid' }, status: [400] },
        { overrides: { firstname: 'Jo' }, status: [400] },
        { overrides: { lastname: '' }, status: [400] },
        { overrides: { phone: '123' }, status: [400] },
        { overrides: { bookingdates: undefined }, status: [400, 409, 500] },
      ];

      cy.wrap(invalid).each(({ overrides, status }) => {
        const body = buildBooking(bookingBase, room.roomid, dates, overrides);
        cy.userBookRoom(body, { timeout: 90000 }).then((res) => {
          expect(status, JSON.stringify(overrides)).to.include(res.status);
        });
      });

      cy.adminGetBookings(room.roomid).should('have.length', 0);
    });
  });

  it('TC-API-08: the same dates cannot be booked twice', () => {
    cy.adminCreateRoom(buildRoom(roomBase)).then((room) => {
      createdRoomIds.push(room.roomid);
      const dates = nextMonthRange(14, 3);
      const overlapping = nextMonthRange(15, 3);

      cy.userBookRoom(buildBooking(bookingBase, room.roomid, dates))
        .its('status')
        .should('eq', 201);
      cy.userBookRoom(buildBooking(bookingBase, room.roomid, dates))
        .its('status')
        .should('eq', 409);
      cy.userBookRoom(buildBooking(bookingBase, room.roomid, overlapping))
        .its('status')
        .should('eq', 409);

      cy.adminGetBookings(room.roomid).should('have.length', 1);
    });
  });

  it('TC-API-09: rejects wrong credentials and anonymous access', () => {
    cy.clearCookies();
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/login`,
      body: { username: Cypress.env('adminUser'), password: 'definitely-wrong' },
      failOnStatusCode: false,
    }).then((res) => {
      expect(AUTH_ERRORS).to.include(res.status);
    });

    cy.clearCookies();
    cy.request({
      url: `${Cypress.env('apiUrl')}/booking?roomid=123`,
      failOnStatusCode: false,
    }).then((res) => {
      expect(AUTH_ERRORS).to.include(res.status);
    });
  });
});

describe('UI ↔ API consistency (cy.intercept)', () => {
  let room;

  before(() => {
    cy.fixture('room').then((base) =>
      cy.adminCreateRoom(buildRoom(base)).then((r) => (room = r))
    );
  });

  after(() => {
    if (room) cy.adminDeleteRoom(room.roomid);
  });

  it('TC-API-07: home page loads rooms from GET /api/room', () => {
    cy.intercept('GET', '**/api/room').as('getRooms');
    cy.visit('/');
    cy.wait('@getRooms').then(({ response }) => {
      expect(response.statusCode).to.eq(200);
      expect(response.body.rooms).to.be.an('array').and.not.be.empty;
      expect(response.body.rooms.map((r) => r.roomid)).to.include(room.roomid);
    });
  });
});
