import { expect, test as base } from '@playwright/test'

/**
 * What is wrong with the problems a page reported, given the problems the
 * test said it expects. Every problem must be an expected one, and every
 * expected problem must have happened. An empty list means all is well.
 */
export function unexplained(problems: readonly string[], expected: readonly RegExp[]): string[] {
  const unexpected = problems.filter(
    (problem) => !expected.some((pattern) => pattern.test(problem)),
  )
  const missing = expected
    .filter((pattern) => !problems.some((problem) => pattern.test(problem)))
    .map((pattern) => `expected, but did not happen: ${String(pattern)}`)
  return [...unexpected, ...missing]
}

type Fixtures = {
  /**
   * Says that this test expects the page to report a problem whose recorded
   * text matches the pattern. Do not give the pattern the `g` or `y` flag:
   * such a pattern remembers where it stopped.
   */
  expectProblem: (pattern: RegExp) => void
  pageHealth: { readonly problems: string[]; readonly expected: RegExp[] }
}

/**
 * Every browser test uses this `test`. It records anything that shows the page
 * is unhealthy and fails the test if there was any, even when the test's own
 * assertions passed. A test about a failure names the problems it expects with
 * `expectProblem`; it then fails if one of them does not happen, and still
 * fails on any other.
 */
export const test = base.extend<Fixtures>({
  pageHealth: [
    async ({ page }, provide) => {
      const problems: string[] = []
      const expected: RegExp[] = []
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
      await provide({ problems, expected })
      expect(unexplained(problems, expected), 'the page reported problems').toEqual([])
    },
    { auto: true },
  ],
  expectProblem: async ({ pageHealth }, provide) => {
    await provide((pattern) => {
      pageHealth.expected.push(pattern)
    })
  },
})

export { expect }
