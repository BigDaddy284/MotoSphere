import { useEffect, useEffectEvent, useRef } from 'react'

/** Stops an engine that was started, and gives back what it held. */
export type Stop = () => void

/** What an engine that is started is handed, to say what it has to say. */
export type Listener = {
  /** Said when the engine has drawn its first complete picture. */
  drawn: () => void
}

/**
 * Starts an engine in an element of the page, and gives the way to stop it.
 * What the engine has to say afterwards it says to the listener.
 */
export type Start = (surface: HTMLElement, listener: Listener) => Stop

/** Loads the engine, and gives the way to start one. */
export type Load = () => Promise<Start>

type GlobeProps = {
  /**
   * How the engine is loaded. It is asked when the globe is shown and not
   * before, and the way that was handed in then is the one that is used.
   */
  load: Load
  /**
   * Told once, when the engine has drawn its first complete picture for a
   * globe that is still shown. Whoever shows the globe need not ask.
   */
  onDrawn?: () => void
  /**
   * Told once, with what went wrong, when the engine cannot be loaded or
   * started for a globe that is still shown.
   */
  onFailed: (why: unknown) => void
}

/**
 * The globe: one element of the page, and one engine that draws in it for
 * as long as the globe is shown.
 *
 * The engine is loaded when the globe is shown and started in the element
 * when it has arrived. When the globe goes, the engine is stopped. A globe
 * can go before its engine has arrived: that engine is then never started,
 * and if it cannot be loaded nobody is told, because nobody is waiting for
 * it any more. Nor is anybody told what an engine says after its globe has
 * gone. React shows a component, takes it away and shows it again
 * in development; then two loadings are asked for, and only the engine of
 * the globe that stayed is started.
 */
export function Globe({ load, onDrawn, onFailed }: GlobeProps) {
  const surface = useRef<HTMLDivElement>(null)
  const loadTheEngine = useEffectEvent(load)
  const drawn = useEffectEvent(() => {
    onDrawn?.()
  })
  const failed = useEffectEvent(onFailed)

  useEffect(() => {
    const element = surface.current
    let shown = true
    let toldItIsDrawn = false
    let stop: Stop | undefined
    const listener: Listener = {
      drawn: () => {
        if (shown && !toldItIsDrawn) {
          toldItIsDrawn = true
          drawn()
        }
      },
    }

    async function begin(): Promise<void> {
      try {
        const start = await loadTheEngine()
        if (shown && element !== null) {
          stop = start(element, listener)
        }
      } catch (why) {
        if (shown) {
          failed(why)
        }
      }
    }
    void begin()

    return () => {
      shown = false
      stop?.()
    }
  }, [])

  return <div ref={surface} />
}
