import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { APP_NAME, APP_TAGLINE, App } from './App.tsx'
import { NO_GLOBE, NO_GLOBE_HELP } from './globe/GlobeStage.tsx'
import { browserGives } from './test/drawing.ts'

/** The labels of the sections marked as current. */
function currentSections() {
  const sections = screen.getByRole('navigation', { name: 'Sections' })
  return within(sections)
    .getAllByRole('button')
    .filter((button) => button.hasAttribute('aria-current'))
    .map((button) => button.textContent)
}

describe('App', () => {
  beforeEach(() => {
    // The page asks for the published data as soon as it is shown. These
    // tests are not about the data, so the answer never comes.
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the application name as the main heading', () => {
    render(<App />)

    expect(screen.getByRole('heading', { level: 1, name: APP_NAME })).toBeVisible()
  })

  it('shows the tagline', () => {
    render(<App />)

    expect(screen.getByText(APP_TAGLINE)).toBeVisible()
  })

  it('has exactly one main landmark', () => {
    render(<App />)

    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('has an empty globe stage where the browser gives a 3D picture', () => {
    render(<App />)

    expect(screen.getByRole('main', { name: 'Globe' })).toBeEmptyDOMElement()
    expect(screen.queryByText(NO_GLOBE)).not.toBeInTheDocument()
  })

  it('says in the globe stage, and nowhere else, that the globe cannot be shown where the browser gives none', () => {
    browserGives([])

    render(<App />)

    const stage = screen.getByRole('main', { name: 'Globe' })
    expect(within(stage).getByText(NO_GLOBE)).toBeVisible()
    expect(within(stage).getByText(NO_GLOBE_HELP)).toBeVisible()
    expect(screen.getAllByText(NO_GLOBE)).toHaveLength(1)
  })

  it('works as before where the globe cannot be shown: the sections and both panels', async () => {
    browserGives([])
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Championships' }))
    expect(currentSections()).toEqual(['Championships'])

    await user.click(screen.getByRole('button', { name: 'Sections' }))
    expect(screen.queryByRole('navigation', { name: 'Sections' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Details' }))
    expect(screen.queryByRole('complementary', { name: 'Details' })).not.toBeInTheDocument()

    expect(screen.getByText(NO_GLOBE)).toBeVisible()
  })

  it('starts in the Explore section', () => {
    render(<App />)

    expect(currentSections()).toEqual(['Explore'])
  })

  it('moves to the section the user clicks', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Championships' }))

    expect(currentSections()).toEqual(['Championships'])
  })

  it('moves to the section the user chooses with the keyboard', async () => {
    const user = userEvent.setup()
    render(<App />)

    screen.getByRole('button', { name: 'Explore' }).focus()
    await user.tab()
    await user.keyboard('{Enter}')
    expect(currentSections()).toEqual(['Events'])

    await user.tab()
    await user.keyboard(' ')
    expect(currentSections()).toEqual(['Tracks'])
  })

  it("shows today's date in the top bar", () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 17, 9, 30))

    render(<App />)

    const date = screen.getByRole('banner').querySelector('time:not(output time)')
    expect(date).not.toBeNull()
    expect(date).toBeVisible()
    expect(date).toHaveAttribute('datetime', '2026-11-17')
    expect(date?.textContent).toContain('2026')
  })

  it('shows the data status in the top bar, before the date', async () => {
    const manifest = {
      format_version: 1,
      generated_at: '2026-11-17T12:53:59Z',
      application_version: '0.1.0',
      counts: {},
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(manifest)))

    render(<App />)

    const topBar = screen.getByRole('banner')
    const status = within(topBar).getByRole('status')
    expect(status).toHaveTextContent('Loading data…')
    expect(await within(status).findByText(/2026/)).toHaveAttribute(
      'datetime',
      '2026-11-17T12:53:59Z',
    )
    expect(status).toHaveTextContent(/^Data updated /)
    const date = topBar.querySelector('time:not(output time)')
    expect(date).not.toBeNull()
    expect(status.compareDocumentPosition(date as Node)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
  })
})
