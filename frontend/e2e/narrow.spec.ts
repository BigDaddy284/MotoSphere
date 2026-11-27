import type { Locator, Page } from '@playwright/test'
import { expect, test } from './fixtures'

// Below this width the screen is narrow: the panels lie over the globe stage.
const NARROW_BELOW = 900
// The widths the panels have when the screen has room for them.
const SECTIONS_WIDTH = 220
const DETAILS_WIDTH = 360
// The room the top bar leaves at its left and right edges.
const TOP_BAR_PADDING = 12
// The height of the top bar when it has one line.
const TOP_BAR_HEIGHT = 48
// On a narrow screen: the room between the things on the top bar's first line,
// the height of a line of information, the room between two pieces of
// information on one line, and the room under the last line (with the bar's
// own bottom line).
const TOP_BAR_GAP = 8
const INFO_LINE_HEIGHT = 21
const INFO_GAP = 16
const TOP_BAR_END = 9
const TAGLINE = 'The World of Motocross, Connected.'

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

function regions(page: Page) {
  const topBar = page.getByRole('banner')
  return {
    topBar,
    sectionsButton: topBar.getByRole('button', { name: 'Sections', exact: true }),
    detailsButton: topBar.getByRole('button', { name: 'Details', exact: true }),
    sections: page.getByRole('navigation', { name: 'Sections' }),
    stage: page.getByRole('main', { name: 'Globe' }),
    details: page.getByRole('complementary', { name: 'Details' }),
  }
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
const TOP_BAR_PIECES = {
  sectionsButton: ['the Sections button', 'header button[aria-controls="sections-panel"]'],
  name: ['the name', 'header h1'],
  status: ['the data status', 'header output'],
  date: ['the date', 'header output + time'],
  detailsButton: ['the Details button', 'header button[aria-controls="details-panel"]'],
} as const

type TopBarPieces = Record<keyof typeof TOP_BAR_PIECES, Piece>

/** Everything the top bar shows, measured once the data status has arrived. */
async function topBarPieces(page: Page): Promise<TopBarPieces> {
  await expect(page.getByRole('banner').getByText('Data updated')).toBeVisible()
  const measure = async ([name, selector]: readonly [string, string]): Promise<Piece> =>
    page.locator(selector).evaluate((element, called) => {
      const rect = element.getBoundingClientRect()
      return {
        name: called,
        left: rect.left,
        right: rect.right,
        top: rect.top,
        bottom: rect.bottom,
        lines: new Set([...element.getClientRects()].map((line) => Math.round(line.top))).size,
        cut: Math.max(0, element.scrollWidth - element.clientWidth),
      }
    }, name)
  return {
    sectionsButton: await measure(TOP_BAR_PIECES.sectionsButton),
    name: await measure(TOP_BAR_PIECES.name),
    status: await measure(TOP_BAR_PIECES.status),
    date: await measure(TOP_BAR_PIECES.date),
    detailsButton: await measure(TOP_BAR_PIECES.detailsButton),
  }
}

/** Which region is on top at a point of the screen. */
async function regionAt(page: Page, x: number, y: number): Promise<string | undefined> {
  return page.evaluate(
    ([px, py]) =>
      document.elementFromPoint(px, py)?.closest('header, nav, main, aside')?.tagName.toLowerCase(),
    [x, y] as const,
  )
}

const NARROW_SCREENS = [
  { width: 320, height: 568 },
  { width: 360, height: 740 },
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: NARROW_BELOW - 1, height: 700 },
]

