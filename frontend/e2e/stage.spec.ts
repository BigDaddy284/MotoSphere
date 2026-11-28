import type { Locator, Page } from '@playwright/test'
import { browserDraws3D } from '../src/globe/drawing.ts'
import { ENGINE_ADDRESS } from '../src/globe/engineAddress.ts'
import { expect, test } from './fixtures'

/**
 * These tests run in a browser that gives a page no 3D picture, as every
 * browser test outside the folder `globe` does. There the globe stage says
 * that the globe cannot be shown. The fixture of every browser test fails
 * each of them for any warning or error on the console.
 */

const WHAT = 'The 3D globe cannot be shown in this browser.'
const HELP =
  'It needs 3D graphics, which this browser does not offer or has switched off. Try an up-to-date browser, or switch on graphics acceleration (also called hardware acceleration) in the settings of this one.'

interface Box {
  x: number
  y: number
  width: number
  height: number
}

async function box(locator: Locator): Promise<Box> {
  const result = await locator.boundingBox()
  if (result === null) {
    throw new Error(`${locator.toString()} has no bounding box: it is not visible`)
  }
  return result
}

function parts(page: Page) {
  const stage = page.getByRole('main', { name: 'Globe' })
  return { stage, what: stage.getByText(WHAT), help: stage.getByText(HELP) }
}

/** Fails unless the inner box lies inside the outer one, to half a pixel. */
function expectInside(inner: Box, outer: Box, name: string): void {
  expect(inner.x, `${name}: left`).toBeGreaterThanOrEqual(outer.x - 0.5)
  expect(inner.y, `${name}: top`).toBeGreaterThanOrEqual(outer.y - 0.5)
  expect(inner.x + inner.width, `${name}: right`).toBeLessThanOrEqual(outer.x + outer.width + 0.5)
  expect(inner.y + inner.height, `${name}: bottom`).toBeLessThanOrEqual(
    outer.y + outer.height + 0.5,
  )
}

test.describe('the globe stage in a browser without 3D pictures', () => {
  test('is in such a browser: the page is given no 3D picture', async ({ page }) => {
    await page.goto('./')

    expect(await page.evaluate(browserDraws3D)).toBe(false)
  })

  test('says that the globe cannot be shown and then why, and nothing else', async ({ page }) => {
    await page.goto('./')
    const { stage, what, help } = parts(page)

    await expect(what).toBeVisible()
    await expect(help).toBeVisible()
    await expect(stage.locator('p')).toHaveText([WHAT, HELP])
    await expect(stage).toHaveText(`${WHAT}${HELP}`)
    await expect(page.getByText(WHAT)).toHaveCount(1)
  })

  test('asks for no file of the engine', async ({ page }) => {
    const asked: string[] = []
    page.on('request', (request) => {
      asked.push(new URL(request.url()).pathname)
    })

    await page.goto('./')
    await expect(parts(page).what).toBeVisible()
    await expect(page.getByRole('banner').getByRole('status')).toHaveText(/^Data updated /)
    await page.waitForLoadState('networkidle')

    expect(asked.length).toBeGreaterThan(2)
    expect(asked.filter((path) => path.startsWith(ENGINE_ADDRESS))).toEqual([])
  })

  test('has the words in the middle of the stage, in the colours of the theme', async ({
    page,
  }) => {
    await page.goto('./')
    const { stage, what, help } = parts(page)
    const room = await box(stage)
    const first = await box(what)
    const second = await box(help)

    expectInside(first, room, 'the first sentence')
    expectInside(second, room, 'the second sentence')
    const middle = room.x + room.width / 2
    expect(Math.abs(first.x + first.width / 2 - middle)).toBeLessThanOrEqual(0.5)
    expect(Math.abs(second.x + second.width / 2 - middle)).toBeLessThanOrEqual(0.5)
    // The second sentence is under the first, a little apart from it.
    expect(second.y - (first.y + first.height)).toBeCloseTo(8, 1)
    // As much room above the words as below them.
    const above = first.y - room.y
    const below = room.y + room.height - (second.y + second.height)
    expect(Math.abs(above - below)).toBeLessThanOrEqual(1)

    await expect(what).toHaveCSS('color', 'rgb(236, 236, 238)')
    await expect(what).toHaveCSS('font-size', '20px')
    await expect(what).toHaveCSS('line-height', '24px')
    await expect(what).toHaveCSS('text-align', 'center')
    await expect(help).toHaveCSS('color', 'rgb(169, 172, 179)')
    await expect(help).toHaveCSS('font-size', '16px')
    await expect(stage).toHaveCSS('background-color', 'rgb(29, 30, 33)')
    // Lines short enough to read: no line is longer than 32 times the size
    // of the text of the page, though the stage has room for more.
    expect(room.width - 48).toBeGreaterThan(512)
    expect(first.width).toBeLessThanOrEqual(512)
    expect(second.width).toBe(512)
  })

  test('keeps the words when a panel is closed, and gives them the room', async ({ page }) => {
    await page.goto('./')
    const { stage, what, help } = parts(page)
    const before = await box(stage)

    await page.getByRole('button', { name: 'Sections' }).click()
    await page.getByRole('button', { name: 'Details' }).click()

    const room = await box(stage)
    expect(room.width).toBeGreaterThan(before.width)
    expect(room).toMatchObject({ x: 0, width: 1280 })
    await expect(what).toBeVisible()
    await expect(help).toBeVisible()
    const first = await box(what)
    expect(Math.abs(first.x + first.width / 2 - 640)).toBeLessThanOrEqual(0.5)
  })
})

const NARROW_SCREENS = [
  { width: 320, height: 568 },
  { width: 390, height: 844 },
  { width: 568, height: 320 },
  { width: 768, height: 1024 },
]

for (const viewport of NARROW_SCREENS) {
  test.describe(`the globe stage without 3D pictures, ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('has both sentences whole inside the stage, and the page does not scroll', async ({
      page,
    }) => {
      await page.goto('./')
      const { stage, what, help } = parts(page)
      const room = await box(stage)

      // The words keep their distance from the edge of the stage.
      const within = {
        x: room.x + 24,
        y: room.y + 24,
        width: room.width - 48,
        height: room.height - 48,
      }
      expectInside(await box(what), within, 'the first sentence')
      expectInside(await box(help), within, 'the second sentence')
      expect(
        await page.evaluate(() => [
          document.documentElement.scrollWidth,
          document.documentElement.scrollHeight,
        ]),
      ).toEqual([viewport.width, viewport.height])
    })
  })
}

test.describe('the globe stage without 3D pictures, too low for the words', () => {
  test.use({ viewport: { width: 320, height: 240 } })

  test('starts the words at its top, and can be scrolled to their end', async ({ page }) => {
    await page.goto('./')
    const { stage, what, help } = parts(page)
    const room = await box(stage)
    const first = await box(what)
    const second = await box(help)

    // The words do not fit: this is the case the test is about.
    expect(first.height + second.height).toBeGreaterThan(room.height)
    expect(first.y).toBe(room.y + 24)
    expect(second.y + second.height).toBeGreaterThan(room.y + room.height)

    await page.mouse.move(room.x + room.width / 2, room.y + room.height / 2)
    await page.mouse.wheel(0, 2000)

    // The end of the words comes to rest 24 pixels above the bottom of the
    // stage, to the pixel: a stage scrolls by whole pixels.
    await expect
      .poll(async () => {
        const end = await box(help)
        return Math.round(end.y + end.height - (room.y + room.height))
      })
      .toBe(-24)
    expect(await page.evaluate(() => document.documentElement.scrollTop)).toBe(0)
  })
})
