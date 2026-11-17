import { expect, test as base } from '@playwright/test'

/**
 * Every browser test uses this `test`. It records anything that shows the page
 * is unhealthy and fails the test if there was any, even when the test's own
 * assertions passed.
 */
export const test = base.extend<{ pageProblems: string[] }>({
  pageProblems: [
    async ({ page }, use) => {
      const problems: string[] = []
      page.on('console', (message) => {
        const type = message.type()
        if (type === 'error' || type === 'warning') {
          problems.push(`console ${type}: ${message.text()}`)
        }
      })
      page.on('pageerror', (error) => {
        problems.push(`uncaught error: ${error.message}`)
      })
      page.on('requestfailed', (request) => {
        problems.push(`request failed: ${request.method()} ${request.url()}`)
      })
      page.on('response', (response) => {
        if (response.status() >= 400) {
          problems.push(`HTTP ${response.status()}: ${response.url()}`)
        }
      })
      await use(problems)
      expect(problems, 'the page reported problems').toEqual([])
    },
    { auto: true },
  ],
})

export { expect }
