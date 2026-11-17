import { expect, test } from './fixtures'

test.describe('built application', () => {
  test('has the application title and language', async ({ page }) => {
    await page.goto('./')
    await expect(page).toHaveTitle('MotoSphere')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  })

  test('shows the application name and tagline', async ({ page }) => {
    await page.goto('./')
    await expect(page.getByRole('heading', { level: 1, name: 'MotoSphere' })).toBeVisible()
    await expect(page.getByText('The World of Motocross, Connected.')).toBeVisible()
  })

  test('has exactly one main landmark', async ({ page }) => {
    await page.goto('./')
    await expect(page.getByRole('main')).toHaveCount(1)
  })
})
