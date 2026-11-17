import type { Page } from '@playwright/test'
import { expect, test, unexplained } from './fixtures'

/**
 * The rule every browser test runs under: a page that reports a problem fails
 * its test, unless the test said it expects exactly that problem.
 */

/** Makes the page report an uncaught error with the given message. */
async function breakPage(page: Page, message: string) {
  const reported = page.waitForEvent('pageerror')
  await page.evaluate((text) => {
    setTimeout(() => {
      throw new Error(text)
    })
  }, message)
  await reported
}

/** Makes the page write a line to its console. */
async function writeToConsole(page: Page, method: 'error' | 'warn' | 'info', text: string) {
  await page.evaluate(`console.${method}(${JSON.stringify(text)})`)
}

test.describe('judging the problems a page reported', () => {
  test('finds nothing wrong when there are no problems and none is expected', () => {
    expect(unexplained([], [])).toEqual([])
  })

  test('names every problem nobody expected', () => {
    expect(unexplained(['console error: boom', 'HTTP 500: /x'], [])).toEqual([
      'console error: boom',
      'HTTP 500: /x',
    ])
  })

  test('accepts a problem the test expects', () => {
    expect(unexplained(['HTTP 404: /data/manifest.json'], [/^HTTP 404: /])).toEqual([])
  })

  test('accepts an expected problem that happens more than once', () => {
    expect(unexplained(['HTTP 404: /a', 'HTTP 404: /a'], [/^HTTP 404: \/a$/])).toEqual([])
  })

  test('names an expected problem that did not happen', () => {
    expect(unexplained([], [/^HTTP 404: /])).toEqual([
      'expected, but did not happen: /^HTTP 404: /',
    ])
  })

  test('names another problem beside the expected one', () => {
    expect(unexplained(['HTTP 404: /a', 'console error: boom'], [/^HTTP 404: /])).toEqual([
      'console error: boom',
    ])
  })

  test('wants every expected problem, not just one of them', () => {
    expect(unexplained(['HTTP 404: /a'], [/^HTTP 404: /, /^console error: /])).toEqual([
      'expected, but did not happen: /^console error: /',
    ])
  })
})

// `test.fail()` turns a test round: it passes only when the test fails. These
// tests do nothing wrong themselves, so what fails them is the rule.
test.describe('a test that expects no problem', () => {
  test('passes on a healthy page', async ({ page }) => {
    await page.goto('/')
  })

  test('passes when the page only writes information to its console', async ({ page }) => {
    await page.goto('/')

    await writeToConsole(page, 'info', 'all is well')
  })

  test('fails when the page reports one', async ({ page }) => {
    test.fail()
    await page.goto('/')

    await breakPage(page, 'boom')
  })
})

test.describe('a test that expects a problem', () => {
  test('passes when the page reports it', async ({ page, expectProblem }) => {
    expectProblem(/^uncaught error: boom$/)
    await page.goto('/')

    await breakPage(page, 'boom')
  })

  test('fails when the page does not report it', async ({ page, expectProblem }) => {
    test.fail()
    expectProblem(/^uncaught error: boom$/)
    await page.goto('/')
  })

  test('fails when the page reports another problem as well', async ({ page, expectProblem }) => {
    test.fail()
    expectProblem(/^uncaught error: boom$/)
    await page.goto('/')

    await breakPage(page, 'boom')
    await breakPage(page, 'bang')
  })

  test('counts an error in the console as a problem', async ({ page, expectProblem }) => {
    expectProblem(/^console error: boom$/)
    await page.goto('/')

    await writeToConsole(page, 'error', 'boom')
  })

  test('counts a warning in the console as a problem', async ({ page, expectProblem }) => {
    expectProblem(/^console warning: careful$/)
    await page.goto('/')

    await writeToConsole(page, 'warn', 'careful')
  })

  test('passes when the page reports each of two expected problems', async ({
    page,
    expectProblem,
  }) => {
    expectProblem(/^uncaught error: boom$/)
    expectProblem(/^uncaught error: bang$/)
    await page.goto('/')

    await breakPage(page, 'boom')
    await breakPage(page, 'bang')
  })
})
