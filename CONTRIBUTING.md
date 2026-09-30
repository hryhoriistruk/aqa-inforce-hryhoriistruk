# Contributing to aqa-inforce-hryhoriistruk

## Setup

- Cypress: `npm install` in the repository root.
- Python: see the "Python" section of `README.md` (`cd python`, virtual environment,
  `pip install -r requirements.txt`, `playwright install chromium`).

## Rules

- Every automated test must map to a case in `test-cases.txt` (put the id in the test name
  or a comment) and every change of behaviour must be reflected there.
- Tests must be independent: create your own room, delete it (and its bookings) in cleanup.
- Python style: `flake8 .`, `black .`, `isort .` (run in `python`); pre-commit hooks are in
  `.pre-commit-config.yaml`.
- Cypress style: keep helpers in `cypress/support/commands.js`, test data in fixtures.

## Pull requests

Describe what changed, which test cases are affected, and attach a test run result.
