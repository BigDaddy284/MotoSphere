import { act, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CurrentDate } from './CurrentDate.tsx'
import { formatDay } from './today.ts'

const HOUR = 60 * 60 * 1000
const DAY = 24 * HOUR

/** The `time` element the component renders. */
function timeElement(container: HTMLElement): HTMLTimeElement {
  const element = container.querySelector('time')
  if (element === null) {
    throw new Error('The component rendered no time element.')
  }
  return element
}

/** Moves the fake clock on, running every timer that falls due. */
function advance(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms)
  })
}

describe('CurrentDate', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it("shows today's date, written out, with the day in machine-readable form", () => {
    vi.setSystemTime(new Date(2026, 10, 17, 14, 30))

    const { container } = render(<CurrentDate />)

    const time = timeElement(container)
    expect(time).toHaveAttribute('datetime', '2026-11-17')
    expect(time.textContent).toBe(formatDay('2026-11-17'))
    expect(time.textContent).toContain('17')
    expect(time.textContent).toContain('2026')
  })

  it('changes at midnight without being loaded again', () => {
    vi.setSystemTime(new Date(2026, 10, 17, 23, 59, 50))
    const { container } = render(<CurrentDate />)

    advance(9_999)
    expect(timeElement(container)).toHaveAttribute('datetime', '2026-11-17')

    advance(1)
    expect(timeElement(container)).toHaveAttribute('datetime', '2026-11-18')
    expect(timeElement(container).textContent).toBe(formatDay('2026-11-18'))
  })

  it('keeps changing at every following midnight', () => {
    vi.setSystemTime(new Date(2026, 10, 17, 23, 59, 50))
    const { container } = render(<CurrentDate />)

    advance(10_000)
    advance(DAY)
    expect(timeElement(container)).toHaveAttribute('datetime', '2026-11-19')

    advance(DAY)
    expect(timeElement(container)).toHaveAttribute('datetime', '2026-11-20')
  })

  it('catches up when the page comes back into view after the device slept', () => {
    vi.setSystemTime(new Date(2026, 10, 17, 22, 0))
    const { container } = render(<CurrentDate />)

    // Moving the clock runs no timers, as when a device sleeps.
    vi.setSystemTime(new Date(2026, 10, 19, 8, 0))
    expect(timeElement(container)).toHaveAttribute('datetime', '2026-11-17')

    act(() => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    expect(timeElement(container)).toHaveAttribute('datetime', '2026-11-19')

    advance(16 * HOUR)
    expect(timeElement(container)).toHaveAttribute('datetime', '2026-11-20')
  })

  it('leaves no timer and no listener behind when it is removed', () => {
    const added = vi.spyOn(document, 'addEventListener')
    const removed = vi.spyOn(document, 'removeEventListener')
    const visibilityCalls = (spy: typeof added | typeof removed) =>
      spy.mock.calls.filter(([type]) => type === 'visibilitychange').length
    vi.setSystemTime(new Date(2026, 10, 17, 14, 30))

    const { unmount } = render(<CurrentDate />)
    expect(vi.getTimerCount()).toBe(1)
    expect(visibilityCalls(added)).toBe(1)

    unmount()
    expect(vi.getTimerCount()).toBe(0)
    expect(visibilityCalls(removed)).toBe(visibilityCalls(added))
  })
})
