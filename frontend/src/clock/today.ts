// A calendar day is handled as a "day key": the text YYYY-MM-DD, for the day
// in the user's own time zone. It is also the machine-readable form that the
// HTML `time` element expects.

function pad(value: number, length: number): string {
  return String(value).padStart(length, '0')
}

/** The day key of a moment, in the time zone of the user's device. */
export function localDayKey(moment: Date): string {
  return [
    pad(moment.getFullYear(), 4),
    pad(moment.getMonth() + 1, 2),
    pad(moment.getDate(), 2),
  ].join('-')
}

/**
 * The milliseconds from a moment to the start of the next day in the time
 * zone of the user's device. Days are not always 24 hours long (clock
 * changes), so this is worked out from the calendar.
 */
export function msUntilNextDay(moment: Date): number {
  const nextDay = new Date(moment.getFullYear(), moment.getMonth(), moment.getDate() + 1)
  return nextDay.getTime() - moment.getTime()
}

/**
 * A day key written out for reading, such as "Tuesday 17 November 2026", in
 * the given language, or in the language of the user's browser.
 */
export function formatDay(dayKey: string, locale?: string): string {
  // The key already is the user's local day. Reading and formatting it as a
  // UTC date keeps the device's time zone from shifting it a second time.
  return new Intl.DateTimeFormat(locale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${dayKey}T00:00:00Z`))
}
