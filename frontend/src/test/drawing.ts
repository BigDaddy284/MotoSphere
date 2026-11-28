/** What a browser does when a page asks it for a picture to draw on. */
interface Browser {
  /** The kinds of picture it gives. */
  kinds: readonly string[]
  /** Whether it hands out the way to give a 3D picture back. */
  takesBack: boolean
}

/** A current browser: it gives both kinds of 3D picture and takes them back. */
const CURRENT: Browser = { kinds: ['webgl', 'webgl2'], takesBack: true }

let browser = CURRENT
let asked: string[] = []
let held = 0

/**
 * A stand-in for the part of the browser that gives a page a picture to
 * draw on, which the test environment does not have. It gives the kinds the
 * test has set, as something that can be given back and nothing more: no
 * test draws.
 */
function getContext(kind: string): object | null {
  asked.push(kind)
  if (!browser.kinds.includes(kind)) {
    return null
  }
  const { takesBack } = browser
  let mine = true
  held += 1
  return {
    getExtension(name: string) {
      if (name !== 'WEBGL_lose_context' || !takesBack) {
        return null
      }
      return {
        // A picture is given back once, however often that is said.
        loseContext() {
          if (mine) {
            mine = false
            held -= 1
          }
        },
      }
    },
  }
}

/** Puts the stand-in in place, as a current browser that was asked for nothing. */
export function installDrawing(): void {
  browser = CURRENT
  asked = []
  held = 0
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    configurable: true,
    writable: true,
    value: getContext,
  })
}

/** Makes the browser one that gives these kinds of picture and no other. */
export function browserGives(kinds: readonly string[], takesBack = true): void {
  browser = { kinds, takesBack }
}

/** The kinds of picture the page asked for, in the order it asked. */
export function picturesAskedFor(): readonly string[] {
  return [...asked]
}

/** How many pictures the page was given and has not given back. */
export function picturesHeld(): number {
  return held
}
