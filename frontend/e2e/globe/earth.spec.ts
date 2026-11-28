import type { Locator, Page, Route } from '@playwright/test'
import { SITE_PATH } from '../../site.ts'
import { ENGINE_ADDRESS } from '../../src/globe/engineAddress.ts'
import { expect, test } from './fixtures'

/**
 * These tests run in the browser of the globe tests, which draws 3D
 * pictures, on the site as it was built: the engine in them is the real
 * one. The fixture of every browser test fails each of them for any warning
 * or error on the console, for a request that fails and for an answer that
 * says a file is not there.
 */

/**
 * How long the globe may take to say that the Earth is drawn. Alone, a
 * globe was complete within eight seconds on every machine it was measured
 * on (TESTING.md, "The browser of the globe tests").
 */
const DRAWN_WITHIN = 20_000

/** Where the pictures of the Earth are that come with the engine. */
const PICTURES = `${ENGINE_ADDRESS}Assets/Textures/NaturalEarthII/`

/** The script that starts the engine, by the name the build gives it. */
const ENGINE_SCRIPT = /\/assets\/earth-[^/]+\.js$/

function parts(page: Page) {
  const stage = page.getByRole('main', { name: 'Globe' })
  return {
    stage,
    /** The element that says whether the globe is still being drawn. */
    globe: stage.locator('[aria-busy]'),
    /** What the engine draws on. */
    surfaces: stage.locator('canvas'),
  }
}

/** Waits until the globe says that its first complete picture is drawn. */
async function untilTheEarthIsDrawn(page: Page): Promise<void> {
  await expect(parts(page).globe).toHaveAttribute('aria-busy', 'false', { timeout: DRAWN_WITHIN })
}

/**
 * Has a page count, from before anything of it runs, how many times a 3D
 * picture is told to draw something. The count is kept beside the page's
 * own things, and read with DRAWINGS.
 */
const COUNT_THE_DRAWINGS = `(() => {
  let drawings = 0
  const pictures = WebGL2RenderingContext.prototype
  for (const way of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced', 'drawRangeElements']) {
    const draw = pictures[way]
    pictures[way] = function (...given) {
      drawings += 1
      return draw.apply(this, given)
    }
  }
  Object.defineProperty(globalThis, 'drawingsCounted', { get: () => drawings })
})()`
const DRAWINGS = 'globalThis.drawingsCounted'

async function box(locator: Locator) {
  const result = await locator.boundingBox()
  if (result === null) {
    throw new Error(`${locator.toString()} has no bounding box: it is not visible`)
  }
  return result
}

/**
 * Has the page start the engine in an element of its own and stop it at
 * once, a number of times in a row. Then once more, left running: started,
 * drawn complete, given another size, which makes it draw again, and
 * stopped a second later. And once to the end: started, drawn complete,
 * and stopped by whoever is told so, there and then.
 *
 * Gives how many drawing surfaces the element held while each engine ran,
 * what was left in it after each was stopped, and how many times each of
 * the last two said that the Earth is drawn.
 */
function startAndStop(script: string, times: number): string {
  return `(async () => {
    const { start } = await import(${JSON.stringify(script)})
    const element = document.createElement('div')
    element.style.cssText = 'position: fixed; left: 0; top: 0; width: 300px; height: 200px'
    document.body.append(element)
    const running = []
    const left = []
    for (let round = 0; round < ${times}; round += 1) {
      const stop = start(element, { drawn() {} })
      running.push(element.querySelectorAll('canvas').length)
      stop()
      left.push(element.childElementCount)
    }
    const saidLeftRunning = await new Promise((resolve) => {
      let said = 0
      const stop = start(element, {
        drawn() {
          said += 1
          if (said === 1) {
            element.style.width = '320px'
            setTimeout(() => {
              stop()
              resolve(said)
            }, 1000)
          }
        },
      })
    })
    left.push(element.childElementCount)
    const saidStoppedAtOnce = await new Promise((resolve) => {
      let said = 0
      const stop = start(element, {
        drawn() {
          said += 1
          stop()
          setTimeout(() => resolve(said), 500)
        },
      })
    })
    left.push(element.childElementCount)
    element.remove()
    return { running, left, saidLeftRunning, saidStoppedAtOnce }
  })()`
}

