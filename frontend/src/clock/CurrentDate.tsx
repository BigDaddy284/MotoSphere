import { formatDay } from './today.ts'
import { useToday } from './useToday.ts'

/** Today's date, written out in the language of the user's browser. */
export function CurrentDate() {
  const today = useToday()

  return <time dateTime={today}>{formatDay(today)}</time>
}
