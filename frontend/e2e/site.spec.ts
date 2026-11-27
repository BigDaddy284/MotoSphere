import { readdirSync, readFileSync } from 'node:fs'
import { extname, join } from 'node:path'
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

/**
 * The published site is files. GitHub Pages answers an address that names no
 * file with "not found", and the site under test answers the same: a missing
 * file is then missing in the tests too, and is not taken for the page.
 */
test.describe('an address under the path that names no file', () => {
  for (const missing of [
    'nothing-here',
    'nothing-here.png',
    'nothing-here.html',
    'nothing/here/at-all.json',
    'data/nothing-here.json',
    'assets/nothing-here.js',
    'assets/',
    'data/',
    'index.html/more',
  ]) {
    test(`${missing} is answered with "not found", and not with the page`, async ({ request }) => {
      const response = await request.get(missing, { maxRedirects: 0 })

      expect(new URL(response.url()).pathname).toBe(`${SITE_PATH}${missing}`)
      expect(response.status()).toBe(404)
      expect(await response.text()).not.toContain('<div id="root">')
    })
  }

  for (const [said, address] of [
    ['the path itself', './'],
    ['the file of the page', 'index.html'],
    ['the path with a question after it', './?from=a-link'],
  ] as const) {
    test(`the page is still answered at ${said}`, async ({ request }) => {
      const response = await request.get(address, { maxRedirects: 0 })

      expect(response.status()).toBe(200)
      expect(response.headers()['content-type']).toMatch(/^text\/html\b/)
      expect(await response.text()).toContain('<div id="root">')
    })
  }

  test('is told to the browser as "not found", and the page is not shown', async ({
    page,
    expectProblem,
  }) => {
    expectProblem(/^HTTP 404: http:\/\/[^/]+\/MotoSphere\/nothing-here$/)
    expectProblem(/^console error: Failed to load resource: .* status of 404 /)

    const response = await page.goto('nothing-here')

    expect(response?.status()).toBe(404)
    await expect(page.getByRole('banner')).toHaveCount(0)
  })
})

/**
 * After every deployment the published site is checked file by file
 * (`scripts/live.py`), and each kind of file is held to what a browser must
 * be told it is. `siteKinds.json` lists the kinds the site is made of. This
 * test holds the list to the site that was built for this run, and a test of
 * the check holds the check's rules to the list. A site that gains a kind of
 * file so fails here until the kind is listed, and there until it has a rule.
 * The browser tests are run from the folder of the front end.
 */
test.describe('the kinds of file of the built site', () => {
  test('are the listed ones, and each of those is there', () => {
    const listed: unknown = JSON.parse(
      readFileSync(join(import.meta.dirname, 'siteKinds.json'), 'utf8'),
    )
    const kinds = readdirSync(join(process.cwd(), 'dist'), { recursive: true, withFileTypes: true })
      .filter((entry) => entry.isFile())
      .map((entry) => extname(entry.name).toLowerCase())

    expect(kinds.length).toBeGreaterThan(200)
    expect([...new Set(kinds)].toSorted()).toEqual(listed)
  })
})
