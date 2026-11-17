import type { Page } from '@playwright/test'
import { expect, test } from './fixtures'
import { tabTo } from './keyboard'

const LABELS = [
  'Explore',
  'Events',
  'Tracks',
  'Championships',
  'Riders',
  'Teams',
  'Results',
  'News',
  'Statistics',
]

function panel(page: Page) {
  return page.getByRole('navigation', { name: 'Sections' })
}

function section(page: Page, name: string) {
  return panel(page).getByRole('button', { name, exact: true })
}

/** Checks that `name` is the only section marked as current. */
async function expectOnlyCurrent(page: Page, name: string) {
  await expect(panel(page).locator('[aria-current]')).toHaveText([name])
  await expect(section(page, name)).toHaveAttribute('aria-current', 'page')
}

test.describe('section navigation', () => {
  test('lists the nine sections and starts in Explore', async ({ page }) => {
    await page.goto('./')

    await expect(panel(page).getByRole('button')).toHaveText(LABELS)
    await expectOnlyCurrent(page, 'Explore')
  })

  test('moves to the section that is clicked and shows it in the selection style', async ({
    page,
  }) => {
    await page.goto('./')

    await section(page, 'Tracks').click()

    await expectOnlyCurrent(page, 'Tracks')
    const tracks = section(page, 'Tracks')
    await expect(tracks).toHaveCSS('background-color', 'rgb(47, 74, 110)')
    await expect(tracks).toHaveCSS('color', 'rgb(236, 236, 238)')
    await expect(tracks).toHaveCSS('border-left-color', 'rgb(94, 168, 255)')
    const explore = section(page, 'Explore')
    await expect(explore).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
    await expect(explore).toHaveCSS('color', 'rgb(169, 172, 179)')
    await expect(explore).toHaveCSS('border-left-color', 'rgba(0, 0, 0, 0)')
  })

  test('can be used with the keyboard alone, with a visible focus ring', async ({ page }) => {
    await page.goto('./')
    // A key pressed before the list is drawn would be lost.
    await expect(section(page, 'Explore')).toBeVisible()

    const explore = section(page, 'Explore')
    await tabTo(page, explore)
    await expect(explore).toBeFocused()
    await expect(explore).toHaveCSS('outline-style', 'solid')
    await expect(explore).toHaveCSS('outline-width', '2px')
    await expect(explore).toHaveCSS('outline-color', 'rgb(94, 168, 255)')

    await page.keyboard.press('Tab')
    await expect(section(page, 'Events')).toBeFocused()
    await page.keyboard.press('Enter')
    await expectOnlyCurrent(page, 'Events')

    await page.keyboard.press('Tab')
    await expect(section(page, 'Tracks')).toBeFocused()
    await page.keyboard.press('Space')
    await expectOnlyCurrent(page, 'Tracks')
  })

  test('shows a hover style on a section that is not current', async ({ page }) => {
    await page.goto('./')

    const riders = section(page, 'Riders')
    await riders.hover()

    await expect(riders).toHaveCSS('background-color', 'rgb(53, 55, 60)')
    await expect(riders).toHaveCSS('color', 'rgb(236, 236, 238)')
    await expectOnlyCurrent(page, 'Explore')
  })

  test.describe('at 1366×768', () => {
    test.use({ viewport: { width: 1366, height: 768 } })

    test('fits every section in the panel without scrolling', async ({ page }) => {
      await page.goto('./')
      await expect(panel(page).getByRole('button')).toHaveCount(9)

      const overflow = await panel(page).evaluate((element) => ({
        x: element.scrollWidth - element.clientWidth,
        y: element.scrollHeight - element.clientHeight,
      }))
      expect(overflow).toEqual({ x: 0, y: 0 })
      for (const label of LABELS) {
        await expect(section(page, label)).toBeInViewport({ ratio: 1 })
      }
    })
  })
})
