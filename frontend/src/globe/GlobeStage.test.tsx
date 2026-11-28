import { render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { describe, expect, it } from 'vitest'
import { browserGives, picturesAskedFor, picturesHeld } from '../test/drawing.ts'
import { GlobeStage, NO_GLOBE, NO_GLOBE_HELP } from './GlobeStage.tsx'

describe('GlobeStage', () => {
  it('shows nothing where the browser gives a 3D picture', () => {
    const { container } = render(<GlobeStage />)

    expect(container).toBeEmptyDOMElement()
  })

  it('says where the browser gives none that the globe cannot be shown, and then why', () => {
    browserGives([])

    const { container } = render(<GlobeStage />)

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

    render(<GlobeStage />)

    expect(screen.getByText(NO_GLOBE)).toBeVisible()
  })

  it('says it in plain words: two sentences, and no name of a technology', () => {
    expect(NO_GLOBE).toBe('The 3D globe cannot be shown in this browser.')
    expect(NO_GLOBE_HELP).toMatch(/^It needs 3D graphics, .*\. Try .*\.$/)
    expect(`${NO_GLOBE} ${NO_GLOBE_HELP}`).not.toMatch(/webgl|gpu|error|fail|cesium/i)
  })

  it('asks the browser when it is first shown and not when it is shown again', () => {
    const { rerender } = render(<GlobeStage />)
    expect(picturesAskedFor()).toEqual(['webgl2'])

    rerender(<GlobeStage />)
    rerender(<GlobeStage />)

    expect(picturesAskedFor()).toEqual(['webgl2'])
  })

  it('keeps what the browser said when it was first shown', () => {
    browserGives([])
    const { rerender } = render(<GlobeStage />)

    browserGives(['webgl2'])
    rerender(<GlobeStage />)

    expect(screen.getByText(NO_GLOBE)).toBeVisible()
  })

  it('holds no 3D picture once it is shown', () => {
    render(<GlobeStage />)

    expect(picturesHeld()).toBe(0)
  })

  it('holds no 3D picture and says it once where React shows it twice', () => {
    browserGives(['webgl2'])
    const first = render(
      <StrictMode>
        <GlobeStage />
      </StrictMode>,
    )
    expect(picturesAskedFor().length).toBeGreaterThan(0)
    expect(picturesHeld()).toBe(0)
    expect(first.container).toBeEmptyDOMElement()
    first.unmount()

    browserGives([])
    render(
      <StrictMode>
        <GlobeStage />
      </StrictMode>,
    )
    expect(screen.getAllByText(NO_GLOBE)).toHaveLength(1)
    expect(screen.getAllByText(NO_GLOBE_HELP)).toHaveLength(1)
  })
})
