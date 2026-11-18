import type { Page } from '@playwright/test'
import { expect, test } from './fixtures'

// The height that follows the bars a phone's browser shows and hides.
const VISIBLE_HEIGHT = '100dvh'

/**
 * What the style sheets, as the browser received them, ask for a property of
 * an element: the value of the last rule that matches the element and sets it.
 */
async function asked(page: Page, selector: string, property: string): Promise<string> {
  return page.evaluate(
    ([chosen, name]) => {
      const element = document.querySelector(chosen)
      if (element === null) {
        throw new Error(`${chosen} is not on the page`)
      }
      let value = ''
      for (const sheet of document.styleSheets) {
        for (const rule of sheet.cssRules) {
          if (rule instanceof CSSStyleRule && element.matches(rule.selectorText)) {
            value = rule.style.getPropertyValue(name) || value
          }
        }
      }
      return value
    },
    [selector, property] as const,
  )
}

test('the layout asks for the height of the visible screen', async ({ page }) => {
  await page.goto('./')

  expect(await asked(page, '#root > div', 'height')).toBe(VISIBLE_HEIGHT)
})

test('the page asks for at least the height of the visible screen', async ({ page }) => {
  await page.goto('./')

  expect(await asked(page, 'body', 'min-height')).toBe(VISIBLE_HEIGHT)
})

for (const viewport of [
  { width: 390, height: 844 },
  { width: 844, height: 390 },
  { width: 1366, height: 768 },
]) {
  test.describe(`at ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('the layout is exactly as tall as the screen', async ({ page }) => {
      await page.goto('./')

      const layout = await page.locator('#root > div').boundingBox()
      expect(layout).toEqual({ x: 0, y: 0, width: viewport.width, height: viewport.height })
    })
  })
}
