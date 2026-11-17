import { useState } from 'react'

/** The side panels the user can close and open. */
export type PanelName = 'sections' | 'details'

const KEY_PREFIX = 'motosphere.panel.'

// The choice is kept in session storage: it survives a reload and ends with
// the browser tab. Storage can be unavailable (some privacy settings block
// it); the panels then simply start open.
function readOpen(name: PanelName): boolean {
  try {
    return window.sessionStorage.getItem(KEY_PREFIX + name) !== 'closed'
  } catch {
    return true
  }
}

function writeOpen(name: PanelName, open: boolean): void {
  try {
    window.sessionStorage.setItem(KEY_PREFIX + name, open ? 'open' : 'closed')
  } catch {
    // Not remembered: the choice still holds until the page is reloaded.
  }
}

/**
 * Whether a side panel is open, and a function that closes or opens it.
 * Panels start open; the user's choice is remembered for the session.
 */
export function usePanelOpen(name: PanelName): [open: boolean, toggle: () => void] {
  const [open, setOpen] = useState(() => readOpen(name))

  function toggle() {
    const next = !open
    writeOpen(name, next)
    setOpen(next)
  }

  return [open, toggle]
}
