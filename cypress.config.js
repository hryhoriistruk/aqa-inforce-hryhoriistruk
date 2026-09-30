const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'https://automationintesting.online',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: 'cypress/support/e2e.js',
    viewportWidth: 1366,
    viewportHeight: 900,
    defaultCommandTimeout: 10000,
    requestTimeout: 90000,
    responseTimeout: 90000,
    video: false,
    retries: { runMode: 1, openMode: 0 },
    env: {
      apiUrl: 'https://automationintesting.online/api',
      adminUser: 'admin',
      adminPassword: 'password',
    },
  },
});
