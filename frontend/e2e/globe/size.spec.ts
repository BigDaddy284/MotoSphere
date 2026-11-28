import type { Page } from '@playwright/test'
import { colourAt } from '../pixel.ts'
import { expect, test } from './fixtures'

/**
 * These tests run in the browser of the globe tests, on the site as it was
 * built, with the real engine. They change the size of the stage, as a
 * person does who closes a panel, makes the window smaller or turns a
 * phone, and read from the page and from the picture itself what the globe
 * shows afterwards.
 *
 * Around the Earth the engine draws the stars, the sun and the moon where
 * they stand at the time of the page. So every test here gives the page one
 * fixed time, and the sky of the test is the same sky on every day.
 */
const THE_TIME_OF_THE_TESTS = new Date('2026-06-21T12:00:00Z')

/** How long the globe may take to say that the Earth is drawn (see earth.spec.ts). */
const DRAWN_WITHIN = 60_000

/**
 * For how long an engine has to have drawn nothing to be taken as at rest,
 * and how long it may take to come to that (see earth.spec.ts).
 */
const AT_REST = 1_500
const AT_REST_WITHIN = 30_000

/**
 * The share of the shorter side of the stage that the Earth takes when the
 * globe opens. It is written here a second time, and not taken from the
 * application, so that the test holds the size itself.
 */
const SHARE_OF_THE_SHORTER_SIDE = 0.8

// The screens the layout knows, by the size of the window.
const SCREENS: [name: string, width: number, height: number][] = [
  ['a desktop', 1280, 720],
  ['a phone held upright', 390, 844],
  ['a phone lying', 844, 390],
  ['a tablet held upright', 768, 1024],
  ['the smallest phone', 320, 568],
]

// Below this width the screen is narrow: the panels lie over the globe stage.
const NARROW_BELOW = 900

/** The eight directions of a compass, as steps across and down the page. */
const DIRECTIONS: [name: string, across: number, down: number][] = [
  ['east', 1, 0],
  ['south-east', Math.SQRT1_2, Math.SQRT1_2],
  ['south', 0, 1],
  ['south-west', -Math.SQRT1_2, Math.SQRT1_2],
  ['west', -1, 0],
  ['north-west', -Math.SQRT1_2, -Math.SQRT1_2],
  ['north', 0, -1],
  ['north-east', Math.SQRT1_2, -Math.SQRT1_2],
]

/**
 * Has a page note, from before anything of it runs, how many pictures its
 * 3D pictures were told to draw and when the last one was. A picture is
 * counted with the first thing a 3D picture is told to draw in one turn of
 * the page, because an engine draws a picture in one turn (earth.spec.ts
 * has the same, with more).
 */
const NOTE_THE_PICTURES = `(() => {
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
  Object.defineProperty(globalThis, 'picturesOfTheEngine', {
    get: () => ({ pictures, still: performance.now() - lastPicture }),
  })
})()`
const PICTURES = 'globalThis.picturesOfTheEngine.pictures'
const STILL = 'globalThis.picturesOfTheEngine.still'

/** Reads a number the page noted, and fails for anything else. */
async function noted(page: Page, what: string): Promise<number> {
  const value: unknown = await page.evaluate(what)
  if (typeof value !== 'number') {
    throw new Error(`The page noted nothing of the engine: ${JSON.stringify(value)}`)
  }
  return value
}

/** A box of the page: where it is and how large. */
type Box = { x: number; y: number; width: number; height: number }

function parts(page: Page) {
  const stage = page.getByRole('main', { name: 'Globe' })
  return {
    stage,
    /** What the engine draws on. */
    surface: stage.locator('canvas'),
    sections: page.getByRole('button', { name: 'Sections', exact: true }),
    details: page.getByRole('button', { name: 'Details', exact: true }),
  }
}

