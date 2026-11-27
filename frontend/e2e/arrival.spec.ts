import type { Page, Route } from '@playwright/test'
import { SITE_PATH } from '../site.ts'
import { manifestUrl } from '../src/data/manifest.ts'
import { expect, test } from './fixtures'

/**
 * The top bar when the data arrives. The page is drawn at once and says
 * "Loading data…"; the data status changes a moment later, to longer words.
 * Nothing on the page may move when it does: the top bar is as tall before as
 * afterwards, at every width, and so the globe stage stays where it is.
 */

const MANIFEST = `**${manifestUrl(SITE_PATH)}`

// Below this width the screen is narrow, and the information has lines of its
// own under the first line of the top bar.
const NARROW_BELOW = 900
// On a narrow screen, from this width on, the two pieces of information share
// a line. Below it each has a line of its own.
const ONE_LINE_OF_INFORMATION_FROM = 640
// From this width on, the name fits between the two buttons on one line, with
// every font. Below it the height of the top bar is not held to a number.
const ONE_LINE_FROM = 360
// The room the top bar leaves at its left and right edges.
const TOP_BAR_PADDING = 12
// The height of the first line of the top bar, of a line of information, and
// of the room under the last line (with the bar's own bottom line).
const TOP_BAR_HEIGHT = 48
const INFO_LINE_HEIGHT = 21
const TOP_BAR_END = 9
// The room between two pieces of information on one line.
const INFO_GAP = 16

/** How tall the top bar is at a width, whatever the data status says. */
function heightAt(width: number): number {
  if (width >= NARROW_BELOW) {
    return TOP_BAR_HEIGHT
  }
  const lines = width >= ONE_LINE_OF_INFORMATION_FROM ? 1 : 2
  return TOP_BAR_HEIGHT + lines * INFO_LINE_HEIGHT + TOP_BAR_END
}

interface Piece {
  /** What it is called when a test fails. */
  name: string
  left: number
  right: number
  top: number
  bottom: number
  /** How many lines it is drawn on. */
  lines: number
  /** How much of it is cut off at its own right edge, in pixels. */
  cut: number
}

// Everything the top bar shows on any screen, from left to right on a wide one.
const PIECES = [
  ['the Sections button', 'header button[aria-controls="sections-panel"]'],
  ['the name', 'header h1'],
  ['the data status', 'header output'],
  ['the date', 'header output + time'],
  ['the Details button', 'header button[aria-controls="details-panel"]'],
] as const
const REGIONS = [
  ['the top bar', 'header'],
  ['the globe stage', 'main'],
] as const

interface Measured {
  /** The top bar and the globe stage: left, top, width and height. */
  topBar: number[]
  stage: number[]
  pieces: Piece[]
  status: Piece
  date: Piece
}

/** Where something is, as its left edge, its top edge, its width and its height. */
function box({ left, right, top, bottom }: Piece): number[] {
  return [left, top, right - left, bottom - top]
}

/** The top bar, the globe stage and everything the top bar shows, as drawn now. */
async function measure(page: Page): Promise<Measured> {
  const all = await page.evaluate(
    (selectors) =>
      selectors.map(([name, selector]) => {
        const element = document.querySelector(selector)
        if (element === null) {
          throw new Error(`${name} is not on the page`)
        }
        const rect = element.getBoundingClientRect()
        return {
          name,
          left: rect.left,
          right: rect.right,
          top: rect.top,
          bottom: rect.bottom,
          lines: new Set([...element.getClientRects()].map((line) => Math.round(line.top))).size,
          cut: Math.max(0, element.scrollWidth - element.clientWidth),
        }
      }),
    [...REGIONS, ...PIECES],
  )
  const one = (name: string): Piece => {
    const found = all.find((candidate) => candidate.name === name)
    if (found === undefined) {
      throw new Error(`${name} was not measured`)
    }
    return found
  }
  return {
    topBar: box(one('the top bar')),
    stage: box(one('the globe stage')),
    pieces: PIECES.map(([name]) => one(name)),
    status: one('the data status'),
    date: one('the date'),
  }
}

/** Fails unless every piece is whole, inside the top bar and apart from every other. */
function expectWholeAndApart({ topBar, pieces }: Measured, width: number): void {
  for (const piece of pieces) {
    expect(piece.left, `${piece.name}: left edge`).toBeGreaterThanOrEqual(TOP_BAR_PADDING)
    expect(piece.right, `${piece.name}: right edge`).toBeLessThanOrEqual(width - TOP_BAR_PADDING)
    expect(piece.top, `${piece.name}: top edge`).toBeGreaterThanOrEqual(0)
    expect(piece.bottom, `${piece.name}: bottom edge`).toBeLessThanOrEqual(topBar[3] ?? 0)
    expect(piece.lines, `${piece.name}: lines`).toBe(1)
    expect(piece.cut, `${piece.name}: cut off`).toBe(0)
  }
  for (const [index, one] of pieces.entries()) {
    for (const other of pieces.slice(index + 1)) {
      const apart =
        one.right <= other.left ||
        other.right <= one.left ||
        one.bottom <= other.top ||
        other.bottom <= one.top
      expect(apart, `${one.name} and ${other.name} are apart`).toBe(true)
    }
  }
}

