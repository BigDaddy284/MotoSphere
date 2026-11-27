/**
 * What React still has to do.
 *
 * React does not show a page at once when it is asked to. Outside `act` it
 * asks the system to call it back a moment later, with `setImmediate`, and
 * does the work then. A test that ends before that moment leaves the work
 * waiting; if the test file ends too, the work runs after the test's
 * document is gone and fails with "window is not defined", in a run now
 * and then (FND-055).
 *
 * This watches what React asks for. The set-up of the unit tests lets no
 * test end before React has nothing waiting (FND-056; TESTING.md).
 */

/** The function React's scheduler asks the system to call when it has work. */
export const REACTS_WORK = 'performWorkUntilDeadline'

/** How many times `settled` lets the waiting work run before it gives up. */
export const TURNS = 100

/** What `settled` fails with when React's work does not come to an end. */
export const STILL_WAITING = `React still has work waiting after it was let run ${TURNS} times: something asks it for more work without end.`

/** What `close` fails with when a test file ends with React's work waiting. */
export function leftWaiting(pieces: number): string {
  return `The test file ends with ${pieces} of React's work still waiting: it would run after the test's document is gone.`
}

export type Work = (...given: unknown[]) => void

/** Who gives out `setImmediate`: the system, or a stand-in for it in a test. */
export type Host = { setImmediate: (work: Work, ...given: unknown[]) => unknown }

export type ReactsWork = {
  /** How many pieces of React's work were asked for and have not run yet. */
  waiting: () => number
  /**
   * Lets the waiting work run until none is waiting. Fails with
   * `STILL_WAITING` when some is still waiting after `TURNS` turns.
   */
  settled: () => Promise<void>
  /**
   * For the end of a test file: gives the host its own `setImmediate` back,
   * and fails with `leftWaiting` when React's work is still waiting then.
   */
  close: () => void
}

/**
 * Puts a counting `setImmediate` in the place of the host's own. It must be
 * called before React is loaded: React keeps the `setImmediate` it finds
 * when it is loaded.
 */
export function watchReactsWork(host: Host): ReactsWork {
  const real = host.setImmediate
  let waiting = 0
  const watched = Object.assign((work: Work, ...given: unknown[]) => {
    if (work.name !== REACTS_WORK) {
      return real(work, ...given)
    }
    waiting += 1
    return real(() => {
      waiting -= 1
      work(...given)
    })
  }, real)
  host.setImmediate = watched
  const stillWaiting = () => waiting
  return {
    waiting: stillWaiting,
    settled: async () => {
      for (let turn = 0; stillWaiting() > 0; turn += 1) {
        if (turn === TURNS) {
          throw new Error(STILL_WAITING)
        }
        // What was asked for before this runs before it: one turn lets
        // every piece that is waiting now run.
        await new Promise<void>((resolve) => {
          real(() => {
            resolve()
          })
        })
      }
    },
    close: () => {
      host.setImmediate = real
      if (waiting > 0) {
        throw new Error(leftWaiting(waiting))
      }
    },
  }
}

/** Where a test runner takes what is to be done after each test and after all. */
export type Hooks = {
  afterEach: (hook: () => Promise<void>) => void
  afterAll: (hook: () => void) => void
}

/**
 * Holds the tests of a file to the watch. After each test, when `tidy` has
 * put away what the test left, React is let do what it was asked for and
 * has not done yet: no test ends with work of the page waiting. When the
 * file is over the watch is closed, which fails if work is waiting even
 * then: it would run after the test's document is gone.
 */
export function endEveryTestSettled(watch: ReactsWork, hooks: Hooks, tidy: () => void): void {
  hooks.afterEach(async () => {
    tidy()
    await watch.settled()
  })
  hooks.afterAll(() => {
    watch.close()
  })
}

function givesOutSetImmediate(system: object): system is Host {
  return 'setImmediate' in system && typeof system.setImmediate === 'function'
}

function theSystem(): Host {
  const system: object = globalThis
  if (!givesOutSetImmediate(system)) {
    throw new Error('The unit tests run where there is a setImmediate, and here there is none.')
  }
  return system
}

/**
 * The watch of the unit tests, over the system's own `setImmediate`. The
 * set-up of the tests brings this module in before anything that loads
 * React.
 */
export const reactsWork = watchReactsWork(theSystem())
