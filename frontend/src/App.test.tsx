import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { APP_NAME, APP_TAGLINE, App } from './App.tsx'

/** The labels of the sections marked as current. */
function currentSections() {
  const sections = screen.getByRole('navigation', { name: 'Sections' })
  return within(sections)
    .getAllByRole('button')
    .filter((button) => button.hasAttribute('aria-current'))
    .map((button) => button.textContent)
}

describe('App', () => {
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

    await user.tab()
    await user.tab()
    await user.keyboard('{Enter}')
    expect(currentSections()).toEqual(['Events'])

    await user.tab()
    await user.keyboard(' ')
    expect(currentSections()).toEqual(['Tracks'])
  })
})
