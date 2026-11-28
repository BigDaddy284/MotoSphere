import type { Load, Start } from '../globe/Globe.tsx'

/** An engine the stand-in started. */
export type Engine = {
  /** The element it was started in. */
  surface: HTMLElement
  /** Whether that element was in the page when the engine was started. */
  inThePage: boolean
  /** How many times it was stopped. */
  stops: number
}

export type StandIn = {
  /** The way to load the engine that a test hands to a globe. */
  load: Load
  /** How many times the engine was asked for. */
  loadings: () => number
  /** Lets a loading end well: the one asked for first, or the one named. */
  arrives: (which?: number) => Promise<void>
  /** Lets a loading end badly, with what went wrong. */
  fails: (why: unknown, which?: number) => Promise<void>
  /** From now on the engine cannot be started, and says this. */
  breaksAtTheStart: (why: unknown) => void
  /** Every engine that was started, in the order they were started. */
  engines: () => readonly Engine[]
  /** The elements in which an engine is running now. */
  running: () => readonly HTMLElement[]
}

type Loading = { give: (start: Start) => void; refuse: (why: unknown) => void }

/** What a test is told that names a loading the engine was not asked for. */
export function noSuchLoading(asked: number, which: number): string {
  return `The engine was asked for ${asked} times, so there is no loading number ${which}.`
}

/** A moment in which what waits on a loading can run. */
function aMoment(): Promise<void> {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, 0)
  })
}

/**
 * A stand-in for the engine of the globe. The real engine draws, which the
 * test environment cannot, and takes its time to load. The stand-in is
 * loaded when the test says so, well or badly, and remembers where it was
 * started and how often it was stopped. Nothing of the real engine is in
 * it.
 */
export function standInEngine(): StandIn {
  const asked: Loading[] = []
  const started: Engine[] = []
  let broken: { why: unknown } | undefined

  const start: Start = (surface) => {
    if (broken !== undefined) {
      throw broken.why
    }
    const engine = { surface, inThePage: surface.isConnected, stops: 0 }
    started.push(engine)
    return () => {
      engine.stops += 1
    }
  }

  function loading(which: number): Loading {
    const found = asked[which]
    if (found === undefined) {
      throw new Error(noSuchLoading(asked.length, which))
    }
    return found
  }

  return {
    load: () =>
      new Promise<Start>((give, refuse) => {
        asked.push({ give, refuse })
      }),
    loadings: () => asked.length,
    arrives: async (which = 0) => {
      loading(which).give(start)
      await aMoment()
    },
    fails: async (why, which = 0) => {
      loading(which).refuse(why)
      await aMoment()
    },
    breaksAtTheStart: (why) => {
      broken = { why }
    },
    engines: () => started.map((engine) => ({ ...engine })),
    running: () => started.filter((engine) => engine.stops === 0).map((engine) => engine.surface),
  }
}
