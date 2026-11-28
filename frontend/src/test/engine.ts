import type { Listener, Load, Start } from '../globe/Globe.tsx'

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
  /**
   * An engine says that its first complete picture is drawn: the one
   * started first, or the one named. It says so whether it was stopped or
   * not, and as often as the test has it say so.
   */
  draws: (which?: number) => void
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

/** What a test is told that names an engine that was not started. */
export function noSuchEngine(started: number, which: number): string {
  return `${started} engines were started, so there is no engine number ${which}.`
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
 * loaded when the test says so, well or badly, remembers where it was
 * started and how often it was stopped, and says that its picture is drawn
 * when the test says so. Nothing of the real engine is in it.
 */
export function standInEngine(): StandIn {
  const asked: Loading[] = []
  const started: Engine[] = []
  // Whom each engine was handed to say things to, in the same order.
  const listeners: Listener[] = []
  let broken: { why: unknown } | undefined

  const start: Start = (surface, listener) => {
    if (broken !== undefined) {
      throw broken.why
    }
    const engine = { surface, inThePage: surface.isConnected, stops: 0 }
    started.push(engine)
    listeners.push(listener)
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
    draws: (which = 0) => {
      const listener = listeners[which]
      if (listener === undefined) {
        throw new Error(noSuchEngine(started.length, which))
      }
      listener.drawn()
    },
    engines: () => started.map((engine) => ({ ...engine })),
    running: () => started.filter((engine) => engine.stops === 0).map((engine) => engine.surface),
  }
}
