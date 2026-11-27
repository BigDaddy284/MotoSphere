import { chromium } from '@playwright/test'
import type { Browser } from '@playwright/test'
import { TEST_BROWSER } from './browser.ts'
import { expect, test } from './fixtures'

// A measurement of the planner's, not a test of the application: how long
// the engine takes to show the Earth on this machine, step by step, alone and
// with a second browser doing the same at the same moment. Every result is
// written to the log on a line that begins MEASURE.
const BROWSERS: Record<string, string[]> = {
  'as the tests start it': [],
  'use-angle=swiftshader': ['--use-angle=swiftshader'],
}
const DRAWING: Record<string, string> = {
  'every frame': '',
  'on request': '&onrequest',
}
const WAIT = 40_000

const FOUND = `(() => {
  const round = (n) => (n === undefined ? null : Math.round(n))
  const times = Object.fromEntries(Object.entries(globalThis.spikeTimes ?? {}).map(([k, v]) => [k, round(v)]))
  const resources = performance.getEntriesByType('resource').map((e) => ({
    name: e.name.split('/').slice(-2).join('/').slice(-40),
    start: round(e.startTime),
    took: round(e.duration),
    waited: round(e.responseStart - e.requestStart),
  }))
  const widget = globalThis.spikeWidget
  return {
    cores: navigator.hardwareConcurrency,
    frameAt: (globalThis.spikeTrace?.frameAt ?? []).map(round),
    progress: (globalThis.spikeTrace?.progress ?? []).map(([at, waiting]) => [round(at), waiting]),
    now: round(performance.now()),
    times,
    frames: widget ? widget.scene.frameState.frameNumber : null,
    resources: resources.length,
    lastEnd: Math.max(0, ...resources.map((r) => r.start + r.took)),
    slowest: resources.toSorted((a, b) => b.took - a.took).slice(0, 6),
    workers: resources.filter((r) => r.name.includes('Workers/')).map((r) => [r.name.slice(-28), r.start, r.took]),
  }
})()`

async function watch(browser: Browser, address: string, said: string[]): Promise<unknown> {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
  page.on('console', (message) => {
    if (message.type() === 'warning' || message.type() === 'error') {
      said.push(
        `${message.type()}: ${message
          .text()
          .replace(/0x[0-9a-f]+/, '0x…')
          .slice(0, 120)}`,
      )
    }
  })
  page.on('pageerror', (error) => said.push(`uncaught: ${error.message.slice(0, 200)}`))
  page.on('requestfailed', (request) => said.push(`request failed: ${request.url().slice(-60)}`))
  const started = Date.now()
  let outcome = 'loaded'
  try {
    await page.goto(address)
    await page.waitForFunction(`globalThis.spikeTimes?.loaded !== undefined`, null, {
      timeout: WAIT,
    })
  } catch (error) {
    outcome = String(error).slice(0, 80)
  }
  const found = await page.evaluate(FOUND)
  return { outcome, ms: Date.now() - started, found }
}

test.describe.configure({ mode: 'serial' })

for (const [round, together] of [1, 2, 1].entries()) {
  for (const [browserName, extra] of Object.entries(BROWSERS)) {
    for (const [drawing, how] of Object.entries(DRAWING)) {
      test(`measure: ${together} at once, ${browserName}, ${drawing}, round ${round + 1}`, async ({
        baseURL,
      }) => {
        test.setTimeout(240_000)
        const said: string[] = []
        const browsers = await Promise.all(
          Array.from({ length: together }, () =>
            chromium.launch({ ...TEST_BROWSER, args: [...(TEST_BROWSER.args ?? []), ...extra] }),
          ),
        )
        let found: unknown[] = []
        try {
          found = await Promise.all(
            browsers.map((browser) => watch(browser, `${baseURL ?? ''}?spike${how}`, said)),
          )
        } finally {
          await Promise.all(browsers.map((browser) => browser.close()))
        }
        process.stdout.write(
          `MEASURE ${process.platform} | ${together} at once | ${browserName} | ${drawing} | ${JSON.stringify(found)} | ${said.length} said | ${JSON.stringify([...new Set(said)])}\n`,
        )
        expect(true).toBe(true)
      })
    }
  }
}
