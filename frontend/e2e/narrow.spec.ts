import type { Locator, Page } from '@playwright/test'
import { expect, test } from './fixtures'

// Below this width the screen is narrow: the panels lie over the globe stage.
const NARROW_BELOW = 900
// The widths the panels have when the screen has room for them.
const SECTIONS_WIDTH = 220
const DETAILS_WIDTH = 360

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
  return {
    topBar: page.getByRole('banner'),
    sections: page.getByRole('navigation', { name: 'Sections' }),
    stage: page.getByRole('main', { name: 'Globe' }),
    details: page.getByRole('complementary', { name: 'Details' }),
  }
}

/** Opens the page as a visitor who closed these side panels earlier in the session. */
async function openWithClosed(page: Page, ...panels: ('sections' | 'details')[]): Promise<void> {
  await page.addInitScript((names) => {
    for (const name of names) {
      window.sessionStorage.setItem(`motosphere.panel.${name}`, 'closed')
    }
  }, panels)
  await page.goto('./')
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

    test('the globe stage keeps the whole width when the panels are closed', async ({ page }) => {
      await openWithClosed(page, 'sections', 'details')
      const region = regions(page)
      await expect(region.sections).toBeHidden()
      await expect(region.details).toBeHidden()

      expect(await box(region.stage)).toMatchObject({ x: 0, width: viewport.width })
      expect(await regionAt(page, viewport.width / 2, viewport.height / 2)).toBe('main')
    })

    test('the sections panel lies over the globe stage, from the left', async ({ page }) => {
      await openWithClosed(page, 'details')
      const region = regions(page)
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
      await openWithClosed(page, 'sections')
      const region = regions(page)
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
})
