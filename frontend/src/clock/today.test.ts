import { describe, expect, it } from 'vitest'
import { formatDay, localDayKey, msUntilNextDay } from './today.ts'

// Every moment is built from local calendar values, never from a UTC text, so
// that these tests give the same result in every time zone.

describe('localDayKey', () => {
  it('writes the day as YYYY-MM-DD', () => {
    expect(localDayKey(new Date(2026, 10, 17, 12, 0))).toBe('2026-11-17')
  })

  it('pads single-digit months and days', () => {
    expect(localDayKey(new Date(2027, 0, 5, 12, 0))).toBe('2027-01-05')
  })

  it('uses the local day up to the last millisecond before midnight', () => {
    expect(localDayKey(new Date(2026, 10, 17, 23, 59, 59, 999))).toBe('2026-11-17')
  })

  it('uses the new local day from midnight', () => {
    expect(localDayKey(new Date(2026, 10, 18, 0, 0, 0, 0))).toBe('2026-11-18')
  })
})

describe('msUntilNextDay', () => {
  it('counts the time left in the day', () => {
    expect(msUntilNextDay(new Date(2026, 10, 17, 23, 59, 50))).toBe(10_000)
  })

  it('is a whole day at midnight', () => {
    const midnight = new Date(2026, 10, 18, 0, 0, 0, 0)

    const next = new Date(midnight.getTime() + msUntilNextDay(midnight))

    expect(localDayKey(next)).toBe('2026-11-19')
    expect([next.getHours(), next.getMinutes(), next.getSeconds(), next.getMilliseconds()]).toEqual(
      [0, 0, 0, 0],
    )
  })

  it('crosses the end of a month and of a year', () => {
    const lateEvening = new Date(2026, 11, 31, 23, 0)

    const wait = msUntilNextDay(lateEvening)

    expect(wait).toBe(3_600_000)
    expect(localDayKey(new Date(lateEvening.getTime() + wait))).toBe('2027-01-01')
  })
})

describe('formatDay', () => {
  it('writes the day out in British English', () => {
    // The comma depends on the version of the language data.
    expect(formatDay('2026-11-17', 'en-GB')).toMatch(/^Tuesday,? 17 November 2026$/)
  })

  it('writes the day out in American English', () => {
    expect(formatDay('2026-11-17', 'en-US')).toBe('Tuesday, November 17, 2026')
  })

  it('writes the day out in German', () => {
    expect(formatDay('2026-11-17', 'de-DE')).toBe('Dienstag, 17. November 2026')
  })

  it('keeps the day of the key at both ends of a month', () => {
    expect(formatDay('2026-03-01', 'en-GB')).toMatch(/^Sunday,? 1 March 2026$/)
    expect(formatDay('2026-12-31', 'en-GB')).toMatch(/^Thursday,? 31 December 2026$/)
  })

  it('refuses text that is not a day', () => {
    expect(() => formatDay('today', 'en-GB')).toThrow(RangeError)
  })
})
