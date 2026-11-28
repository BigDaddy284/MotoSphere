import { act, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { APP_NAME } from './App.tsx'

// The real engine draws, which the test environment cannot. In its place
// stands one that only notes where it was started.
const startedIn = vi.hoisted((): HTMLElement[] => [])
vi.mock('./globe/earth.ts', () => ({
  start: (surface: HTMLElement) => {
    startedIn.push(surface)
    return () => {}
  },
}))

// main.tsx runs as soon as it is imported, so every test prepares the
// document first and then imports a fresh copy of the module.
describe('entry point', () => {
  beforeEach(() => {
    vi.resetModules()
    // The page asks for the published data as soon as it is shown. These
    // tests are not about the data, so the answer never comes.
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))
  })

  afterEach(() => {
    document.body.replaceChildren()
    startedIn.length = 0
  })

  it('renders the application into the root element', async () => {
    const root = document.createElement('div')
    root.id = 'root'
    document.body.append(root)

    // Inside `act`, React does all it has to do before the test goes on:
    // the page is shown in full, and nothing of it is left waiting that
    // could run after the test's document is gone.
    await act(async () => {
      await import('./main.tsx')
    })

    expect(screen.getByRole('heading', { level: 1, name: APP_NAME })).toBeVisible()
  })

  it('hands the application the engine of the globe, which is fetched when the globe is shown', async () => {
    const root = document.createElement('div')
    root.id = 'root'
    document.body.append(root)

    await act(async () => {
      await import('./main.tsx')
    })
    await vi.waitFor(() => {
      expect(startedIn).toHaveLength(1)
    })

    const stage = screen.getByRole('main', { name: 'Globe' })
    expect(startedIn[0]).toBe(stage.firstElementChild?.firstElementChild)
    expect(startedIn[0]).not.toBeUndefined()
  })

  it('fails with a clear message when the root element is missing', async () => {
    await expect(import('./main.tsx')).rejects.toThrow('no element with id "root"')
  })
})
