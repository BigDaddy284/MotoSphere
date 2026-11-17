import { describe, expect, it } from 'vitest'
import { formatDataDate } from './dataDate.ts'

// The moment is built from local calendar values, so that these tests give
// the same result in every time zone.
const EVENING = new Date(2026, 10, 17, 23, 30).toISOString()

describe('formatDataDate', () => {
  it.each([
    ['en-GB', '17 November 2026'],
    ['en-US', 'November 17, 2026'],
    ['de-DE', '17. November 2026'],
  ])('writes the day out in full for %s', (locale, expected) => {
    expect(formatDataDate(EVENING, locale)).toBe(expected)
  })

  it('uses the day where the user is, not the day in UTC', () => {
    const justAfterMidnight = new Date(2026, 10, 18, 0, 30).toISOString()

    expect(formatDataDate(justAfterMidnight, 'en-GB')).toBe('18 November 2026')
  })

  it("uses the browser's language when none is given", () => {
    const expected = new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(new Date(EVENING))

    expect(formatDataDate(EVENING)).toBe(expected)
  })
})
