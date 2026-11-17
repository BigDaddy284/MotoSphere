import { useEffect, useState } from 'react'
import { localDayKey, msUntilNextDay } from './today.ts'

/**
 * Today's day key (YYYY-MM-DD) in the time zone of the user's device. It
 * changes when the day changes, without a reload.
 */
export function useToday(): string {
  const [today, setToday] = useState(() => localDayKey(new Date()))

  useEffect(() => {
    let timer: number | undefined

    function refresh() {
      const now = new Date()
      setToday(localDayKey(now))
      window.clearTimeout(timer)
      timer = window.setTimeout(refresh, msUntilNextDay(now))
    }

    // A timer does not run while the device sleeps, so the day is also
    // checked whenever the page comes back into view.
    document.addEventListener('visibilitychange', refresh)
    refresh()

    return () => {
      document.removeEventListener('visibilitychange', refresh)
      window.clearTimeout(timer)
    }
  }, [])

  return today
}
