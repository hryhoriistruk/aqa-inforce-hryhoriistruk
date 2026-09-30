import './commands';

Cypress.on('uncaught:exception', (err) => {
  if (/Minified React error #418|Hydration failed/i.test(err.message)) {
    return false;
  }
  return true;
});
