import { browserDraws3D } from '../../src/globe/drawing.ts'
import { expect, test } from './fixtures'

/**
 * These tests run in the browser of the globe tests, which draws 3D
 * pictures. There the globe stage shows the globe and has nothing to say.
 * The fixture of every browser test fails each of them for any warning or
 * error on the console.
 */

test.describe('the globe stage in a browser that draws 3D pictures', () => {
  test('does not say that the globe cannot be shown: it shows the globe', async ({ page }) => {
    await page.goto('./')
    await expect(page.getByRole('banner').getByRole('status')).toHaveText(/^Data updated /)

    const stage = page.getByRole('main', { name: 'Globe' })
    await expect(stage.locator('[aria-busy]')).toHaveCount(1)
    await expect(stage.locator('p')).toHaveCount(0)
    await expect(page.getByText('cannot be shown')).toHaveCount(0)
  })

  test('is asked forty times in a row whether it draws, and the browser has no word about it', async ({
    page,
  }) => {
    // A browser keeps only so many 3D pictures for a page, and warns on the
    // console when it takes the oldest away. The question is asked forty
    // times without a pause in which the browser could clear anything
    // away: a question that kept its picture would get that warning.
    await page.goto('./')

    const answers = await page.evaluate(
      `Array.from({ length: 40 }, () => (${browserDraws3D.toString()})())`,
    )

    expect(answers).toEqual(Array.from({ length: 40 }, () => true))
  })

  test('has the top bar and both panels working around it', async ({ page }) => {
    await page.goto('./')
    const stage = page.getByRole('main', { name: 'Globe' })
    const sections = page.getByRole('navigation', { name: 'Sections' })
    const details = page.getByRole('complementary', { name: 'Details' })
    await expect(sections).toBeVisible()
    await expect(details).toBeVisible()

    await sections.getByRole('button', { name: 'Championships' }).click()
    await expect(sections.getByRole('button', { name: 'Championships' })).toHaveAttribute(
      'aria-current',
      'page',
    )

    await page.getByRole('button', { name: 'Sections' }).click()
    await page.getByRole('button', { name: 'Details' }).click()
    await expect(sections).toBeHidden()
    await expect(details).toBeHidden()
    expect(await stage.boundingBox()).toMatchObject({ x: 0, width: 1280 })

    await page.getByRole('button', { name: 'Sections' }).click()
    await page.getByRole('button', { name: 'Details' }).click()
    await expect(sections).toBeVisible()
    await expect(details).toBeVisible()
    await expect(stage.locator('[aria-busy]')).toHaveCount(1)
  })
})
