import { act, render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { describe, expect, it, onTestFinished } from 'vitest'
import { browserGives, picturesAskedFor, picturesHeld } from '../test/drawing.ts'
import { standInEngine } from '../test/engine.ts'
import { GlobeStage, NO_GLOBE, NO_GLOBE_HELP } from './GlobeStage.tsx'

/** The element of the stage that says whether the globe is still being drawn. */
function globe(container: HTMLElement): Element {
  const found = container.querySelector('[aria-busy]')
  if (found === null) {
    throw new Error('The stage shows no globe.')
  }
  return found
}

/**
 * Listens, until the test is over, for what the page hands the browser as a
 * failure that nobody caught, and takes each as dealt with.
 */
function handedToTheBrowser(): unknown[] {
  const handed: unknown[] = []
  const listen = (event: ErrorEvent) => {
    handed.push(event.error)
    event.preventDefault()
  }
  window.addEventListener('error', listen)
  onTestFinished(() => {
    window.removeEventListener('error', listen)
  })
  return handed
}

describe('GlobeStage', () => {
  describe('where the browser gives a 3D picture', () => {
    it('shows the globe and nothing else: one element, and in it the surface, empty', () => {
      const engine = standInEngine()

      const { container } = render(<GlobeStage loadTheEngine={engine.load} />)

      expect(container.children).toHaveLength(1)
      expect(container.firstElementChild).toBe(globe(container))
      expect(globe(container).children).toHaveLength(1)
      expect(globe(container).firstElementChild?.tagName).toBe('DIV')
      expect(globe(container).firstElementChild).toBeEmptyDOMElement()
      expect(screen.queryByText(NO_GLOBE)).not.toBeInTheDocument()
      expect(screen.queryByText(NO_GLOBE_HELP)).not.toBeInTheDocument()
    })

    it('asks for the engine once, with the way it was handed', () => {
      const engine = standInEngine()

      const { rerender } = render(<GlobeStage loadTheEngine={engine.load} />)
      rerender(<GlobeStage loadTheEngine={engine.load} />)

      expect(engine.loadings()).toBe(1)
    })

    it('starts the engine in the surface when it has arrived', async () => {
      const engine = standInEngine()
      const { container } = render(<GlobeStage loadTheEngine={engine.load} />)
      expect(engine.engines()).toEqual([])

      await engine.arrives()

      expect(engine.engines()).toEqual([
        { surface: globe(container).firstElementChild, inThePage: true, stops: 0 },
      ])
    })

    it('says that the globe is busy until the engine has drawn its first complete picture', async () => {
      const engine = standInEngine()
      const { container } = render(<GlobeStage loadTheEngine={engine.load} />)
      expect(globe(container)).toHaveAttribute('aria-busy', 'true')

      await engine.arrives()
      expect(globe(container)).toHaveAttribute('aria-busy', 'true')

      act(() => {
        engine.draws()
      })
      expect(globe(container)).toHaveAttribute('aria-busy', 'false')
    })

    it('does not say it again afterwards, and keeps the surface and the engine it has', async () => {
      const engine = standInEngine()
      const { container, rerender } = render(<GlobeStage loadTheEngine={engine.load} />)
      const surface = globe(container).firstElementChild
      await engine.arrives()
      act(() => {
        engine.draws()
      })

      rerender(<GlobeStage loadTheEngine={engine.load} />)
      act(() => {
        engine.draws()
      })

      expect(globe(container)).toHaveAttribute('aria-busy', 'false')
      expect(globe(container).firstElementChild).toBe(surface)
      expect(engine.loadings()).toBe(1)
      expect(engine.engines()).toEqual([{ surface, inThePage: true, stops: 0 }])
    })

    it('stops the engine when the stage goes', async () => {
      const engine = standInEngine()
      const { unmount } = render(<GlobeStage loadTheEngine={engine.load} />)
      await engine.arrives()

      unmount()

      expect(engine.engines().map((started) => started.stops)).toEqual([1])
    })

    it('hands an engine that cannot be loaded to the browser, and stays busy', async () => {
      const handed = handedToTheBrowser()
      const engine = standInEngine()
      const why = new Error('the engine did not arrive')
      const { container } = render(<GlobeStage loadTheEngine={engine.load} />)

      await engine.fails(why)

      expect(handed).toEqual([why])
      expect(handed[0]).toBe(why)
      expect(globe(container)).toHaveAttribute('aria-busy', 'true')
      expect(screen.queryByText(NO_GLOBE)).not.toBeInTheDocument()
    })

    it('hands an engine that cannot be started to the browser, and stays busy', async () => {
      const handed = handedToTheBrowser()
      const engine = standInEngine()
      const why = new Error('the engine did not start')
      engine.breaksAtTheStart(why)
      const { container } = render(<GlobeStage loadTheEngine={engine.load} />)

      await engine.arrives()

      expect(handed).toEqual([why])
      expect(handed[0]).toBe(why)
      expect(globe(container)).toHaveAttribute('aria-busy', 'true')
    })

    it('hands the browser nothing while all goes well', async () => {
      const handed = handedToTheBrowser()
      const engine = standInEngine()
      render(<GlobeStage loadTheEngine={engine.load} />)

      await engine.arrives()
      act(() => {
        engine.draws()
      })

      expect(handed).toEqual([])
    })

    it('holds no 3D picture once it is shown', () => {
      render(<GlobeStage loadTheEngine={standInEngine().load} />)

      expect(picturesHeld()).toBe(0)
    })
  })

  describe('where the browser gives none', () => {
    it('says that the globe cannot be shown, and then why', () => {
      browserGives([])

      const { container } = render(<GlobeStage loadTheEngine={standInEngine().load} />)

      expect(screen.getByText(NO_GLOBE)).toBeVisible()
      expect(screen.getByText(NO_GLOBE_HELP)).toBeVisible()
      expect([...container.querySelectorAll('p')].map((line) => line.textContent)).toEqual([
        NO_GLOBE,
        NO_GLOBE_HELP,
      ])
      expect(container).toHaveTextContent(`${NO_GLOBE}${NO_GLOBE_HELP}`, {
        normalizeWhitespace: false,
      })
    })

    it('says the same where the browser gives only the older kind of 3D picture', () => {
      browserGives(['webgl'])

      render(<GlobeStage loadTheEngine={standInEngine().load} />)

      expect(screen.getByText(NO_GLOBE)).toBeVisible()
    })

    it('does not ask for the engine, and shows no globe that could be busy', async () => {
      browserGives([])
      const engine = standInEngine()

      const { container, rerender } = render(<GlobeStage loadTheEngine={engine.load} />)
      rerender(<GlobeStage loadTheEngine={engine.load} />)
      await act(async () => {})

      expect(engine.loadings()).toBe(0)
      expect(container.querySelector('[aria-busy]')).toBeNull()
    })
  })

  it('says it in plain words: two sentences, and no name of a technology', () => {
    expect(NO_GLOBE).toBe('The 3D globe cannot be shown in this browser.')
    expect(NO_GLOBE_HELP).toMatch(/^It needs 3D graphics, .*\. Try .*\.$/)
    expect(`${NO_GLOBE} ${NO_GLOBE_HELP}`).not.toMatch(/webgl|gpu|error|fail|cesium/i)
  })

  it('asks the browser when it is first shown and not when it is shown again', () => {
    const engine = standInEngine()
    const { rerender } = render(<GlobeStage loadTheEngine={engine.load} />)
    expect(picturesAskedFor()).toEqual(['webgl2'])

    rerender(<GlobeStage loadTheEngine={engine.load} />)
    rerender(<GlobeStage loadTheEngine={engine.load} />)

    expect(picturesAskedFor()).toEqual(['webgl2'])
  })

  it('keeps what the browser said when it was first shown', () => {
    browserGives([])
    const engine = standInEngine()
    const { rerender } = render(<GlobeStage loadTheEngine={engine.load} />)

    browserGives(['webgl2'])
    rerender(<GlobeStage loadTheEngine={engine.load} />)

    expect(screen.getByText(NO_GLOBE)).toBeVisible()
    expect(engine.loadings()).toBe(0)
  })

  it('shows one globe with one engine, and says it once, where React shows it twice', async () => {
    browserGives(['webgl2'])
    const engine = standInEngine()
    const first = render(
      <StrictMode>
        <GlobeStage loadTheEngine={engine.load} />
      </StrictMode>,
    )
    expect(picturesAskedFor().length).toBeGreaterThan(0)
    expect(picturesHeld()).toBe(0)
    expect(first.container.querySelectorAll('[aria-busy]')).toHaveLength(1)
    await engine.arrives(0)
    await engine.arrives(1)
    expect(engine.running()).toEqual([globe(first.container).firstElementChild])
    first.unmount()

    browserGives([])
    render(
      <StrictMode>
        <GlobeStage loadTheEngine={standInEngine().load} />
      </StrictMode>,
    )
    expect(screen.getAllByText(NO_GLOBE)).toHaveLength(1)
    expect(screen.getAllByText(NO_GLOBE_HELP)).toHaveLength(1)
  })
})
