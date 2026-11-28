import { defineConfig, devices } from '@playwright/test'
import { GLOBE_BROWSER, TEST_BROWSER } from './e2e/browser.ts'
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
    // How a browser is started where a project does not say otherwise
    // (e2e/browser.ts).
    launchOptions: TEST_BROWSER,
  },
  projects: [
    // Every test that is not about the globe, in a browser that gives a page
    // no 3D picture.
    {
      name: 'chromium',
      testIgnore: '**/e2e/globe/**',
      use: { ...devices['Desktop Chrome'] },
    },
    // The tests of the globe, in `e2e/globe`: in a browser that is told how
    // to draw 3D pictures, and one test at a time, whatever the number of
    // workers. Two globes drawn at once in software take each other's
    // processor time, and on GitHub's Windows machine neither is then loaded
    // within forty seconds (FND-058; TESTING.md has what was measured).
    //
    // A test of the globe has 90 seconds, where a test has 30 otherwise.
    // Its browser draws in software, and a test that waits for the Earth or
    // reads its picture waits for that drawing: how long that takes is a
    // matter of the machine and of how much of the Earth is in view
    // (GLB-031; TESTING.md, "The browser of the globe tests"). A globe test
    // holds what the page shows, not how fast a machine is.
    {
      name: 'globe',
      testDir: './e2e/globe',
      workers: 1,
      timeout: 90_000,
      use: { ...devices['Desktop Chrome'], launchOptions: GLOBE_BROWSER },
    },
  ],
  webServer: {
    command: `npm run data && npm run build && npm run preview -- --host ${HOST} --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
