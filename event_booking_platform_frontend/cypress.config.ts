import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000", // Your Next.js development server URL
    setupNodeEvents(on, config) {
      // implement node event listeners here
      // (e.g., for tasks, plugins)
    },
    supportFile: "cypress/support/e2e.ts", // or e2e.js if using JavaScript
    specPattern: "cypress/e2e/**/*.cy.{js,jsx,ts,tsx}", // Pattern for test files
  },
  component: {
    devServer: {
      framework: "next",
      bundler: "webpack",
    },
  },
  // You can add other Cypress configurations here:
  // viewportWidth: 1280,
  // viewportHeight: 720,
  // video: false, // Disable video recording to save space/time
  // screenshotOnRunFailure: true,
});
