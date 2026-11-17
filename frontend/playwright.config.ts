import { defineConfig, devices } from '@playwright/test'

const HOST = '127.0.0.1'
const PORT = 4173
const BASE_URL = `http://${HOST}:${PORT}`

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
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run data && npm run build && npm run preview -- --host ${HOST} --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