for (const viewport of NARROW_SCREENS) {
  test.describe(`narrow screen, ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('the top bar and the globe stage each have the whole width', async ({ page }) => {
      await page.goto('./')
      const region = regions(page)
      const topBar = await box(region.topBar)
      const stage = await box(region.stage)

      expect(topBar).toMatchObject({ x: 0, y: 0, width: viewport.width })
      expect(stage).toEqual({
        x: 0,
        y: topBar.height,
        width: viewport.width,
        height: viewport.height - topBar.height,
      })
    })

    test('the page opens with both panels closed and the globe stage in view', async ({ page }) => {
      await page.goto('./')
      const region = regions(page)

      await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'false')
      await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'false')
      await expect(region.sections).toBeHidden()
      await expect(region.details).toBeHidden()
      expect(await box(region.stage)).toMatchObject({ x: 0, width: viewport.width })
      expect(await regionAt(page, viewport.width / 2, viewport.height / 2)).toBe('main')
    })

    test('the sections panel lies over the globe stage, from the left', async ({ page }) => {
      await page.goto('./')
      const region = regions(page)
      await region.sectionsButton.click()
      await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'true')
      const stage = await box(region.stage)
      const sections = await box(region.sections)

      expect(stage).toMatchObject({ x: 0, width: viewport.width })
      expect(sections).toEqual({
        x: 0,
        y: stage.y,
        width: Math.min(SECTIONS_WIDTH, viewport.width),
        height: stage.height,
      })
      expect(await regionAt(page, sections.width / 2, viewport.height / 2)).toBe('nav')
      await expect(region.sections.getByRole('button', { name: 'Explore' })).toBeVisible()
    })

    test('the details panel lies over the globe stage, from the right', async ({ page }) => {
      await page.goto('./')
      const region = regions(page)
      await region.detailsButton.click()
      await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'true')
      const stage = await box(region.stage)
      const details = await box(region.details)

      expect(stage).toMatchObject({ x: 0, width: viewport.width })
      const width = Math.min(DETAILS_WIDTH, viewport.width)
      expect(details).toEqual({
        x: viewport.width - width,
        y: stage.y,
        width,
        height: stage.height,
      })
      expect(await regionAt(page, viewport.width - width / 2, viewport.height / 2)).toBe('aside')
    })

    test('a button closes the panel it opened', async ({ page }) => {
      await page.goto('./')
      const region = regions(page)

      await region.sectionsButton.click()
      await expect(region.sections).toBeVisible()
      await region.sectionsButton.click()
      await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'false')
      await expect(region.sections).toBeHidden()

      await region.detailsButton.click()
      await expect(region.details).toBeVisible()
      await region.detailsButton.click()
      await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'false')
      await expect(region.details).toBeHidden()
      expect(await regionAt(page, viewport.width / 2, viewport.height / 2)).toBe('main')
    })

    test('opening one panel closes the other', async ({ page }) => {
      await page.goto('./')
      const region = regions(page)

      await region.sectionsButton.click()
      await expect(region.sections).toBeVisible()
      await region.detailsButton.click()
      await expect(region.details).toBeVisible()
      await expect(region.sections).toBeHidden()
      await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'false')

      await region.sectionsButton.click()
      await expect(region.sections).toBeVisible()
      await expect(region.details).toBeHidden()
      await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'false')
    })

    test('the panels are closed again when the page is loaded again', async ({ page }) => {
      await page.goto('./')
      const region = regions(page)
      await region.detailsButton.click()
      await expect(region.details).toBeVisible()

      await page.reload()

      await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'false')
      await expect(region.details).toBeHidden()
      await expect(region.sections).toBeHidden()
    })

    test('the page itself does not scroll', async ({ page }) => {
      await page.goto('./')
      const overflow = await page.evaluate(() => {
        const root = document.documentElement
        return {
          horizontal: root.scrollWidth - root.clientWidth,
          vertical: root.scrollHeight - root.clientHeight,
        }
      })
      expect(overflow).toEqual({ horizontal: 0, vertical: 0 })
    })

    test('everything in the top bar is whole and inside it', async ({ page }) => {
      await page.goto('./')
      const topBar = await box(regions(page).topBar)

      for (const piece of Object.values(await topBarPieces(page))) {
        expect(piece.left, `${piece.name}: left edge`).toBeGreaterThanOrEqual(TOP_BAR_PADDING)
        expect(piece.right, `${piece.name}: right edge`).toBeLessThanOrEqual(
          viewport.width - TOP_BAR_PADDING,
        )
        expect(piece.top, `${piece.name}: top edge`).toBeGreaterThanOrEqual(0)
        expect(piece.bottom, `${piece.name}: bottom edge`).toBeLessThanOrEqual(topBar.height)
        expect(piece.lines, `${piece.name}: lines`).toBe(1)
        expect(piece.cut, `${piece.name}: cut off`).toBe(0)
      }
    })

    test('nothing in the top bar lies over anything else in it', async ({ page }) => {
      await page.goto('./')
      const pieces = Object.values(await topBarPieces(page))

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
    })

    test('the tagline gives way', async ({ page }) => {
      await page.goto('./')
      await expect(page.getByRole('banner').getByRole('heading', { level: 1 })).toBeVisible()

      await expect(page.getByText(TAGLINE)).toBeHidden()
    })
  })
}

// From this width on, the name fits between the two buttons on one line.
const ONE_LINE_FROM = 360
// From this width on, the data status and the date fit on one line together.
const TWO_PIECES_FROM = 768

for (const viewport of NARROW_SCREENS.filter((screen) => screen.width >= ONE_LINE_FROM)) {
  test.describe(`narrow screen, ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('the top bar starts with one line: the name between the two buttons', async ({ page }) => {
      await page.goto('./')
      const { sectionsButton, name, detailsButton } = await topBarPieces(page)

      expect(sectionsButton.left).toBe(TOP_BAR_PADDING)
      expect(detailsButton.right).toBe(viewport.width - TOP_BAR_PADDING)
      expect(detailsButton.top).toBe(sectionsButton.top)
      expect(detailsButton.bottom).toBeLessThan(TOP_BAR_HEIGHT)
      expect(name.left - sectionsButton.right).toBeCloseTo(TOP_BAR_GAP, 3)
      expect(name.right).toBeLessThan(detailsButton.left)
      expect(name.top).toBeLessThan(sectionsButton.top)
      expect(name.bottom).toBeGreaterThan(sectionsButton.bottom)
    })

    test('the information starts right under that line, at the left edge', async ({ page }) => {
      await page.goto('./')
      const { status } = await topBarPieces(page)

      expect(status.top).toBe(TOP_BAR_HEIGHT)
      expect(status.left).toBe(TOP_BAR_PADDING)
      expect(status.bottom - status.top).toBe(INFO_LINE_HEIGHT)
    })

    if (viewport.width < TWO_PIECES_FROM) {
      test('the data status and the date each have a line', async ({ page }) => {
        await page.goto('./')
        const topBar = await box(regions(page).topBar)
        const { status, date } = await topBarPieces(page)

        expect(date.top).toBe(status.bottom)
        expect(date.left).toBe(TOP_BAR_PADDING)
        expect(date.bottom - date.top).toBe(INFO_LINE_HEIGHT)
        expect(topBar.height - date.bottom).toBe(TOP_BAR_END)
      })
    } else {
      test('the data status and the date share a line', async ({ page }) => {
        await page.goto('./')
        const topBar = await box(regions(page).topBar)
        const { status, date } = await topBarPieces(page)

        expect(date.top).toBe(status.top)
        expect(date.left - status.right).toBeCloseTo(INFO_GAP, 3)
        expect(topBar.height - date.bottom).toBe(TOP_BAR_END)
      })
    }
  })
}

