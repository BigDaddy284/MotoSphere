import type { APIRequestContext, Page } from '@playwright/test'
import { SITE_PATH } from '../site.ts'
import { manifestUrl } from '../src/data/manifest.ts'
import { expect, test } from './fixtures'

/**
 * The data status in the top bar. The built site under test carries data
 * that the real export command wrote for this run (see `data.spec.ts`), and
 * the tests of the normal case read that data. Only the tests of what can go
 * wrong replace the server's answer.
 */

const MANIFEST = `**${manifestUrl(SITE_PATH)}`

function dataStatus(page: Page) {
  return page.getByRole('banner').getByRole('status')
}

/** When the served data was generated, as the manifest says it. */
async function generatedAt(request: APIRequestContext): Promise<string> {
  const response = await request.get(manifestUrl('./'))
  const manifest: unknown = await response.json()
  if (
    typeof manifest !== 'object' ||
    manifest === null ||
    !('generated_at' in manifest) ||
    typeof manifest.generated_at !== 'string'
  ) {
    throw new Error('The served manifest has no generation time.')
  }
  return manifest.generated_at
}

/** A manifest as the pipeline writes it, generated at the given moment. */
function manifestAt(moment: string) {
  return { format_version: 1, generated_at: moment, application_version: '0.1.0', counts: {} }
}

function writtenOut(moment: string, locale: string, timeZone: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone,
  }).format(new Date(moment))
}

