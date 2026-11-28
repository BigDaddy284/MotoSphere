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
 * How long the globe may take to say that the Earth is drawn. Mostly that
 * is a few seconds. On GitHub's Windows machine it was up to fifteen in 22
 * openings that were measured, and more than twenty once, in a test that
 * waited for twenty and failed (TESTING.md, "What a slow machine does to
 * the tests of the Earth"). A test holds what the engine does, not how fast
 * a machine is: it waits for two thirds of the 90 seconds it has.
 */
const DRAWN_WITHIN = 60_000

/**
 * For how long an engine has to have drawn nothing to be taken as at rest,
 * and how long it may take to come to that once the Earth is drawn. The
 * last picture came up to 3.7 seconds after that moment where it was
 * measured (TESTING.md, "What a slow machine does to the tests of the
 * Earth").
 */
const AT_REST = 1_500
const AT_REST_WITHIN = 30_000

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
 * Has a page note, from before anything of it runs, two things that a test
 * cannot see from outside at the moment it needs them: how many pictures
 * its 3D pictures were told to draw, and which files had arrived. A picture
 * is counted with the first thing a 3D picture is told to draw in one turn
 * of the page, because an engine draws a picture in one turn. The page
 * notes both again at the moment the globe says that it is no longer busy.
 * And it notes when the last picture was drawn, so that a test can ask how
 * long the engine has drawn nothing. The notes are kept beside the page's
 * own things: NOW gives them as they are, WHEN_SAID as they were at that
 * moment.
 */
const NOTE_WHAT_THE_ENGINE_DOES = `(() => {
  let pictures = 0
  let drawing = false
  let lastPicture = performance.now()
  const context = WebGL2RenderingContext.prototype
  for (const way of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced', 'drawRangeElements']) {
    const draw = context[way]
    context[way] = function (...given) {
      if (!drawing) {
        drawing = true
        pictures += 1
        lastPicture = performance.now()
        queueMicrotask(() => {
          drawing = false
        })
      }
      return draw.apply(this, given)
    }
  }
  const now = () => ({
    pictures,
    still: performance.now() - lastPicture,
    arrived: performance.getEntriesByType('resource').map((entry) => new URL(entry.name).pathname),
  })
  let whenSaid
  new MutationObserver((changes) => {
    for (const { target } of changes) {
      if (
        whenSaid === undefined &&
        target instanceof Element &&
        target.closest('main') !== null &&
        target.getAttribute('aria-busy') === 'false'
      ) {
        whenSaid = now()
      }
    }
  }).observe(document, { subtree: true, attributes: true, attributeFilter: ['aria-busy'] })
  Object.defineProperty(globalThis, 'notesOfTheEngine', { get: () => ({ now: now(), whenSaid }) })
})()`
const NOW = 'globalThis.notesOfTheEngine.now'
const WHEN_SAID = 'globalThis.notesOfTheEngine.whenSaid'

/**
 * What the page noted: the pictures drawn, for how many milliseconds none
 * has been drawn, and the paths of the files that arrived.
 */
type Notes = { pictures: number; still: number; arrived: string[] }

/** Reads what the page noted, and fails for anything else. */
function notes(noted: unknown): Notes {
  if (
    typeof noted === 'object' &&
    noted !== null &&
    'pictures' in noted &&
    typeof noted.pictures === 'number' &&
    'still' in noted &&
    typeof noted.still === 'number' &&
    'arrived' in noted &&
    Array.isArray(noted.arrived)
  ) {
    return { pictures: noted.pictures, still: noted.still, arrived: noted.arrived.map(String) }
  }
  throw new Error(`The page noted nothing of the engine: ${JSON.stringify(noted)}`)
}

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

  test('says that the Earth is drawn when its pictures have arrived, and asks for nothing and draws nothing new after that', async ({
    page,
  }) => {
    const under = new Set<string>()
    page.on('request', (request) => {
      under.add(request.url())
    })
    page.on('requestfinished', (request) => {
      under.delete(request.url())
    })
    await page.addInitScript(NOTE_WHAT_THE_ENGINE_DOES)
    await page.goto('./')
    const { stage } = parts(page)

    await untilTheEarthIsDrawn(page)
    // What the page noted at the moment the globe said so. A test sees that
    // moment late, by as much as a second, and an engine can do much in a
    // second: so the page notes it there and then.
    const said = notes(await page.evaluate(WHEN_SAID))
    const picture = await stage.screenshot()
    const pictures = said.arrived.filter((path) => path.startsWith(PICTURES))

    expect(said.pictures).toBeGreaterThan(0)
    expect(pictures).toContain(`${PICTURES}tilemapresource.xml`)
    expect(pictures.filter((path) => path.endsWith('.jpg')).length).toBeGreaterThanOrEqual(2)
    expect([...under]).toEqual([])
    // The engine draws when something has changed and not all the time, so
    // once the Earth is drawn it comes to rest. Not at that very moment:
    // it draws the complete picture a few times more, of its own accord,
    // for work it had under way when the last piece arrived. How many
    // times is the engine's affair and differs from machine to machine.
    // What is held is that it stops: an engine that goes on drawing never
    // lets this long pass without a picture.
    await expect
      .poll(async () => notes(await page.evaluate(NOW)).still, {
        message: 'milliseconds since the engine last drew a picture',
        timeout: AT_REST_WITHIN,
      })
      .toBeGreaterThanOrEqual(AT_REST)
    const later = notes(await page.evaluate(NOW))
    expect([...under]).toEqual([])
    expect(later.arrived).toEqual(said.arrived)
    expect((await stage.screenshot()).equals(picture)).toBe(true)
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
    //
    // Twenty-two engines one after the other take their time where 3D
    // pictures are drawn in software: on GitHub's machines this test took
    // 8.9 seconds on Linux and 18.5 on Windows when it was written. A test
    // of the globe has 90 seconds (playwright.config.ts, GLB-031): it holds
    // what the engine does, not how fast a machine is.
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
