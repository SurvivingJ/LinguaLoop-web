import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5000';

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.spec.js',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },

  projects: [
    // Auth setup runs first — saves storageState to playwright/.auth/user.json
    {
      name: 'auth-setup',
      testMatch: '**/auth.setup.js',
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Reuse the auth state captured during setup
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['auth-setup'],
    },
  ],

  // Flask must be running locally before `npm run test:e2e`
  // In CI, start the server in the workflow before running this command.
});
