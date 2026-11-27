import { createServer } from 'node:http'
import type { AddressInfo } from 'node:net'
import { chromium } from '@playwright/test'
import type { LaunchOptions, Page } from '@playwright/test'
import {
  FEATURES_OFF,
  GLOBE_BROWSER,
  PLAYWRIGHTS_OWN_FEATURES_OFF,
  PLAYWRIGHTS_OWN_SWITCH,
  RANDOM_PORTS_FEATURE,
  TEST_BROWSER,
  TEST_BROWSER_SWITCH,
} from './browser.ts'
import { expect, test } from './fixtures'

/**
 * Starts one more browser and gives every list of features to turn off that
 * it was started with. Inside a test, Playwright starts a browser with the
 * options of the project unless the call says otherwise, so no options
 * means: as the browser of every test is started.
 */
async function featuresOffOf(options: LaunchOptions = {}): Promise<string[]> {
  const started = await chromium.launchServer(options)
  try {
    return started.process().spawnargs.filter((word) => word.startsWith(FEATURES_OFF))
  } finally {
    await started.close()
  }
}

/** How many connections the test of the ports has the browser open. */
const CONNECTIONS = 40

/** Two ports are in order when the second is at most this far after the first. */
const NEXT_IS_WITHIN = 4

/**
 * Has the page open one connection after another to a server of the test's
 * own, which closes each after one answer, and gives the port the browser
 * came from each time, in the order the connections arrived.
 */
async function portsOf(page: Page): Promise<number[]> {
  const ports: number[] = []
  const server = createServer((_request, response) => {
    response.writeHead(200, {
      'Content-Type': 'text/html',
      'Cache-Control': 'no-store',
      Connection: 'close',
    })
    response.end('<!doctype html><title>ports</title><link rel="icon" href="data:,">')
  })
  server.on('connection', (socket) => {
    ports.push(socket.remotePort ?? 0)
  })
  await new Promise<void>((resolve) => {
    server.listen(0, '127.0.0.1', resolve)
  })
  try {
    const address: AddressInfo | string | null = server.address()
    if (address === null || typeof address === 'string') {
      throw new Error('the server of the test has no port')
    }
    for (let visit = 0; visit < CONNECTIONS; visit += 1) {
      await page.goto(`http://127.0.0.1:${address.port}/`)
    }
  } finally {
    server.closeAllConnections()
    await new Promise<void>((resolve) => {
      server.close(() => {
        resolve()
      })
    })
  }
  return ports
}

test.describe('the browser of the tests', () => {
  test('is started with one list of features to turn off, which names the random ports', async () => {
    expect(await featuresOffOf()).toEqual([TEST_BROWSER_SWITCH])
  })

  test("is told Playwright's own list, and after it the feature of the random ports", () => {
    expect(TEST_BROWSER_SWITCH).toBe(
      `${FEATURES_OFF}${[...PLAYWRIGHTS_OWN_FEATURES_OFF, RANDOM_PORTS_FEATURE].join(',')}`,
    )
    expect(RANDOM_PORTS_FEATURE).toBe('TcpPortRandomizationWin')
    expect(new Set(PLAYWRIGHTS_OWN_FEATURES_OFF).size).toBe(PLAYWRIGHTS_OWN_FEATURES_OFF.length)
    expect(PLAYWRIGHTS_OWN_FEATURES_OFF).not.toContain(RANDOM_PORTS_FEATURE)
  })

  test("has Playwright's own list as Playwright gives it", async () => {
    // A browser started with none of the project's options: what Playwright
    // tells it by itself. If this fails after an upgrade of Playwright, the
    // list in browser.ts has to follow.
    expect(await featuresOffOf({ ignoreDefaultArgs: [], args: [] })).toEqual([
      PLAYWRIGHTS_OWN_SWITCH,
    ])
  })

  test('takes its ports in order where Windows would give it ports at random', async ({ page }) => {
    // What the feature is turned off for, seen from outside. On a Windows
    // where the feature is on, hardly any port is near the one before; with
    // it off, nearly every port is the next one. On other systems there is
    // no such feature, and the order of the ports is the system's own.
    const ports = await portsOf(page)
    expect(ports).toHaveLength(CONNECTIONS)
    const inOrder = ports.filter((port, index) => {
      const step = port - (ports[index - 1] ?? port)
      return step >= 1 && step <= NEXT_IS_WITHIN
    }).length
    const atLeast = process.platform === 'win32' ? CONNECTIONS / 2 : 0
    expect(inOrder).toBeGreaterThanOrEqual(atLeast)
  })

  test('is set for every project, and for the project of the globe with one word more', ({
    browserName,
  }, testInfo) => {
    expect(browserName).toBe('chromium')
    expect(testInfo.project.name).toBe('chromium')
    expect(testInfo.project.use.launchOptions).toEqual(TEST_BROWSER)
    expect(testInfo.config.projects.map((project) => project.use.launchOptions)).toEqual([
      TEST_BROWSER,
      GLOBE_BROWSER,
    ])
  })
})
