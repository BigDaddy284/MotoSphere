import type { Locator, Page } from '@playwright/test'
import { expect, test } from './fixtures'

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

const VIEWPORTS = [
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
]

for (const viewport of VIEWPORTS) {
  test.describe(`layout at ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('the four regions fill the screen without overlapping', async ({ page }) => {
      await page.goto('/')
      const region = regions(page)
      const topBar = await box(region.topBar)
      const sections = await box(region.sections)
      const stage = await box(region.stage)
      const details = await box(region.details)

      expect(topBar.x).toBe(0)
      expect(topBar.y).toBe(0)
      expect(topBar.width).toBe(viewport.width)

      const topBarBottom = topBar.y + topBar.height
      for (const panel of [sections, stage, details]) {
        expect(panel.y).toBe(topBarBottom)
        expect(panel.y + panel.height).toBe(viewport.height)
      }

      expect(sections.x).toBe(0)
      expect(stage.x).toBe(sections.x + sections.width)
      expect(details.x).toBe(stage.x + stage.width)
      expect(details.x + details.width).toBe(viewport.width)
    })

    test('the globe stage is the largest region', async ({ page }) => {
      await page.goto('/')
      const region = regions(page)
      const sections = await box(region.sections)
      const stage = await box(region.stage)
      const details = await box(region.details)

      expect(stage.width).toBeGreaterThan(viewport.width / 2)
      expect(stage.width).toBeGreaterThan(sections.width + details.width)
    })

    test('the page itself does not scroll', async ({ page }) => {
      await page.goto('/')
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

test('the regions use the Graphite surfaces', async ({ page }) => {
  await page.goto('/')
  const region = regions(page)
  await expect(region.topBar).toHaveCSS('background-color', 'rgb(27, 28, 31)')
  await expect(region.sections).toHaveCSS('background-color', 'rgb(34, 35, 39)')
  await expect(region.stage).toHaveCSS('background-color', 'rgb(29, 30, 33)')
  await expect(region.details).toHaveCSS('background-color', 'rgb(34, 35, 39)')
})