test.describe('the globe in a browser that draws 3D pictures', () => {
  test('is one drawing surface that fills the stage, with a pixel for each pixel of it', async ({
    page,
  }) => {
    await page.goto('./')
    const { stage, surfaces } = parts(page)
    await untilTheEarthIsDrawn(page)

    await expect(surfaces).toHaveCount(1)
    const room = await box(stage)
    expect(room).toEqual({ x: 220, y: 48, width: 700, height: 672 })
    expect(await box(surfaces)).toEqual(room)
    expect(
      await surfaces.evaluate((surface) =>
        surface instanceof HTMLCanvasElement ? [surface.width, surface.height] : [],
      ),
    ).toEqual([700, 672])
    expect(
      await page.evaluate(() => [
        document.documentElement.scrollWidth,
        document.documentElement.scrollHeight,
      ]),
    ).toEqual([1280, 720])
  })

  test('does not hold the page back: with the script of the engine held back, the page is there and works, and the globe is busy', async ({
    page,
  }) => {
    const held: Route[] = []
    await page.route(ENGINE_SCRIPT, (route) => {
      held.push(route)
    })

    await page.goto('./')
    const { globe, surfaces } = parts(page)
    const sections = page.getByRole('navigation', { name: 'Sections' })
    await expect.poll(() => held.length, 'requests for the script of the engine, held back').toBe(1)
    await expect(page.getByRole('heading', { level: 1, name: 'MotoSphere' })).toBeVisible()
    await expect(page.getByRole('banner').getByRole('status')).toHaveText(/^Data updated /)
    await sections.getByRole('button', { name: 'Championships' }).click()
    await expect(sections.getByRole('button', { name: 'Championships' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(globe).toHaveAttribute('aria-busy', 'true')
    await expect(surfaces).toHaveCount(0)

    await held[0]?.continue()

    await untilTheEarthIsDrawn(page)
    await expect(surfaces).toHaveCount(1)
    expect(held).toHaveLength(1)
  })

  test('says that the Earth is drawn when its pictures have arrived, and asks for nothing and draws nothing after that', async ({
    page,
  }) => {
    const under = new Set<string>()
    const arrived: string[] = []
    page.on('request', (request) => {
      under.add(request.url())
    })
    page.on('requestfinished', (request) => {
      under.delete(request.url())
      arrived.push(new URL(request.url()).pathname)
    })
    await page.addInitScript(COUNT_THE_DRAWINGS)
    await page.goto('./')
    const { stage } = parts(page)

    await untilTheEarthIsDrawn(page)
    const drawings = await page.evaluate(DRAWINGS)
    const picture = await stage.screenshot()
    const pictures = arrived.filter((path) => path.startsWith(PICTURES))
    const then = arrived.length

    expect(drawings).toBeGreaterThan(0)
    expect([...under]).toEqual([])
    expect(pictures).toContain(`${PICTURES}tilemapresource.xml`)
    expect(pictures.filter((path) => path.endsWith('.jpg')).length).toBeGreaterThanOrEqual(2)
    // Long enough for an engine that had more to fetch or to draw to do so.
    await page.waitForTimeout(1_500)
    expect([...under]).toEqual([])
    expect(arrived.slice(then)).toEqual([])
    expect((await stage.screenshot()).equals(picture)).toBe(true)
    // The engine draws when something has changed and not all the time.
    expect(await page.evaluate(DRAWINGS)).toBe(drawings)
  })

  test('asks nothing of another computer: every file comes from the site, the engine files from their folder', async ({
    page,
    baseURL,
  }) => {
    const asked: URL[] = []
    page.on('request', (request) => {
      asked.push(new URL(request.url()))
    })

    await page.goto('./')
    await untilTheEarthIsDrawn(page)

    const site = new URL(baseURL ?? '')
    expect(site.pathname).toBe(SITE_PATH)
    expect(
      asked
        .filter(
          (address) => address.origin !== site.origin || !address.pathname.startsWith(SITE_PATH),
        )
        .map(String),
    ).toEqual([])
    expect(asked.filter((address) => ENGINE_SCRIPT.test(address.pathname))).toHaveLength(1)
    expect(
      asked.filter((address) => address.pathname.startsWith(ENGINE_ADDRESS)).length,
    ).toBeGreaterThan(5)
    // Nothing of the engine's services that need an account.
    expect(asked.map(String).filter((address) => /ion|token|key=/i.test(address))).toEqual([
      new URL(`${ENGINE_ADDRESS}Assets/Images/ion-credit.png`, site).href,
    ])
  })

  test('can be stopped and started again twenty times in a row, and the browser has its 3D picture back each time', async ({
    page,
  }) => {
    // A browser keeps only so many 3D pictures for a page (sixteen in this
    // one). When a page asks for one more, it takes the oldest away and
    // says so on the console, which fails this test: the oldest is the
    // globe of the page.
    const scripts: string[] = []
    page.on('request', (request) => {
      if (ENGINE_SCRIPT.test(new URL(request.url()).pathname)) {
        scripts.push(request.url())
      }
    })
    await page.goto('./')
    const { surfaces } = parts(page)
    await untilTheEarthIsDrawn(page)
    expect(scripts).toHaveLength(1)

    const result = await page.evaluate(startAndStop(scripts[0] ?? '', 20))

    expect(result).toEqual({
      running: Array.from({ length: 20 }, () => 1),
      left: Array.from({ length: 22 }, () => 0),
      saidLeftRunning: 1,
      saidStoppedAtOnce: 1,
    })
    await expect(surfaces).toHaveCount(1)
    expect(
      await surfaces.evaluate(
        (surface) =>
          surface instanceof HTMLCanvasElement &&
          surface.getContext('webgl2')?.isContextLost() === false,
      ),
    ).toBe(true)
  })
})
