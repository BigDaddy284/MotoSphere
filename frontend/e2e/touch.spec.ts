import type { Page } from '@playwright/test'
import { expect, test } from './fixtures'

// The least height and width of a control under a finger, in pixels.
const TOUCH_TARGET = 44
// The heights the controls have with a mouse.
const BUTTON_HEIGHT = 31
const SECTION_HEIGHT = 40
// The height of the top bar when it has one line.
const TOP_BAR_HEIGHT = 48

const PHONE = { width: 390, height: 844 }
const DESKTOP = { width: 1366, height: 768 }

interface Control {
  name: string
  top: number
  bottom: number
  width: number
  height: number
}

/** Every control of the layout, with its sections panel open. */
async function controls(page: Page): Promise<{ buttons: Control[]; sections: Control[] }> {
  const topBar = page.getByRole('banner')
  const sectionsButton = topBar.getByRole('button', { name: 'Sections', exact: true })
  if ((await sectionsButton.getAttribute('aria-expanded')) === 'false') {
    await sectionsButton.click()
  }
  const sections = page.getByRole('navigation', { name: 'Sections' })
  await expect(sections.getByRole('button')).toHaveCount(9)
  const measure = (selector: string) =>
    page.locator(selector).evaluateAll((elements) =>
      elements.map((element) => {
        const rect = element.getBoundingClientRect()
        return {
          name: element.textContent,
          top: rect.top,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height,
        }
      }),
    )
  return { buttons: await measure('header button'), sections: await measure('nav button') }
}

for (const viewport of [PHONE, DESKTOP]) {
  test.describe(`touch screen, ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport, hasTouch: true })

    test('the buttons in the top bar are tall enough for a finger', async ({ page }) => {
      await page.goto('./')
      const { buttons } = await controls(page)

      expect(buttons.map((button) => button.name)).toEqual(['Sections', 'Details'])
      for (const button of buttons) {
        expect(button.height, button.name).toBe(TOUCH_TARGET)
        expect(button.width, `${button.name}: width`).toBeGreaterThanOrEqual(TOUCH_TARGET)
        expect(button.top, `${button.name}: top edge`).toBeGreaterThanOrEqual(0)
        expect(button.bottom, `${button.name}: bottom edge`).toBeLessThanOrEqual(TOP_BAR_HEIGHT)
      }
    })

    test('every section is tall enough for a finger, one right under the other', async ({
      page,
    }) => {
      await page.goto('./')
      const { sections } = await controls(page)

      expect(sections).toHaveLength(9)
      for (const [index, section] of sections.entries()) {
        expect(section.height, section.name).toBe(TOUCH_TARGET)
        expect(section.width, `${section.name}: width`).toBeGreaterThanOrEqual(TOUCH_TARGET)
        const next = sections[index + 1]
        if (next !== undefined) {
          expect(next.top, `${next.name} follows ${section.name}`).toBe(section.bottom)
        }
      }
    })
  })

  test.describe(`mouse, ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport, hasTouch: false })

    test('the controls keep their sizes', async ({ page }) => {
      await page.goto('./')
      const { buttons, sections } = await controls(page)

      expect(buttons.map((button) => button.height)).toEqual([BUTTON_HEIGHT, BUTTON_HEIGHT])
      expect(sections.map((section) => section.height)).toEqual(
        Array.from({ length: 9 }, () => SECTION_HEIGHT),
      )
    })
  })
}

test.describe('touch screen, the top bar', () => {
  test.use({ hasTouch: true })

  test('keeps its height of one line on a wide screen', async ({ page }) => {
    await page.setViewportSize(DESKTOP)
    await page.goto('./')

    const topBar = await page.getByRole('banner').boundingBox()
    expect(topBar?.height).toBe(TOP_BAR_HEIGHT)
  })

  test('is no taller on a phone than with a mouse', async ({ page, browser }) => {
    await page.setViewportSize(PHONE)
    await page.goto('./')
    await expect(page.getByRole('banner').getByText('Data updated')).toBeVisible()
    const withTouch = await page.getByRole('banner').boundingBox()

    const context = await browser.newContext({ viewport: PHONE, hasTouch: false })
    const mousePage = await context.newPage()
    await mousePage.goto(page.url())
    await expect(mousePage.getByRole('banner').getByText('Data updated')).toBeVisible()
    const withMouse = await mousePage.getByRole('banner').boundingBox()
    await context.close()

    expect(withTouch?.height).toBeGreaterThan(TOP_BAR_HEIGHT)
    expect(withTouch?.height).toBe(withMouse?.height)
  })
})
