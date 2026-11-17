import type { Locator, Page } from '@playwright/test'

const MAX_PRESSES = 20

/**
 * Presses Tab, as a keyboard user would, until the element has focus. Fails
 * if the element cannot be reached that way.
 */
export async function tabTo(page: Page, target: Locator): Promise<void> {
  for (let presses = 0; presses < MAX_PRESSES; presses += 1) {
    await page.keyboard.press('Tab')
    if (await target.evaluate((element) => element === document.activeElement)) {
      return
    }
  }
  throw new Error(`${target.toString()} was not reached with ${MAX_PRESSES} presses of Tab`)
}
