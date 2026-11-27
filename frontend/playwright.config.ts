import { defineConfig, devices } from '@playwright/test'
import { TEST_BROWSER } from './e2e/browser.ts'
import { SITE_PATH } from './site.ts'

const HOST = '127.0.0.1'
const PORT = 4173
// The built site is served under the path it will have when published, and
// every test reaches it through this address. A test writes addresses
// relative to it (`./`, `favicon.svg`), never from the root of the server.
const BASE_URL = `http://${HOST}:${PORT}${SITE_PATH}`

// When this run of the browser tests started. The test runner reads this file
// first and every worker inherits the value, so they all agree. The data
// tests use it to prove that the published data was exported for this run.
process.env['MOTOSPHERE_E2E_STARTED'] ??= String(Date.now())

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'off',
    // Every test runs in a browser started this way (e2e/browser.ts).
    launchOptions: TEST_BROWSER,
  },
  // The planner's measurement: the tests run in a browser without 3D pictures,
  // and the measurement beside them, one at a time, in a browser that draws them.
  projects: [
    {
      name: 'chromium',
      testIgnore: 'measure.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          ...TEST_BROWSER,
          args: [...(TEST_BROWSER.args ?? []), '--disable-3d-apis'],
        },
      },
    },
    {
      name: 'globe',
      testMatch: 'measure.spec.ts',
      workers: 1,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `npm run data && npm run build && npm run preview -- --host ${HOST} --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
