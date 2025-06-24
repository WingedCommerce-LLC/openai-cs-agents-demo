import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: true,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    env: {
      // Test environment variables
      API_URL: 'http://localhost:8000',
      TEST_USER_EMAIL: 'test@example.com',
      TEST_USER_PASSWORD: 'test-password-123'
    },
    setupNodeEvents(on, config) {
      // Code coverage setup
      require('@cypress/code-coverage/task')(on, config)

      // Custom tasks
      on('task', {
        log(message) {
          console.log(message)
          return null
        },

        // Database seeding task
        seedDatabase() {
          // Implementation would connect to test database and seed data
          console.log('Seeding test database...')
          return null
        },

        // Clean database task
        cleanDatabase() {
          // Implementation would clean test database
          console.log('Cleaning test database...')
          return null
        }
      })

      return config
    }
  },

  component: {
    devServer: {
      framework: 'next',
      bundler: 'webpack'
    },
    supportFile: 'cypress/support/component.ts',
    specPattern: 'cypress/component/**/*.cy.{js,jsx,ts,tsx}',
    indexHtmlFile: 'cypress/support/component-index.html'
  },

  // Coverage settings
  env: {
    codeCoverage: {
      url: 'http://localhost:3000/__coverage__'
    }
  }
})