/** Where the stage is in the page now. */
async function room(page: Page): Promise<Box> {
  const box = await parts(page).stage.boundingBox()
  if (box === null) {
    throw new Error('The globe stage has no place in the page: it is not visible')
  }
  return box
}

/** How many pixels the picture of the surface has, across and down. */
async function pixels(page: Page): Promise<number[]> {
  return parts(page).surface.evaluate((canvas) =>
    canvas instanceof HTMLCanvasElement ? [canvas.width, canvas.height] : [],
  )
}

/** How bright a colour is: its red, green and blue together, from 0 to 765. */
function brightness([red, green, blue]: readonly [number, number, number]): number {
  return red + green + blue
}

/**
 * The sky is black but for its stars, and a star is a point or two wide.
 * So the sky at a place is read at three points two pixels apart, and the
 * darkest of them is the sky.
 */
async function darkestOfThree(page: Page, x: number, y: number): Promise<number> {
  const read: number[] = []
  for (const step of [-2, 0, 2]) {
    read.push(brightness(await colourAt(page, Math.round(x) + step, Math.round(y) + step)))
  }
  return Math.min(...read)
}

/** Opens the page at a size of the window and waits until the Earth is drawn. */
async function openAt(page: Page, width: number, height: number): Promise<void> {
  await page.setViewportSize({ width, height })
  await page.clock.setFixedTime(THE_TIME_OF_THE_TESTS)
  await page.addInitScript(NOTE_THE_PICTURES)
  await page.goto('./')
  await expect(parts(page).stage.locator('[aria-busy]')).toHaveAttribute('aria-busy', 'false', {
    timeout: DRAWN_WITHIN,
  })
}

/** Waits until the engine has drawn nothing for a second and a half. */
async function untilTheEngineRests(page: Page): Promise<void> {
  await expect
    .poll(() => noted(page, STILL), {
      message: 'milliseconds since the engine last drew a picture',
      timeout: AT_REST_WITHIN,
    })
    .toBeGreaterThanOrEqual(AT_REST)
}

/**
 * Holds that the globe fills the stage as it is now and shows the whole
 * Earth in the middle of it, round, at four fifths of its shorter side:
 * the surface is where the stage is and as large, its picture has a pixel
 * for each pixel of it, and in the eight directions of a compass there is
 * Earth a tenth of the radius inside the edge the Earth is to have, and sky
 * a tenth outside it. Gives the stage, for what a test holds beside that.
 */
async function fillsTheStageWithTheWholeEarth(page: Page, when: string): Promise<Box> {
  // The style of the engine keeps the surface as large as the stage; the
  // picture in it gets its pixels from the engine, in the next turn of its
  // work, and the engine draws anew then.
  await expect
    .poll(
      async () => {
        const { width, height } = await room(page)
        const [across, down] = await pixels(page)
        return across === width && down === height
      },
      { message: `${when}: the picture has a pixel for each pixel of the stage` },
    )
    .toBe(true)
  await untilTheEngineRests(page)
  const stage = await room(page)
  expect(await parts(page).surface.boundingBox(), `${when}: where the surface is`).toEqual(stage)
  expect(await pixels(page), `${when}: the pixels of the picture`).toEqual([
    stage.width,
    stage.height,
  ])

  const x = stage.x + stage.width / 2
  const y = stage.y + stage.height / 2
  const radius = (SHARE_OF_THE_SHORTER_SIDE * Math.min(stage.width, stage.height)) / 2
  for (const [direction, across, down] of DIRECTIONS) {
    const inside = await colourAt(
      page,
      Math.round(x + 0.9 * radius * across),
      Math.round(y + 0.9 * radius * down),
    )
    expect(brightness(inside), `${when}: inside, to the ${direction}`).toBeGreaterThan(300)
    const outside = await darkestOfThree(page, x + 1.1 * radius * across, y + 1.1 * radius * down)
    expect(outside, `${when}: outside, to the ${direction}`).toBeLessThan(150)
  }
  return stage
}

