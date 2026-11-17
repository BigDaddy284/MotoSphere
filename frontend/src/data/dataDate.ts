/**
 * Writes the day of a moment out in full, in the given language (the
 * browser's when none is given) and in the time zone of the user's device,
 * for example "17 November 2026".
 */
export function formatDataDate(moment: string, locale?: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(moment))
}
