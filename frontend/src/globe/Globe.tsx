import { useEffect, useEffectEvent, useRef } from 'react'

/** Stops an engine that was started, and gives back what it held. */
export type Stop = () => void

/** Starts an engine in an element of the page, and gives the way to stop it. */
export type Start = (surface: HTMLElement) => Stop

/** Loads the engine, and gives the way to start one. */
export type Load = () => Promise<Start>

type GlobeProps = {
  /**
   * How the engine is loaded. It is asked when the globe is shown and not
   * before, and the way that was handed in then is the one that is used.
   */
  load: Load
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
 * it any more. React shows a component, takes it away and shows it again
 * in development; then two loadings are asked for, and only the engine of
 * the globe that stayed is started.
 */
export function Globe({ load, onFailed }: GlobeProps) {
  const surface = useRef<HTMLDivElement>(null)
  const loadTheEngine = useEffectEvent(load)
  const failed = useEffectEvent(onFailed)

  useEffect(() => {
    const element = surface.current
    let shown = true
    let stop: Stop | undefined

    async function begin(): Promise<void> {
      try {
        const start = await loadTheEngine()
        if (shown && element !== null) {
          stop = start(element)
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