test.describe('data status', () => {
  test.describe('for a British user in London', () => {
    test.use({ locale: 'en-GB', timezoneId: 'Europe/London' })

    test('says when the published data was updated', async ({ page, request }) => {
      const moment = await generatedAt(request)
      await page.goto('./')

      const expected = writtenOut(moment, 'en-GB', 'Europe/London')
      expect(expected).toMatch(/^\d{1,2} [A-Z][a-z]+ \d{4}$/)
      await expect(dataStatus(page)).toHaveText(`Data updated ${expected}`)
      await expect(dataStatus(page).locator('time')).toHaveAttribute('datetime', moment)
    })

    test('sits between the tagline and the date, in the quiet text colour', async ({ page }) => {
      await page.setViewportSize({ width: 1366, height: 768 })
      await page.goto('./')

      const status = dataStatus(page)
      await expect(status).toHaveText(/^Data updated /)
      await expect(status).toBeInViewport({ ratio: 1 })
      await expect(status).toHaveCSS('color', 'rgb(169, 172, 179)')
      await expect(status).toHaveCSS('font-size', '14px')
      const tagline = await page.getByText('The World of Motocross, Connected.').boundingBox()
      const statusBox = await status.boundingBox()
      const date = await page.getByRole('banner').locator('time:not(output time)').boundingBox()
      if (tagline === null || statusBox === null || date === null) {
        throw new Error('The tagline, the data status or the date is not visible.')
      }
      expect(statusBox.x).toBeGreaterThan(tagline.x + tagline.width)
      // A clear gap between the status and the date, and both on one line.
      expect(date.x - (statusBox.x + statusBox.width)).toBeGreaterThanOrEqual(12)
      expect(Math.abs(date.y - statusBox.y)).toBeLessThanOrEqual(1)
    })
  })

  // The served data was generated a moment ago, so its day is today in every
  // time zone. To check that the day is the user's own, these two tests answer
  // with a manifest whose moment falls on different days around the world.
  test.describe('for an American user in Los Angeles', () => {
    test.use({ locale: 'en-US', timezoneId: 'America/Los_Angeles' })

    test('writes the date the American way, for the day in Los Angeles', async ({ page }) => {
      await page.route(MANIFEST, (route) =>
        route.fulfill({ json: manifestAt('2026-11-17T02:00:00Z') }),
      )
      await page.goto('./')

      await expect(dataStatus(page)).toHaveText('Data updated November 16, 2026')
    })
  })

  test.describe('for a German user in Tokyo', () => {
    test.use({ locale: 'de-DE', timezoneId: 'Asia/Tokyo' })

    test('writes the date the German way, for the day in Tokyo', async ({ page }) => {
      await page.route(MANIFEST, (route) =>
        route.fulfill({ json: manifestAt('2026-11-17T20:00:00Z') }),
      )
      await page.goto('./')

      await expect(dataStatus(page)).toHaveText('Data updated 18. November 2026')
      await expect(dataStatus(page).locator('time')).toHaveAttribute(
        'datetime',
        '2026-11-17T20:00:00Z',
      )
    })
  })

  test('says the data is loading until it arrives', async ({ page }) => {
    const held: (() => Promise<void>)[] = []
    await page.route(MANIFEST, (route) => {
      held.push(() => route.continue())
    })
    await page.goto('./')

    await expect(dataStatus(page)).toHaveText('Loading data…')
    expect(held).toHaveLength(1)

    await held[0]?.()
    await expect(dataStatus(page)).toHaveText(/^Data updated /)
  })

  test('says the data is unavailable when the answer is a web page', async ({ page }) => {
    // A server that answers every address with the application's page does
    // this when the data has not been published.
    await page.route(MANIFEST, (route) =>
      route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>MotoSphere</title>' }),
    )
    await page.goto('./')

    await expect(dataStatus(page)).toHaveText('Data unavailable')
  })

  test('says the data is unavailable when the manifest is damaged', async ({ page }) => {
    await page.route(MANIFEST, (route) =>
      route.fulfill({ json: { format_version: 1, generated_at: 'yesterday' } }),
    )
    await page.goto('./')

    await expect(dataStatus(page)).toHaveText('Data unavailable')
  })

  test('asks for a reload when the data is in a newer format', async ({ page }) => {
    await page.route(MANIFEST, (route) =>
      route.fulfill({ json: { format_version: 2, layout: 'something new' } }),
    )
    await page.goto('./')

    await expect(dataStatus(page)).toHaveText('Reload the page to see the data')
  })

  test('keeps the rest of the page working when the data is unavailable', async ({ page }) => {
    await page.route(MANIFEST, (route) => route.fulfill({ contentType: 'text/html', body: '' }))
    await page.goto('./')
    await expect(dataStatus(page)).toHaveText('Data unavailable')

    await page.getByRole('button', { name: 'Tracks' }).click()

    await expect(page.getByRole('button', { name: 'Tracks' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(page.getByRole('banner').locator('time:not(output time)')).toBeVisible()
  })

  // A missing file and a failed request are page problems, which fail every
  // browser test (see `fixtures.ts`). These two tests say that they expect them.
  test('says the data is unavailable when the server does not have the manifest', async ({
    page,
    expectProblem,
  }) => {
    expectProblem(/^HTTP 404: http:\/\/[^/]+\/MotoSphere\/data\/manifest\.json$/)
    expectProblem(/^console error: Failed to load resource: .* status of 404 /)
    await page.route(MANIFEST, (route) =>
      route.fulfill({ status: 404, contentType: 'text/html', body: '<h1>Not found</h1>' }),
    )
    await page.goto('./')
    await expect(dataStatus(page)).toHaveText('Data unavailable')

    await page.getByRole('button', { name: 'Events' }).click()

    await expect(page.getByRole('button', { name: 'Events' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  test('says the data is unavailable when the request for the manifest fails', async ({
    page,
    expectProblem,
  }) => {
    expectProblem(/^request failed: GET http:\/\/[^/]+\/MotoSphere\/data\/manifest\.json$/)
    expectProblem(/^console error: Failed to load resource: net::ERR_FAILED$/)
    await page.route(MANIFEST, (route) => route.abort())
    await page.goto('./')
    await expect(dataStatus(page)).toHaveText('Data unavailable')

    await page.getByRole('button', { name: 'Events' }).click()

    await expect(page.getByRole('button', { name: 'Events' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })
})
