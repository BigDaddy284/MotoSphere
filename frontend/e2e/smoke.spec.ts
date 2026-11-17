import { expect, test } from './fixtures'

test.describe('built application', () => {
  test('has the application title and language', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle('MotoSphere')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  })

  test('shows the application name and tagline', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1, name: 'MotoSphere' })).toBeVisible()
    await expect(page.getByText('The World of Motocross, Connected.')).toBeVisible()
  })

  test('has exactly one main landmark', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('main')).toHaveCount(1)
  })

  test('serves the icon the page links to', async ({ page, request }) => {
    await page.goto('/')
    await expect(page.locator('link[rel="icon"]')).toHaveAttribute('href', '/favicon.svg')
    const response = await request.get('/favicon.svg')
    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toContain('image/svg+xml')
  })
})
