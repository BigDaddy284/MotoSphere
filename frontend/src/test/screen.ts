import { act } from '@testing-library/react'

/** The width of the screen the tests start with: a wide one. */
export const WIDE_SCREEN = 1366

// The only kind of question about the screen the application asks.
const MAX_WIDTH = /^\(max-width: (\d+)px\)$/

type Listener = () => void

let width = WIDE_SCREEN
const listeners = new Set<Listener>()

/**
 * A stand-in for the part of the browser that knows how wide the screen is,
 * which the test environment does not have. It answers from the width the
 * test has set, and refuses a question it does not understand.
 */
function matchMedia(query: string): MediaQueryList {
  const limit = MAX_WIDTH.exec(query)?.[1]
  if (limit === undefined) {
    throw new Error(`The stand-in screen does not understand the question ${query}`)
  }
  const answer = {
    media: query,
    get matches() {
      return width <= Number(limit)
    },
    addEventListener(_type: string, listener: Listener) {
      listeners.add(listener)
    },
    removeEventListener(_type: string, listener: Listener) {
      listeners.delete(listener)
    },
  }
  return answer as MediaQueryList
}

/** Puts the stand-in in place, with a wide screen that nothing is watching. */
export function installScreen(): void {
  width = WIDE_SCREEN
  listeners.clear()
  window.matchMedia = matchMedia
}

/** Changes the width of the screen, in pixels, and tells whoever is watching. */
export function showScreen(pixels: number): void {
  act(() => {
    width = pixels
    for (const listener of listeners) {
      listener()
    }
  })
}

/** How many parts of the page are watching the width of the screen. */
export function screenWatchers(): number {
  return listeners.size
}
