import { expect, test } from './fixtures'

test.describe('Graphite theme', () => {
  test('uses the dark background and light text', async ({ page }) => {
    await page.goto('./')
    const body = page.locator('body')
    await expect(body).toHaveCSS('background-color', 'rgb(29, 30, 33)')
    await expect(body).toHaveCSS('color', 'rgb(236, 236, 238)')
    await expect(page.locator('html')).toHaveCSS('color-scheme', 'dark')
  })

  test('uses the Segoe UI font stack at a readable size, with no page margin', async ({ page }) => {
    await page.goto('./')
    const body = page.locator('body')
    await expect(body).toHaveCSS('font-family', /^"Segoe UI Variable Text", "Segoe UI", system-ui/)
    await expect(body).toHaveCSS('font-size', '16px')
    await expect(body).toHaveCSS('line-height', '24px')
    await expect(body).toHaveCSS('margin', '0px')
    // The application's own heading is styled by the shell, so the test adds
    // a heading to measure the base heading style.
    await page.evaluate(() => {
      const heading = document.createElement('h2')
      heading.textContent = 'Heading probe'
      document.body.append(heading)
    })
    const heading = page.getByRole('heading', { name: 'Heading probe' })
    await expect(heading).toHaveCSS('font-size', '24px')
    await expect(heading).toHaveCSS('font-weight', '700')
  })

  test('shows a focus ring when an element is reached by keyboard', async ({ page }) => {
    await page.goto('./')
    // The test adds its own button, first on the page, to measure the base
    // focus style rather than a component's.
    await page.evaluate(() => {
      const button = document.createElement('button')
      button.textContent = 'Focus target'
      document.body.prepend(button)
    })
    const button = page.getByRole('button', { name: 'Focus target' })
    await expect(button).toHaveCSS('outline-style', 'none')

    await page.keyboard.press('Tab')

    await expect(button).toBeFocused()
    await expect(button).toHaveCSS('outline-style', 'solid')
    await expect(button).toHaveCSS('outline-width', '2px')
    await expect(button).toHaveCSS('outline-color', 'rgb(94, 168, 255)')
    await expect(button).toHaveCSS('outline-offset', '2px')
  })

  test('removes motion for people who ask for reduced motion', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('./')
    const durations = await page.evaluate(() => {
      const element = document.createElement('div')
      element.style.transition = 'opacity 2s'
      element.style.animation = 'none 2s'
      document.body.append(element)
      const style = getComputedStyle(element)
      return {
        transition: Number.parseFloat(style.transitionDuration),
        animation: Number.parseFloat(style.animationDuration),
      }
    })
    expect(durations).toEqual({ transition: 0.00001, animation: 0.00001 })
  })

  test('keeps motion for everyone else', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' })
    await page.goto('./')
    const transitionDuration = await page.evaluate(() => {
      const element = document.createElement('div')
      element.style.transition = 'opacity 2s'
      document.body.append(element)
      return getComputedStyle(element).transitionDuration
    })
    expect(transitionDuration).toBe('2s')
  })
})