function dataStatus(page: Page) {
  return page.getByRole('banner').getByRole('status')
}

/**
 * Opens the page with the data held back, and waits until the page has asked
 * for it and says that it is loading. Gives what lets the data through.
 */
async function openWithTheDataHeldBack(page: Page): Promise<() => Promise<void>> {
  const held: Route[] = []
  await page.route(MANIFEST, (route) => {
    held.push(route)
  })
  await page.goto('./')
  await expect.poll(() => held.length, 'requests for the manifest, held back').toBe(1)
  await expect(dataStatus(page)).toHaveText('Loading data…')
  return async () => {
    await held[0]?.continue()
    await expect(dataStatus(page)).toHaveText(/^Data updated /)
  }
}

// What the page says when the data could not be loaded, each with an answer
// of the server that makes it say so.
const WITHOUT_THE_DATA = [
  {
    says: 'Data unavailable',
    answer: { contentType: 'text/html', body: '<!doctype html><title>MotoSphere</title>' },
  },
  {
    says: 'Reload the page to see the data',
    answer: { json: { format_version: 2, layout: 'something new' } },
  },
]

const SCREENS = [
  { width: 320, height: 568 },
  { width: 360, height: 740 },
  { width: 390, height: 844 },
  { width: ONE_LINE_OF_INFORMATION_FROM - 1, height: 360 },
  { width: ONE_LINE_OF_INFORMATION_FROM, height: 360 },
  { width: 844, height: 390 },
  { width: NARROW_BELOW - 1, height: 700 },
  { width: 1366, height: 768 },
]