test.describe('the globe when the stage changes its size', () => {
  test('keeps the Earth as large and in the middle when the panels beside it close and open, on a desktop', async ({
    page,
  }) => {
    await openAt(page, 1280, 720)
    const { sections, details } = parts(page)
    const open = await fillsTheStageWithTheWholeEarth(page, 'as it opens')
    expect(open).toEqual({ x: 220, y: 48, width: 700, height: 672 })

    let pictures = await noted(page, PICTURES)
    await sections.click()
    const wider = await fillsTheStageWithTheWholeEarth(page, 'with the sections closed')
    expect(wider).toEqual({ x: 0, y: 48, width: 920, height: 672 })
    expect(await noted(page, PICTURES), 'a new picture').toBeGreaterThan(pictures)

    pictures = await noted(page, PICTURES)
    await details.click()
    const widest = await fillsTheStageWithTheWholeEarth(page, 'with both panels closed')
    expect(widest).toEqual({ x: 0, y: 48, width: 1280, height: 672 })
    expect(await noted(page, PICTURES), 'a new picture').toBeGreaterThan(pictures)

    pictures = await noted(page, PICTURES)
    await sections.click()
    await details.click()
    const again = await fillsTheStageWithTheWholeEarth(page, 'with both panels open again')
    expect(again).toEqual(open)
    expect(await noted(page, PICTURES), 'a new picture').toBeGreaterThan(pictures)
  })

  test('takes four fifths of the shorter side again when the window is made smaller and larger, on a desktop', async ({
    page,
  }) => {
    await openAt(page, 1280, 720)
    await fillsTheStageWithTheWholeEarth(page, 'as it opens')

    let pictures = await noted(page, PICTURES)
    await page.setViewportSize({ width: 1000, height: 560 })
    const smaller = await fillsTheStageWithTheWholeEarth(page, 'in a smaller window')
    expect(smaller).toEqual({ x: 220, y: 48, width: 420, height: 512 })
    expect(await noted(page, PICTURES), 'a new picture').toBeGreaterThan(pictures)

    pictures = await noted(page, PICTURES)
    await page.setViewportSize({ width: 1600, height: 900 })
    const larger = await fillsTheStageWithTheWholeEarth(page, 'in a larger window')
    expect(larger).toEqual({ x: 220, y: 48, width: 1020, height: 852 })
    expect(await noted(page, PICTURES), 'a new picture').toBeGreaterThan(pictures)
  })

  for (const [screen, width, height] of SCREENS) {
    test(`shows the whole Earth again when the screen is turned on its side and back, on ${screen}`, async ({
      page,
    }) => {
      await openAt(page, width, height)
      const upright = await fillsTheStageWithTheWholeEarth(page, 'as it opens')

      if (width < NARROW_BELOW) {
        // A panel lies over the stage here and takes no room from it.
        const { sections } = parts(page)
        await sections.click()
        await expect(sections).toHaveAttribute('aria-expanded', 'true')
        expect(await room(page), 'the stage under a panel').toEqual(upright)
        expect(await pixels(page), 'the picture under a panel').toEqual([
          upright.width,
          upright.height,
        ])
        await sections.click()
        await expect(sections).toHaveAttribute('aria-expanded', 'false')
      }

      let pictures = await noted(page, PICTURES)
      await page.setViewportSize({ width: height, height: width })
      const turned = await fillsTheStageWithTheWholeEarth(page, 'turned on its side')
      expect(turned.width, 'the stage has another width').not.toBe(upright.width)
      expect(await noted(page, PICTURES), 'a new picture').toBeGreaterThan(pictures)

      pictures = await noted(page, PICTURES)
      await page.setViewportSize({ width, height })
      const back = await fillsTheStageWithTheWholeEarth(page, 'turned back')
      expect(back).toEqual(upright)
      expect(await noted(page, PICTURES), 'a new picture').toBeGreaterThan(pictures)
    })
  }
})
