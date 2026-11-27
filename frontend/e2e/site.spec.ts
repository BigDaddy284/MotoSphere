import { SITE_PATH } from '../site.ts'
import { manifestUrl } from '../src/data/manifest.ts'
import { expect, test } from './fixtures'

/**
 * The published site does not live at the root of its server: GitHub Pages
 * serves it under the name of the repository. The site under test is served
 * the same way, and these tests show that the application needs nothing from
 * outside its own path.
 */

test.describe("the site's path", () => {
  test('is the name of the repository, between slashes', () => {
    expect(SITE_PATH).toBe('/MotoSphere/')
  })

  test('is where the application is served', async ({ page, baseURL }) => {
    expect(baseURL?.endsWith(SITE_PATH)).toBe(true)

    const response = await page.goto('./')

    expect(response?.status()).toBe(200)
    expect(new URL(page.url()).pathname).toBe(SITE_PATH)
    await expect(page).toHaveTitle('MotoSphere')
    await expect(page.getByRole('banner')).toBeVisible()
  })

  test('holds everything the page loads', async ({ page }) => {
    const loaded: string[] = []
    page.on('request', (request) => {
      loaded.push(new URL(request.url()).pathname)
    })

    await page.goto('./')
    await expect(page.getByRole('banner').getByRole('status')).toHaveText(/^Data updated /)

    expect(loaded.filter((pathname) => !pathname.startsWith(SITE_PATH))).toEqual([])
    expect(loaded).toContain(SITE_PATH)
    expect(loaded).toContain(manifestUrl(SITE_PATH))
    expect(loaded.some((pathname) => pathname.endsWith('.js'))).toBe(true)
    expect(loaded.some((pathname) => pathname.endsWith('.css'))).toBe(true)
  })

  for (const file of ['favicon.svg', 'favicon.ico', 'apple-touch-icon.png', 'data/manifest.json']) {
    test(`${file} is under the path and not at the root of the server`, async ({ request }) => {
      const underThePath = await request.get(file)
      const atTheRoot = await request.get(`/${file}`, { maxRedirects: 0 })

      expect(underThePath.status()).toBe(200)
      expect(new URL(underThePath.url()).pathname).toBe(`${SITE_PATH}${file}`)
      expect(atTheRoot.status()).toBe(404)
    })
  }
})
