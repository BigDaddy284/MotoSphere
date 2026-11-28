import { render } from '@testing-library/react'
import { Activity, StrictMode, Suspense, use } from 'react'
import { describe, expect, it } from 'vitest'
import { standInEngine, type StandIn } from '../test/engine.ts'
import { Globe } from './Globe.tsx'

/** What a test hands a globe to be told a failure with, and what it was told. */
function listener() {
  const told: unknown[] = []
  return {
    told,
    onFailed: (why: unknown) => {
      told.push(why)
    },
  }
}

/** What a test hands a globe to be told that the picture is drawn, and each time it was told. */
function watcher() {
  const told: unknown[][] = []
  return {
    told,
    onDrawn: (...given: unknown[]) => {
      told.push(given)
    },
  }
}

/** The component as it is written, to be read by a test. */
const written = import.meta.glob<string>('./Globe.tsx', {
  query: '?raw',
  import: 'default',
  eager: true,
})

/** Shows a globe the way React shows everything in development: twice. */
function shownTwice(engine: StandIn, onFailed: (why: unknown) => void) {
  return render(
    <StrictMode>
      <Globe load={engine.load} onFailed={onFailed} />
    </StrictMode>,
  )
}

const NEVER = new Promise<never>(() => {})

/** Something that is never ready to be shown, so that nothing beside it is shown either. */
function NeverReady(): never {
  return use(NEVER)
}

/** A moment in which anything that was wrongly left waiting would run. */
function aMoment(): Promise<void> {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, 20)
  })
}

