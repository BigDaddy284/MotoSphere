import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AppShell } from './AppShell.tsx'

function renderShell() {
  return render(<AppShell name="Test name" tagline="Test tagline" />)
}

describe('AppShell', () => {
  it('shows the name as the main heading, with the tagline, in the top bar', () => {
    renderShell()

    const topBar = screen.getByRole('banner')
    expect(within(topBar).getByRole('heading', { level: 1, name: 'Test name' })).toBeVisible()
    expect(within(topBar).getByText('Test tagline')).toBeVisible()
  })

  it('has a sections panel', () => {
    renderShell()

    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeInTheDocument()
  })

  it('has the globe stage as the main region', () => {
    renderShell()

    expect(screen.getByRole('main', { name: 'Globe' })).toBeInTheDocument()
  })

  it('has a details panel that says how to fill it', () => {
    renderShell()

    const details = screen.getByRole('complementary', { name: 'Details' })
    expect(
      within(details).getByText('Select something on the globe to see its details here.'),
    ).toBeVisible()
  })

  it('has exactly one of each region', () => {
    renderShell()

    expect(screen.getAllByRole('banner')).toHaveLength(1)
    expect(screen.getAllByRole('navigation')).toHaveLength(1)
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(screen.getAllByRole('complementary')).toHaveLength(1)
  })

  it('puts the regions in reading order: top bar, sections, globe, details', () => {
    const { container } = renderShell()

    const regions = [...container.querySelectorAll('header, nav, main, aside')].map((element) =>
      element.tagName.toLowerCase(),
    )
    expect(regions).toEqual(['header', 'nav', 'main', 'aside'])
  })
})
