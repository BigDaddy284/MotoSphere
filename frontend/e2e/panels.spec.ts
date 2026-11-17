import type { Page } from '@playwright/test'
import { expect, test } from './fixtures'
import { tabTo } from './keyboard'

const WIDTH = 1366
const HEIGHT = 768
// At this size the sections panel is 220 pixels wide and the details panel 360.
const SECTIONS_RIGHT = 220
const DETAILS_LEFT = 1006

function regions(page: Page) {
  const topBar = page.getByRole('banner')
  return {
    sectionsButton: topBar.getByRole('button', { name: 'Sections', exact: true }),
    detailsButton: topBar.getByRole('button', { name: 'Details', exact: true }),
    sections: page.getByRole('navigation', { name: 'Sections' }),
    details: page.getByRole('complementary', { name: 'Details' }),
    stage: page.getByRole('main', { name: 'Globe' }),
  }
}

/** The left and right edges of the globe stage, in pixels. */
async function stageEdges(page: Page): Promise<{ left: number; right: number }> {
  const stage = regions(page).stage
  const box = await stage.boundingBox()
  if (box === null) {
    throw new Error(`${stage.toString()} has no bounding box: it is not visible`)
  }
  return { left: box.x, right: box.x + box.width }
}

test.describe('side panels', () => {
  test.use({ viewport: { width: WIDTH, height: HEIGHT } })

  test('start open', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)

    await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'true')
    await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'true')
    await expect(region.sections).toBeVisible()
    await expect(region.details).toBeVisible()
    expect(await stageEdges(page)).toEqual({ left: SECTIONS_RIGHT, right: DETAILS_LEFT })
  })

  test('closing the sections panel gives its room to the globe stage', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)

    await region.sectionsButton.click()
    await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'false')
    await expect(region.sections).toBeHidden()
    await expect(region.details).toBeVisible()
    expect(await stageEdges(page)).toEqual({ left: 0, right: DETAILS_LEFT })

    await region.sectionsButton.click()
    await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'true')
    await expect(region.sections).toBeVisible()
    expect(await stageEdges(page)).toEqual({ left: SECTIONS_RIGHT, right: DETAILS_LEFT })
  })

  test('closing the details panel gives its room to the globe stage', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)

    await region.detailsButton.click()
    await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'false')
    await expect(region.details).toBeHidden()
    await expect(region.sections).toBeVisible()
    expect(await stageEdges(page)).toEqual({ left: SECTIONS_RIGHT, right: WIDTH })

    await region.detailsButton.click()
    await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'true')
    await expect(region.details).toBeVisible()
    expect(await stageEdges(page)).toEqual({ left: SECTIONS_RIGHT, right: DETAILS_LEFT })
  })

  test('with both panels closed the globe stage is as wide as the screen', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)

    await region.sectionsButton.click()
    await region.detailsButton.click()
    await expect(region.sections).toBeHidden()
    await expect(region.details).toBeHidden()

    expect(await stageEdges(page)).toEqual({ left: 0, right: WIDTH })
    const overflow = await page.evaluate(() => {
      const root = document.documentElement
      return {
        horizontal: root.scrollWidth - root.clientWidth,
        vertical: root.scrollHeight - root.clientHeight,
      }
    })
    expect(overflow).toEqual({ horizontal: 0, vertical: 0 })
    await expect(region.sectionsButton).toBeVisible()
    await expect(region.detailsButton).toBeVisible()
  })

  test('can be closed and opened with the keyboard alone', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)
    // A key pressed before the top bar is drawn would be lost.
    await expect(region.sectionsButton).toBeVisible()

    await tabTo(page, region.sectionsButton)
    await expect(region.sectionsButton).toHaveCSS('outline-style', 'solid')
    await expect(region.sectionsButton).toHaveCSS('outline-color', 'rgb(94, 168, 255)')
    await page.keyboard.press('Enter')
    await expect(region.sections).toBeHidden()
    await page.keyboard.press('Space')
    await expect(region.sections).toBeVisible()

    await tabTo(page, region.detailsButton)
    await page.keyboard.press('Space')
    await expect(region.details).toBeHidden()
    await page.keyboard.press('Enter')
    await expect(region.details).toBeVisible()
  })

  test('a closed panel takes its sections out of the keyboard order', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)

    await region.sectionsButton.click()
    await expect(region.sections).toBeHidden()
    await page.keyboard.press('Tab')

    await expect(region.detailsButton).toBeFocused()
    await expect(page.getByRole('button', { name: 'Explore' })).toHaveCount(0)
  })

  test('stay as the user left them when the page is reloaded', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)

    await region.detailsButton.click()
    await expect(region.details).toBeHidden()
    await page.reload()

    await expect(region.detailsButton).toHaveAttribute('aria-expanded', 'false')
    await expect(region.details).toBeHidden()
    await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'true')
    await expect(region.sections).toBeVisible()
    expect(await stageEdges(page)).toEqual({ left: SECTIONS_RIGHT, right: WIDTH })
  })

  test('start open again in a new tab', async ({ page, context }) => {
    await page.goto('./')
    await regions(page).sectionsButton.click()
    await expect(regions(page).sections).toBeHidden()

    const newTab = await context.newPage()
    await newTab.goto('./')
    const region = regions(newTab)

    await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'true')
    await expect(region.sections).toBeVisible()
  })

  test('the buttons show whether their panel is open', async ({ page }) => {
    await page.goto('./')
    const region = regions(page)

    await expect(region.sectionsButton).toHaveCSS('background-color', 'rgb(53, 55, 60)')
    await expect(region.sectionsButton).toHaveCSS('color', 'rgb(236, 236, 238)')

    await region.sectionsButton.click()
    await expect(region.sectionsButton).toHaveAttribute('aria-expanded', 'false')
    // Move the mouse off the button so the hover style does not apply.
    await page.mouse.move(WIDTH / 2, 400)

    await expect(region.sectionsButton).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
    await expect(region.sectionsButton).toHaveCSS('color', 'rgb(169, 172, 179)')
    await expect(region.detailsButton).toHaveCSS('background-color', 'rgb(53, 55, 60)')
  })
})