for (const viewport of SCREENS) {
  test.describe(`when the data arrives, ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('the top bar keeps its height and the globe stage does not move', async ({ page }) => {
      const letTheDataThrough = await openWithTheDataHeldBack(page)
      const loading = await measure(page)

      await letTheDataThrough()
      const arrived = await measure(page)

      expect(arrived.topBar).toEqual(loading.topBar)
      expect(arrived.stage).toEqual(loading.stage)
      expect(arrived.status.top).toBe(loading.status.top)
      expect(arrived.date.top).toBe(loading.date.top)
      // The stage lies right under the top bar and reaches the end of the screen.
      const height = loading.topBar[3] ?? 0
      expect(loading.topBar).toEqual([0, 0, viewport.width, height])
      expect(loading.stage[1]).toBe(height)
      expect(loading.stage[3]).toBe(viewport.height - height)
      if (viewport.width >= ONE_LINE_FROM) {
        expect(height).toBe(heightAt(viewport.width))
      }
    })

    test('everything in the top bar is whole and apart, before and after', async ({ page }) => {
      const letTheDataThrough = await openWithTheDataHeldBack(page)

      expectWholeAndApart(await measure(page), viewport.width)

      await letTheDataThrough()
      expectWholeAndApart(await measure(page), viewport.width)
    })

    for (const { says, answer } of WITHOUT_THE_DATA) {
      test(`the top bar is as tall when it says "${says}"`, async ({ page }) => {
        await page.goto('./')
        await expect(dataStatus(page)).toHaveText(/^Data updated /)
        const withTheData = await measure(page)

        await page.route(MANIFEST, (route) => route.fulfill(answer))
        await page.reload()
        await expect(dataStatus(page)).toHaveText(says)
        const without = await measure(page)

        expect(without.topBar).toEqual(withTheData.topBar)
        expect(without.stage).toEqual(withTheData.stage)
        expectWholeAndApart(without, viewport.width)
      })
    }
  })
}

test.describe(`one pixel below ${ONE_LINE_OF_INFORMATION_FROM}`, () => {
  test.use({ viewport: { width: ONE_LINE_OF_INFORMATION_FROM - 1, height: 700 } })

  test('each piece of information has a line of its own, before and after', async ({ page }) => {
    const letTheDataThrough = await openWithTheDataHeldBack(page)
    const loading = await measure(page)
    await letTheDataThrough()
    const arrived = await measure(page)

    for (const { status, date } of [loading, arrived]) {
      expect(status.top).toBe(TOP_BAR_HEIGHT)
      expect(status.left).toBe(TOP_BAR_PADDING)
      expect(status.bottom - status.top).toBe(INFO_LINE_HEIGHT)
      expect(date.top).toBe(status.bottom)
      expect(date.left).toBe(TOP_BAR_PADDING)
      expect(date.bottom - date.top).toBe(INFO_LINE_HEIGHT)
    }
  })
})

test.describe(`at ${ONE_LINE_OF_INFORMATION_FROM} pixels`, () => {
  test.use({ viewport: { width: ONE_LINE_OF_INFORMATION_FROM, height: 700 } })

  test('the two pieces of information share a line, before and after', async ({ page }) => {
    const letTheDataThrough = await openWithTheDataHeldBack(page)
    const loading = await measure(page)
    await letTheDataThrough()
    const arrived = await measure(page)

    for (const { status, date } of [loading, arrived]) {
      expect(status.top).toBe(TOP_BAR_HEIGHT)
      expect(status.left).toBe(TOP_BAR_PADDING)
      expect(status.bottom - status.top).toBe(INFO_LINE_HEIGHT)
      expect(date.top).toBe(status.top)
      expect(date.left - status.right).toBeCloseTo(INFO_GAP, 3)
      expect(date.bottom - date.top).toBe(INFO_LINE_HEIGHT)
    }
  })
})

/**
 * Opens the page on a day whose date is a long one, with data of that day,
 * and sets the letters of the two pieces of information far apart.
 */
async function openWithLongWords(page: Page, apart = '0.6em'): Promise<void> {
  await page.clock.setFixedTime(new Date('2026-09-30T12:00:00Z'))
  await page.route(MANIFEST, (route) =>
    route.fulfill({
      json: {
        format_version: 1,
        generated_at: '2026-09-30T08:00:00Z',
        application_version: '0.1.0',
        counts: {},
      },
    }),
  )
  await page.goto('./')
  await expect(dataStatus(page)).toHaveText('Data updated 30 September 2026')
  await expect(page.getByRole('banner').locator('output + time')).toHaveText(
    /^Wednesday,? 30 September 2026$/,
  )
  await page.addStyleTag({
    content: `header output, header output + time { letter-spacing: ${apart}; }`,
  })
}

// Words can be longer than any line the layout was measured for: another
// language, another font, larger letters. Here they are made so.
test.describe('when the words are too long for the line', () => {
  test.use({ locale: 'en-GB', timezoneId: 'Europe/London' })

  test.describe('on a line the two pieces share', () => {
    const viewport = { width: 700, height: 700 }
    test.use({ viewport })

    test('the data status stays whole and the date gives way', async ({ page }) => {
      await openWithLongWords(page)
      const { topBar, stage, status, date } = await measure(page)

      expect(topBar).toEqual([0, 0, viewport.width, heightAt(viewport.width)])
      expect(stage[1]).toBe(heightAt(viewport.width))
      expect(status.cut).toBe(0)
      expect(status.lines).toBe(1)
      expect(date.top).toBe(status.top)
      expect(date.left - status.right).toBeCloseTo(INFO_GAP, 3)
      expect(date.lines).toBe(1)
      expect(date.cut).toBeGreaterThan(0)
      expect(date.right).toBe(viewport.width - TOP_BAR_PADDING)
      await expect(page.getByRole('banner').locator('output + time')).toHaveCSS(
        'text-overflow',
        'ellipsis',
      )
    })
  })

  test.describe('on a line the data status is too long for by itself', () => {
    const viewport = { width: 700, height: 700 }
    test.use({ viewport })

    test('the data status ends at the edge of the line', async ({ page }) => {
      await openWithLongWords(page, '1.5em')
      const { topBar, stage, status } = await measure(page)

      expect(topBar).toEqual([0, 0, viewport.width, heightAt(viewport.width)])
      expect(stage[1]).toBe(heightAt(viewport.width))
      expect(status.left).toBe(TOP_BAR_PADDING)
      expect(status.right).toBe(viewport.width - TOP_BAR_PADDING)
      expect(status.lines).toBe(1)
      expect(status.cut).toBeGreaterThan(0)
    })
  })

  test.describe('where each piece has a line of its own', () => {
    const viewport = { width: 360, height: 740 }
    test.use({ viewport })

    test('each piece ends at the edge of its line', async ({ page }) => {
      await openWithLongWords(page)
      const { topBar, stage, status, date } = await measure(page)

      expect(topBar).toEqual([0, 0, viewport.width, heightAt(viewport.width)])
      expect(stage[1]).toBe(heightAt(viewport.width))
      expect(date.top).toBe(status.bottom)
      for (const piece of [status, date]) {
        expect(piece.left, `${piece.name}: left edge`).toBe(TOP_BAR_PADDING)
        expect(piece.right, `${piece.name}: right edge`).toBe(viewport.width - TOP_BAR_PADDING)
        expect(piece.lines, `${piece.name}: lines`).toBe(1)
        expect(piece.cut, `${piece.name}: cut off`).toBeGreaterThan(0)
      }
      await expect(dataStatus(page)).toHaveCSS('text-overflow', 'ellipsis')
    })
  })
})
