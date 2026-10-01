# aqa-inforce-hryhoriistruk

[![Python CI](https://github.com/hryhoriistruk/aqa-inforce-hryhoriistruk/actions/workflows/python-ci.yml/badge.svg)](https://github.com/hryhoriistruk/aqa-inforce-hryhoriistruk/actions/workflows/python-ci.yml)
[![Cypress CI](https://github.com/hryhoriistruk/aqa-inforce-hryhoriistruk/actions/workflows/cypress-ci.yml/badge.svg)](https://github.com/hryhoriistruk/aqa-inforce-hryhoriistruk/actions/workflows/cypress-ci.yml)

Automated tests for <https://automationintesting.online/> (Restful-booker platform):
UI tests for the User App (room booking) and API tests for the Admin / User flows.

The same test cases (`test-cases.txt`) are automated twice:

| Framework | Folder | Run from |
|---|---|---|
| **Cypress** (JavaScript) | `cypress` | repository root |
| **Playwright + pytest** (Python) | `python` | `python` |

## Test cases (where to find them)

| What | File | Location |
|---|---|---|
| Manual test cases (UI + API), defects and observations | `test-cases.txt` | repository root |
| UI automation - Cypress (TC-UI-01…08, TC-UI-10…15) | `user-spec.cy.js` | `cypress/e2e` |
| API automation - Cypress (TC-API-01…09) | `admin-spec.cy.js` | `cypress/e2e` |
| UI automation - Playwright (TC-UI-01…08, TC-UI-10…15) | `test_ui_booking.py` | `python/tests` |
| API automation - pytest (TC-API-01…09) | `test_api_rooms.py` | `python/tests` |

Manual only: TC-UI-09 (calendar mouse-drag; the same booking flow is automated in TC-UI-01).
Known application defects are described in `test-cases.txt` (BUG-01…03 and OBS-01…06).

TC-UI-08 ("earlier booked dates show as Unavailable") is automated in three checks: the calendar
data feed, the "cannot be booked again" behaviour, and the calendar drawing itself. The drawing
fails because of BUG-03 (the calendar does not draw earlier booked days), so that check is a
**known-bug test**: `xfail` in pytest (XPASS once the application is fixed) and pending in
Cypress (run it with `CYPRESS_RUN_KNOWN_BUGS=true npm run test:ui`).

`cy.intercept` (Cypress) and `page.expect_response` (Playwright) are used to check the
requests behind the UI (booking POST, room list, calendar feed).

---

## Cypress

Requirements: Node.js 18+.

```bash
git clone https://github.com/hryhoriistruk/aqa-inforce-hryhoriistruk.git
cd aqa-inforce-hryhoriistruk
npm ci
```

```bash
npm test               
npm run test:ui        
npm run test:api       
npm run test:headed    
npm run cy:open        
CYPRESS_RUN_KNOWN_BUGS=true npm run test:ui   
```

Base URL and admin credentials are set in `cypress.config.js` and can be overridden, e.g.
`CYPRESS_BASE_URL=... CYPRESS_apiUrl=... npm test`.

## Python (Playwright + pytest)

Requirements: Python 3.9+ (CI runs the suite on 3.9, 3.10, 3.11 and 3.12).

```bash
cd python
source .venv/bin/activate        
pip install -r requirements.txt
playwright install chromium
cp .env.example .env             
```

```bash
pytest                                                    
pytest -m ui                                              
pytest -m api                                             
pytest --headed                                           
pytest -n auto                                            
pytest --html=reports/report.html --self-contained-html   
pytest --alluredir=allure-results && allure serve allure-results   
```

Flaky tests are retried automatically (`--reruns 2` via `pytest-rerunfailures`), which is
useful on the shared demo site.

Code quality (run inside `python`): `flake8 .`, `black --check .`, `isort --check-only .`

## Repository structure

```
aqa-inforce-hryhoriistruk
├── .github
│   └── workflows
│       ├── python-ci.yml        
│       └── cypress-ci.yml       
├── cypress
│   ├── downloads                
│   ├── e2e
│   │   ├── user-spec.cy.js      
│   │   └── admin-spec.cy.js     
│   ├── fixtures                 
│   └── support                  
├── python
│   ├── tests                    
│   ├── pages                    
│   ├── conftest.py              
│   ├── helpers.py               
│   └── pytest.ini, pyproject.toml, .flake8, requirements.txt, .env.example
├── .editorconfig               
├── .gitignore
├── .pre-commit-config.yaml      
├── test-cases.txt
├── cypress.config.js
├── package.json
├── package-lock.json
└── README.md
```

## Notes

- Every test creates its own room with a unique name through the Admin API and deletes it
  (with its bookings) afterwards, so tests are independent and do not pollute the shared site.
- The demo site is shared and reset periodically - if a test flakes, simply re-run it
  (or rely on the automatic retries in CI).
- API tests accept both response codes where the public gateway and the room service differ
  (200/202, 401/403); see OBS-03 in `test-cases.txt`.

## CI

GitHub Actions, triggered on push to `main`, `develop`, `working`, on pull requests to
`main`/`develop`, and manually via `workflow_dispatch`:

- **`python-ci.yml`** — matrix over Python 3.9-3.12: `flake8`, `black --check`, `isort
  --check-only`, then `pytest` with automatic retries and both HTML + Allure artifacts.
- **`cypress-ci.yml`** — `npm ci` + Cypress run in Chrome; screenshots are uploaded as an
  artifact on failure.