describe('Globe', () => {
  it('is one empty element of the page and nothing else', () => {
    const engine = standInEngine()

    const { container } = render(<Globe load={engine.load} onFailed={listener().onFailed} />)

    expect(container.children).toHaveLength(1)
    expect(container.firstElementChild?.tagName).toBe('DIV')
    expect(container.firstElementChild).toBeEmptyDOMElement()
  })

  it('asks for the engine once when it is shown, and starts nothing while it loads', async () => {
    const engine = standInEngine()

    render(<Globe load={engine.load} onFailed={listener().onFailed} />)
    await aMoment()

    expect(engine.loadings()).toBe(1)
    expect(engine.engines()).toEqual([])
  })

  it('does not ask for the engine while it is only drawn and not shown', async () => {
    const engine = standInEngine()

    // React draws the globe, finds that what stands beside it is not ready,
    // and shows neither.
    const { container } = render(
      <Suspense fallback={<p>Not yet.</p>}>
        <Globe load={engine.load} onFailed={listener().onFailed} />
        <NeverReady />
      </Suspense>,
    )
    await aMoment()

    expect(container).toHaveTextContent('Not yet.')
    expect(container.querySelector('div')).toBeNull()
    expect(engine.loadings()).toBe(0)
  })

  it('starts one engine when it has arrived, in its own element, which is in the page', async () => {
    const engine = standInEngine()
    const { container } = render(<Globe load={engine.load} onFailed={listener().onFailed} />)

    await engine.arrives()

    expect(engine.engines()).toEqual([
      { surface: container.firstElementChild, inThePage: true, stops: 0 },
    ])
    expect(engine.engines()[0]?.surface).toBe(container.firstElementChild)
    expect(engine.loadings()).toBe(1)
  })

  it('tells nobody anything when the engine is loaded and started', async () => {
    const engine = standInEngine()
    const { told, onFailed } = listener()
    render(<Globe load={engine.load} onFailed={onFailed} />)

    await engine.arrives()

    expect(told).toEqual([])
  })

  it('keeps its element and its engine when it is shown again with the same things', async () => {
    const engine = standInEngine()
    const { onFailed } = listener()
    const { container, rerender } = render(<Globe load={engine.load} onFailed={onFailed} />)
    const element = container.firstElementChild
    await engine.arrives()

    rerender(<Globe load={engine.load} onFailed={onFailed} />)
    rerender(<Globe load={engine.load} onFailed={onFailed} />)
    await aMoment()

    expect(container.firstElementChild).toBe(element)
    expect(engine.loadings()).toBe(1)
    expect(engine.engines()).toEqual([{ surface: element, inThePage: true, stops: 0 }])
  })

  it('keeps its engine when whoever shows it hands it another listener', async () => {
    const engine = standInEngine()
    const { container, rerender } = render(
      <Globe load={engine.load} onFailed={listener().onFailed} />,
    )
    await engine.arrives()

    rerender(<Globe load={engine.load} onFailed={listener().onFailed} />)
    await aMoment()

    expect(engine.loadings()).toBe(1)
    expect(engine.engines()).toEqual([
      { surface: container.firstElementChild, inThePage: true, stops: 0 },
    ])
  })

  it('goes by the way of loading it was handed when it was shown, and not by a later one', async () => {
    const first = standInEngine()
    const later = standInEngine()
    const { onFailed } = listener()
    const { rerender } = render(<Globe load={first.load} onFailed={onFailed} />)

    rerender(<Globe load={later.load} onFailed={onFailed} />)
    await first.arrives()
    rerender(<Globe load={later.load} onFailed={onFailed} />)
    await aMoment()

    expect(first.loadings()).toBe(1)
    expect(first.running()).toHaveLength(1)
    expect(later.loadings()).toBe(0)
    expect(later.engines()).toEqual([])
  })

  it('stops its engine once when it goes', async () => {
    const engine = standInEngine()
    const { unmount } = render(<Globe load={engine.load} onFailed={listener().onFailed} />)
    await engine.arrives()

    unmount()
    await aMoment()

    expect(engine.engines().map(({ stops }) => stops)).toEqual([1])
    expect(engine.running()).toEqual([])
  })

  it('does not stop its engine before it goes', async () => {
    const engine = standInEngine()
    render(<Globe load={engine.load} onFailed={listener().onFailed} />)

    await engine.arrives()
    await aMoment()

    expect(engine.engines().map(({ stops }) => stops)).toEqual([0])
    expect(engine.running()).toHaveLength(1)
  })

  it('never starts an engine that arrives after it has gone', async () => {
    const engine = standInEngine()
    const { told, onFailed } = listener()
    const { unmount } = render(<Globe load={engine.load} onFailed={onFailed} />)

    unmount()
    await engine.arrives()
    await aMoment()

    expect(engine.loadings()).toBe(1)
    expect(engine.engines()).toEqual([])
    expect(told).toEqual([])
  })

  it('tells whoever shows it, once and with what went wrong, when the engine cannot be loaded', async () => {
    const engine = standInEngine()
    const why = new Error('The file could not be fetched.')
    const { told, onFailed } = listener()
    const { unmount } = render(<Globe load={engine.load} onFailed={onFailed} />)

    await engine.fails(why)
    await aMoment()

    expect(told).toEqual([why])
    expect(told[0]).toBe(why)
    expect(engine.engines()).toEqual([])

    unmount()
    await aMoment()

    expect(told).toEqual([why])
  })

  it('hands on whatever the loading failed with, an error or not', async () => {
    const engine = standInEngine()
    const { told, onFailed } = listener()
    render(<Globe load={engine.load} onFailed={onFailed} />)

    await engine.fails('offline')

    expect(told).toEqual(['offline'])
  })

  it('tells whoever shows it when the way of loading breaks before it gives anything', async () => {
    const why = new Error('There is no way to load the engine.')
    const { told, onFailed } = listener()

    render(
      <Globe
        load={() => {
          throw why
        }}
        onFailed={onFailed}
      />,
    )
    await aMoment()

    expect(told).toEqual([why])
  })

  it('tells nobody when the engine cannot be loaded for a globe that has gone', async () => {
    const engine = standInEngine()
    const { told, onFailed } = listener()
    const { unmount } = render(<Globe load={engine.load} onFailed={onFailed} />)

    unmount()
    await engine.fails(new Error('The file could not be fetched.'))
    await aMoment()

    expect(told).toEqual([])
    expect(engine.engines()).toEqual([])
  })

  it('tells whoever shows it, once, when the engine has arrived and cannot be started', async () => {
    const engine = standInEngine()
    const why = new Error('The browser gave no picture.')
    engine.breaksAtTheStart(why)
    const { told, onFailed } = listener()
    const { unmount } = render(<Globe load={engine.load} onFailed={onFailed} />)

    await engine.arrives()
    await aMoment()

    expect(told).toEqual([why])
    expect(told[0]).toBe(why)
    expect(engine.engines()).toEqual([])

    // There is no engine to stop, and going says nothing more.
    unmount()
    await aMoment()

    expect(told).toEqual([why])
  })

  it('tells the listener it has now, not the one it was first shown with', async () => {
    const engine = standInEngine()
    const first = listener()
    const now = listener()
    const why = new Error('The file could not be fetched.')
    const { rerender } = render(<Globe load={engine.load} onFailed={first.onFailed} />)

    rerender(<Globe load={engine.load} onFailed={now.onFailed} />)
    await engine.fails(why)

    expect(first.told).toEqual([])
    expect(now.told).toEqual([why])
  })

  it('loads and starts an engine anew when it is shown again after it has gone', async () => {
    const engine = standInEngine()
    const { onFailed } = listener()
    const first = render(<Globe load={engine.load} onFailed={onFailed} />)
    const firstElement = first.container.firstElementChild
    await engine.arrives(0)
    first.unmount()

    const again = render(<Globe load={engine.load} onFailed={onFailed} />)
    await engine.arrives(1)

    expect(engine.loadings()).toBe(2)
    expect(again.container.firstElementChild).not.toBe(firstElement)
    expect(engine.engines()).toEqual([
      { surface: firstElement, inThePage: true, stops: 1 },
      { surface: again.container.firstElementChild, inThePage: true, stops: 0 },
    ])
    expect(engine.running()).toEqual([again.container.firstElementChild])
  })

  it('has an engine of its own beside another globe, and only its own is stopped with it', async () => {
    const engine = standInEngine()
    const { onFailed } = listener()
    const one = render(<Globe load={engine.load} onFailed={onFailed} />)
    const other = render(<Globe load={engine.load} onFailed={onFailed} />)
    await engine.arrives(0)
    await engine.arrives(1)

    expect(engine.running()).toEqual([
      one.container.firstElementChild,
      other.container.firstElementChild,
    ])

    one.unmount()

    expect(engine.running()).toEqual([other.container.firstElementChild])
    expect(engine.engines().map(({ stops }) => stops)).toEqual([1, 0])
  })

  describe('where React shows it, takes it away and shows it again (StrictMode)', () => {
    it('asks for the engine twice and starts nothing while it loads', async () => {
      const engine = standInEngine()

      shownTwice(engine, listener().onFailed)
      await aMoment()

      expect(engine.loadings()).toBe(2)
      expect(engine.engines()).toEqual([])
    })

    it.each([
      { order: 'in the order they were asked for', sequence: [0, 1] },
      { order: 'the later one first', sequence: [1, 0] },
    ])('runs exactly one engine once both loadings have ended, $order', async ({ sequence }) => {
      const engine = standInEngine()
      const { told, onFailed } = listener()
      const { container } = shownTwice(engine, onFailed)

      for (const which of sequence) {
        await engine.arrives(which)
      }
      await aMoment()

      expect(engine.engines()).toEqual([
        { surface: container.firstElementChild, inThePage: true, stops: 0 },
      ])
      expect(told).toEqual([])
    })

    it('starts nothing for the loading of the globe that was taken away', async () => {
      const engine = standInEngine()
      shownTwice(engine, listener().onFailed)

      await engine.arrives(0)
      await aMoment()

      expect(engine.engines()).toEqual([])

      await engine.arrives(1)

      expect(engine.engines()).toHaveLength(1)
    })

    it('stops that one engine once when it goes', async () => {
      const engine = standInEngine()
      const { unmount } = shownTwice(engine, listener().onFailed)
      await engine.arrives(0)
      await engine.arrives(1)

      unmount()
      await aMoment()

      expect(engine.engines().map(({ stops }) => stops)).toEqual([1])
      expect(engine.running()).toEqual([])
    })

    it('tells of an engine that cannot be loaded once, though both loadings fail', async () => {
      const engine = standInEngine()
      const { told, onFailed } = listener()
      const why = new Error('The file could not be fetched.')
      shownTwice(engine, onFailed)

      await engine.fails(new Error('For the globe that was taken away.'), 0)
      await engine.fails(why, 1)
      await aMoment()

      expect(told).toEqual([why])
      expect(engine.engines()).toEqual([])
    })

    it('starts nothing when it goes while both loadings are still under way', async () => {
      const engine = standInEngine()
      const { told, onFailed } = listener()
      const { unmount } = shownTwice(engine, onFailed)

      unmount()
      await engine.arrives(0)
      await engine.arrives(1)
      await aMoment()

      expect(engine.engines()).toEqual([])
      expect(told).toEqual([])
    })
  })

  describe('when the engine has drawn its first complete picture', () => {
    it('tells nobody while the engine loads, nor when it has only been started', async () => {
      const engine = standInEngine()
      const { told, onDrawn } = watcher()
      render(<Globe load={engine.load} onDrawn={onDrawn} onFailed={listener().onFailed} />)
      await aMoment()

      expect(told).toEqual([])

      await engine.arrives()
      await aMoment()

      expect(engine.running()).toHaveLength(1)
      expect(told).toEqual([])
    })

    it('tells whoever shows it, once and with nothing else, when the engine says so', async () => {
      const engine = standInEngine()
      const { told, onDrawn } = watcher()
      const failure = listener()
      render(<Globe load={engine.load} onDrawn={onDrawn} onFailed={failure.onFailed} />)
      await engine.arrives()

      engine.draws()

      expect(told).toEqual([[]])
      expect(failure.told).toEqual([])
      expect(engine.engines().map(({ stops }) => stops)).toEqual([0])
    })

    it('tells it once, though the engine says it again and again', async () => {
      const engine = standInEngine()
      const { told, onDrawn } = watcher()
      render(<Globe load={engine.load} onDrawn={onDrawn} onFailed={listener().onFailed} />)
      await engine.arrives()

      engine.draws()
      engine.draws()
      engine.draws()
      await aMoment()

      expect(told).toHaveLength(1)
    })

    it('tells nobody what the engine says after the globe has gone', async () => {
      const engine = standInEngine()
      const { told, onDrawn } = watcher()
      const { unmount } = render(
        <Globe load={engine.load} onDrawn={onDrawn} onFailed={listener().onFailed} />,
      )
      await engine.arrives()

      unmount()
      engine.draws()
      await aMoment()

      expect(engine.engines().map(({ stops }) => stops)).toEqual([1])
      expect(told).toEqual([])
    })

    it('tells the listener it has now, not the one it was first shown with', async () => {
      const engine = standInEngine()
      const first = watcher()
      const now = watcher()
      const { onFailed } = listener()
      const { rerender } = render(
        <Globe load={engine.load} onDrawn={first.onDrawn} onFailed={onFailed} />,
      )
      await engine.arrives()

      rerender(<Globe load={engine.load} onDrawn={now.onDrawn} onFailed={onFailed} />)
      engine.draws()

      expect(first.told).toEqual([])
      expect(now.told).toEqual([[]])
    })

    it('keeps its engine when whoever shows it hands it another listener for the picture', async () => {
      const engine = standInEngine()
      const { onFailed } = listener()
      const { container, rerender } = render(
        <Globe load={engine.load} onDrawn={watcher().onDrawn} onFailed={onFailed} />,
      )
      await engine.arrives()

      rerender(<Globe load={engine.load} onDrawn={watcher().onDrawn} onFailed={onFailed} />)
      rerender(<Globe load={engine.load} onFailed={onFailed} />)
      await aMoment()

      expect(engine.loadings()).toBe(1)
      expect(engine.engines()).toEqual([
        { surface: container.firstElementChild, inThePage: true, stops: 0 },
      ])
    })

    it('can be shown by someone who does not ask: the engine says it, and nothing happens', async () => {
      const engine = standInEngine()
      const { told, onFailed } = listener()
      render(<Globe load={engine.load} onFailed={onFailed} />)
      await engine.arrives()

      expect(() => {
        engine.draws()
      }).not.toThrow()
      await aMoment()

      expect(told).toEqual([])
      expect(engine.running()).toHaveLength(1)
    })

    it('tells someone who asks only later, if the engine has not said it yet', async () => {
      const engine = standInEngine()
      const { told, onDrawn } = watcher()
      const { onFailed } = listener()
      const { rerender } = render(<Globe load={engine.load} onFailed={onFailed} />)
      await engine.arrives()

      rerender(<Globe load={engine.load} onDrawn={onDrawn} onFailed={onFailed} />)
      engine.draws()

      expect(told).toEqual([[]])
    })

    it('tells each of two globes of its own engine, and of no other', async () => {
      const engine = standInEngine()
      const one = watcher()
      const other = watcher()
      render(<Globe load={engine.load} onDrawn={one.onDrawn} onFailed={listener().onFailed} />)
      render(<Globe load={engine.load} onDrawn={other.onDrawn} onFailed={listener().onFailed} />)
      await engine.arrives(0)
      await engine.arrives(1)

      engine.draws(1)

      expect(one.told).toEqual([])
      expect(other.told).toEqual([[]])

      engine.draws(0)

      expect(one.told).toEqual([[]])
      expect(other.told).toEqual([[]])
    })

    it('tells a globe that is shown again after it has gone of its new engine only', async () => {
      const engine = standInEngine()
      const { onFailed } = listener()
      const before = watcher()
      const again = watcher()
      const first = render(
        <Globe load={engine.load} onDrawn={before.onDrawn} onFailed={onFailed} />,
      )
      await engine.arrives(0)
      first.unmount()
      render(<Globe load={engine.load} onDrawn={again.onDrawn} onFailed={onFailed} />)
      await engine.arrives(1)

      engine.draws(0)

      expect(before.told).toEqual([])
      expect(again.told).toEqual([])

      engine.draws(1)

      expect(before.told).toEqual([])
      expect(again.told).toEqual([[]])
    })

    it('tells a globe that React put aside and shows again of its new engine, a second time', async () => {
      const engine = standInEngine()
      const { told, onDrawn } = watcher()
      const { onFailed } = listener()
      // React keeps what it puts aside, the element too, and takes it out
      // of sight: for as long as that lasts the globe has gone.
      const shown = (mode: 'visible' | 'hidden') => (
        <Activity mode={mode}>
          <Globe load={engine.load} onDrawn={onDrawn} onFailed={onFailed} />
        </Activity>
      )
      const { container, rerender } = render(shown('visible'))
      const element = container.firstElementChild
      await engine.arrives(0)
      engine.draws(0)

      expect(told).toEqual([[]])

      rerender(shown('hidden'))
      engine.draws(0)

      expect(engine.running()).toEqual([])
      expect(told).toEqual([[]])

      rerender(shown('visible'))
      await engine.arrives(1)

      expect(container.firstElementChild).toBe(element)
      expect(engine.engines()).toEqual([
        { surface: element, inThePage: true, stops: 1 },
        { surface: element, inThePage: true, stops: 0 },
      ])
      expect(told).toEqual([[]])

      engine.draws(0)

      expect(told).toEqual([[]])

      engine.draws(1)
      engine.draws(1)

      expect(told).toEqual([[], []])
    })

    it.each([
      {
        what: 'cannot be loaded',
        goesWrong: (engine: StandIn) => engine.fails(new Error('The file could not be fetched.')),
      },
      {
        what: 'cannot be started',
        goesWrong: (engine: StandIn) => {
          engine.breaksAtTheStart(new Error('The browser gave no picture.'))
          return engine.arrives()
        },
      },
    ])('tells nobody that a picture is drawn when the engine $what', async ({ goesWrong }) => {
      const engine = standInEngine()
      const { told, onDrawn } = watcher()
      const failure = listener()
      render(<Globe load={engine.load} onDrawn={onDrawn} onFailed={failure.onFailed} />)

      await goesWrong(engine)
      await aMoment()

      expect(failure.told).toHaveLength(1)
      expect(told).toEqual([])
    })

    it('does not take a listener that fails for a failure of the engine', async () => {
      const engine = standInEngine()
      const why = new Error('Whoever shows the globe could not take it.')
      const failure = listener()
      let asked = 0
      render(
        <Globe
          load={engine.load}
          onDrawn={() => {
            asked += 1
            throw why
          }}
          onFailed={failure.onFailed}
        />,
      )
      await engine.arrives()

      // What the listener fails with goes back to the engine that said it.
      expect(() => {
        engine.draws()
      }).toThrow(why)
      await aMoment()

      expect(failure.told).toEqual([])
      expect(engine.engines().map(({ stops }) => stops)).toEqual([0])

      // And it was told: it is not told a second time.
      engine.draws()

      expect(asked).toBe(1)
    })

    describe('where React shows the globe, takes it away and shows it again (StrictMode)', () => {
      it.each([
        { order: 'in the order they were asked for', sequence: [0, 1] },
        { order: 'the later one first', sequence: [1, 0] },
      ])(
        'tells once, of the one engine that runs, when the loadings ended $order',
        async ({ sequence }) => {
          const engine = standInEngine()
          const { told, onDrawn } = watcher()
          render(
            <StrictMode>
              <Globe load={engine.load} onDrawn={onDrawn} onFailed={listener().onFailed} />
            </StrictMode>,
          )
          for (const which of sequence) {
            await engine.arrives(which)
          }

          expect(engine.engines()).toHaveLength(1)
          engine.draws()
          engine.draws()

          expect(told).toEqual([[]])
        },
      )

      it('tells nobody once it has gone', async () => {
        const engine = standInEngine()
        const { told, onDrawn } = watcher()
        const { unmount } = render(
          <StrictMode>
            <Globe load={engine.load} onDrawn={onDrawn} onFailed={listener().onFailed} />
          </StrictMode>,
        )
        await engine.arrives(0)
        await engine.arrives(1)

        unmount()
        engine.draws()

        expect(told).toEqual([])
      })
    })
  })

  it('names nothing of the engine itself: how it is loaded is handed to it', () => {
    const source = written['./Globe.tsx'] ?? ''

    expect(Object.keys(written)).toEqual(['./Globe.tsx'])
    expect(source).toContain('export function Globe(')
    expect(source).not.toMatch(/cesium/i)
    expect(source).not.toMatch(/\bimport\(/)
    expect([...source.matchAll(/from '([^']+)'/g)].map(([, from]) => from)).toEqual(['react'])
  })
})
