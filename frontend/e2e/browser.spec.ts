import { createServer } from 'node:http'
import type { AddressInfo } from 'node:net'
import { chromium } from '@playwright/test'
import type { LaunchOptions, Page } from '@playwright/test'
import {
  FEATURES_OFF,
  GLOBE_BROWSER,
  NO_3D_SWITCH,
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

/**
 * Starts one more browser as the browser of this project is started, and
 * gives every word it was started with that begins as `word` does.
 */
async function toldOf(word: string): Promise<string[]> {
  const started = await chromium.launchServer()
  try {
    return started.process().spawnargs.filter((told) => told.startsWith(word))
  } finally {
    await started.close()
  }
}

/** Has the page ask for a picture of each kind, each on a canvas of its own. */
const ASK_FOR_PICTURES = `(() => {
  const given = (kind) => document.createElement('canvas').getContext(kind) !== null
  const flat = document.createElement('canvas')
  flat.width = 2
  flat.height = 2
  const pen = flat.getContext('2d')
  if (pen === null) {
    return { webgl2: given('webgl2'), webgl: given('webgl'), flat: null }
  }
  pen.fillStyle = 'rgb(10, 200, 30)'
  pen.fillRect(0, 0, 2, 2)
  return {
    webgl2: given('webgl2'),
    webgl: given('webgl'),
    flat: [...pen.getImageData(1, 1, 1, 1).data],
  }
})()`

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

  test('is told once to give its pages no 3D picture', async () => {
    expect(await toldOf(NO_3D_SWITCH)).toEqual([NO_3D_SWITCH])
    expect(NO_3D_SWITCH).toBe('--disable-3d-apis')
    expect(TEST_BROWSER).toEqual({
      ignoreDefaultArgs: [PLAYWRIGHTS_OWN_SWITCH],
      args: [TEST_BROWSER_SWITCH, NO_3D_SWITCH],
    })
  })

  test('gives a page no 3D picture, and a flat one as before, without a word of its own', async ({
    page,
  }) => {
    // The fixture of every browser test fails this test for any warning or
    // error on the console.
    await page.goto('./')
    expect(await page.evaluate(ASK_FOR_PICTURES)).toEqual({
      webgl2: false,
      webgl: false,
      flat: [10, 200, 30, 255],
    })
  })

  test('is set for the project of these tests, and the browser of the globe for its project', ({
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