test.describe(`the narrowest wide screen, ${NARROW_BELOW} pixels`, () => {
  test.use({ viewport: { width: NARROW_BELOW, height: 700 } })

  test('has the panels beside the globe stage', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)
    const sections = await box(region.sections)
    const stage = await box(region.stage)
    const details = await box(region.details)

    expect(sections).toMatchObject({ x: 0, width: SECTIONS_WIDTH })
    expect(stage).toMatchObject({
      x: SECTIONS_WIDTH,
      width: NARROW_BELOW - SECTIONS_WIDTH - DETAILS_WIDTH,
    })
    expect(details).toMatchObject({ x: NARROW_BELOW - DETAILS_WIDTH, width: DETAILS_WIDTH })
  })

  test('has a top bar of one line, with the tagline', async ({ page }) => {
    await page.goto('./')
    const topBar = await box(regions(page).topBar)
    const pieces = Object.values(await topBarPieces(page))

    expect(topBar.height).toBe(TOP_BAR_HEIGHT)
    for (const piece of pieces) {
      expect(piece.left, `${piece.name}: left edge`).toBeGreaterThanOrEqual(TOP_BAR_PADDING)
      expect(piece.right, `${piece.name}: right edge`).toBeLessThanOrEqual(
        NARROW_BELOW - TOP_BAR_PADDING,
      )
      expect(piece.top, `${piece.name}: top edge`).toBeGreaterThanOrEqual(0)
      expect(piece.bottom, `${piece.name}: bottom edge`).toBeLessThanOrEqual(TOP_BAR_HEIGHT)
      expect(piece.lines, `${piece.name}: lines`).toBe(1)
    }
    const order = pieces.toSorted((one, other) => one.left - other.left).map((piece) => piece.name)
    expect(order).toEqual([
      'the Sections button',
      'the name',
      'the data status',
      'the date',
      'the Details button',
    ])
    await expect(page.getByText(TAGLINE)).toBeVisible()
  })
})

test.describe('between a wide screen and a narrow one', () => {
  const WIDE = { width: 1366, height: 768 }
  const PHONE = { width: 390, height: 844 }
  test.use({ viewport: WIDE })

  test('the panels change at once when the width crosses the line', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)
    await expect(region.sections).toBeVisible()
    await expect(region.details).toBeVisible()

    await page.setViewportSize({ width: NARROW_BELOW - 1, height: 700 })
    await expect(region.sections).toBeHidden()
    await expect(region.details).toBeHidden()
    await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'false')
    await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'false')

    await page.setViewportSize({ width: NARROW_BELOW, height: 700 })
    await expect(region.sections).toBeVisible()
    await expect(region.details).toBeVisible()
    expect(await box(region.stage)).toMatchObject({
      x: SECTIONS_WIDTH,
      width: NARROW_BELOW - SECTIONS_WIDTH - DETAILS_WIDTH,
    })
  })

  test('what was chosen on the wide screen is still there afterwards', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)
    await region.detailsButton.click()
    await expect(region.details).toBeHidden()

    await page.setViewportSize(PHONE)
    await expect(region.sections).toBeHidden()
    await region.detailsButton.click()
    await expect(region.details).toBeVisible()
    await region.sectionsButton.click()
    await region.sectionsButton.click()
    await expect(region.sections).toBeHidden()

    await page.setViewportSize(WIDE)
    await expect(region.sections).toBeVisible()
    await expect(region.details).toBeHidden()
    expect(await box(region.stage)).toMatchObject({
      x: SECTIONS_WIDTH,
      width: WIDE.width - SECTIONS_WIDTH,
    })

    await page.reload()
    await expect(region.sections).toBeVisible()
    await expect(region.details).toBeHidden()
  })
})
