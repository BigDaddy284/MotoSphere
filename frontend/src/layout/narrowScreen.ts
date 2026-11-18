import { useSyncExternalStore } from 'react'

/**
 * A screen too narrow for the side panels to stand beside the globe stage: a
 * phone, or a tablet held upright. The layout's style sheet draws the same
 * line, in the same words.
 */
export const NARROW_SCREEN = '(max-width: 899px)'

function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia(NARROW_SCREEN)
  query.addEventListener('change', onChange)
  return () => {
    query.removeEventListener('change', onChange)
  }
}

function isNarrow(): boolean {
  return window.matchMedia(NARROW_SCREEN).matches
}

/** Whether the screen is a narrow one, now and whenever its width changes. */
export function useNarrowScreen(): boolean {
  return useSyncExternalStore(subscribe, isNarrow)
}
