import type { Page } from '@playwright/test'
import { expect, test } from './fixtures'

function currentDate(page: Page) {
  // The data status has a time element of its own, inside an output element.
  return page.getByRole('banner').locator('time:not(output time)')
}

test.describe('current date', () => {
  test.describe('for a British user in London', () => {
    test.use({ locale: 'en-GB', timezoneId: 'Europe/London' })

    test("shows today's date in the top bar", async ({ page }) => {
      await page.clock.setFixedTime(new Date('2026-11-17T12:00:00Z'))
      await page.goto('/')

      await expect(currentDate(page)).toHaveText(/^Tuesday,? 17 November 2026$/)
      await expect(currentDate(page)).toHaveAttribute('datetime', '2026-11-17')
    })

    test('changes at midnight without a reload', async ({ page }) => {
      await page.clock.install({ time: new Date('2026-11-17T23:59:50Z') })
      await page.goto('/')
      await expect(currentDate(page)).toHaveAttribute('datetime', '2026-11-17')

      await page.clock.fastForward(15_000)

      await expect(currentDate(page)).toHaveAttribute('datetime', '2026-11-18')
      await expect(currentDate(page)).toHaveText(/^Wednesday,? 18 November 2026$/)
    })

    test('sits between the tagline and the Details button, in the quiet text colour', async ({
      page,
    }) => {
      await page.setViewportSize({ width: 1366, height: 768 })
      await page.clock.setFixedTime(new Date('2026-11-17T12:00:00Z'))
      await page.goto('/')

      const date = currentDate(page)
      await expect(date).toBeInViewport({ ratio: 1 })
      await expect(date).toHaveCSS('color', 'rgb(169, 172, 179)')
      await expect(date).toHaveCSS('font-size', '14px')
      const tagline = await page.getByText('The World of Motocross, Connected.').boundingBox()
      const dateBox = await date.boundingBox()
      const details = await page
        .getByRole('banner')
        .getByRole('button', { name: 'Details', exact: true })
        .boundingBox()
      if (tagline === null || dateBox === null || details === null) {
        throw new Error('The tagline, the date or the Details button is not visible.')
      }
      expect(dateBox.x).toBeGreaterThan(tagline.x + tagline.width)
      expect(dateBox.x + dateBox.width).toBeLessThan(details.x)
      // The date and the button are pushed to the right-hand end of the bar.
      expect(details.x - (dateBox.x + dateBox.width)).toBeLessThanOrEqual(16)
      expect(1366 - (details.x + details.width)).toBeLessThanOrEqual(16)
    })
  })

  test.describe('for an American user in Los Angeles', () => {
    test.use({ locale: 'en-US', timezoneId: 'America/Los_Angeles' })

    test('shows the day where the user is, in the American form', async ({ page }) => {
      // 02:00 in London on the 17th is still the evening of the 16th in Los Angeles.
      await page.clock.setFixedTime(new Date('2026-11-17T02:00:00Z'))
      await page.goto('/')

      await expect(currentDate(page)).toHaveText('Monday, November 16, 2026')
      await expect(currentDate(page)).toHaveAttribute('datetime', '2026-11-16')
    })
  })

  test.describe('for a German user in Tokyo', () => {
    test.use({ locale: 'de-DE', timezoneId: 'Asia/Tokyo' })

    test('shows the day where the user is, in German', async ({ page }) => {
      // 20:00 in London on the 17th is already the morning of the 18th in Tokyo.
      await page.clock.setFixedTime(new Date('2026-11-17T20:00:00Z'))
      await page.goto('/')

      await expect(currentDate(page)).toHaveText('Mittwoch, 18. November 2026')
      await expect(currentDate(page)).toHaveAttribute('datetime', '2026-11-18')
    })
  })
})
