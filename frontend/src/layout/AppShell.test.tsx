import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AppShell } from './AppShell.tsx'

function renderShell() {
  return render(
    <AppShell name="Test name" tagline="Test tagline" sections={<p>Test sections</p>} />,
  )
}

describe('AppShell', () => {
  it('shows the name as the main heading, with the tagline, in the top bar', () => {
    renderShell()

    const topBar = screen.getByRole('banner')
    expect(within(topBar).getByRole('heading', { level: 1, name: 'Test name' })).toBeVisible()
    expect(within(topBar).getByText('Test tagline')).toBeVisible()
  })

  it('shows the sections content inside the sections panel', () => {
    renderShell()

    const sections = screen.getByRole('navigation', { name: 'Sections' })
    expect(within(sections).getByText('Test sections')).toBeVisible()
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

/** The button in the top bar that closes and opens a side panel. */
function panelButton(name: 'Sections' | 'Details') {
  return within(screen.getByRole('banner')).getByRole('button', { name })
}

/** The sections panel, or null when it is closed. */
function sectionsPanel() {
  return screen.queryByRole('navigation', { name: 'Sections' })
}

/** The details panel, or null when it is closed. */
function detailsPanel() {
  return screen.queryByRole('complementary', { name: 'Details' })
}

describe('AppShell side panels', () => {
  it('start open, each with a button in the top bar that controls it', () => {
    renderShell()

    const sectionsButton = panelButton('Sections')
    const detailsButton = panelButton('Details')
    expect(sectionsButton).toHaveAttribute('aria-expanded', 'true')
    expect(detailsButton).toHaveAttribute('aria-expanded', 'true')

    const sections = sectionsPanel()
    const details = detailsPanel()
    expect(sections).toBeVisible()
    expect(details).toBeVisible()
    expect(sectionsButton).toHaveAttribute('aria-controls', sections?.id)
    expect(detailsButton).toHaveAttribute('aria-controls', details?.id)
    expect(sections?.id).toBeTruthy()
    expect(details?.id).toBeTruthy()
    expect(sections?.id).not.toBe(details?.id)
  })

  it('closes the sections panel, and only that panel, with its button', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(panelButton('Sections'))

    expect(sectionsPanel()).toBeNull()
    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'false')
    expect(detailsPanel()).toBeVisible()
    expect(panelButton('Details')).toHaveAttribute('aria-expanded', 'true')
  })

  it('closes the details panel, and only that panel, with its button', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(panelButton('Details'))

    expect(detailsPanel()).toBeNull()
    expect(panelButton('Details')).toHaveAttribute('aria-expanded', 'false')
    expect(sectionsPanel()).toBeVisible()
    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'true')
  })

  it('opens a closed panel again with the same button, with its content', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(panelButton('Sections'))
    await user.click(panelButton('Sections'))

    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Test sections')).toBeVisible()
  })

  it('keeps a closed panel in the page, hidden, so the button still points at it', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(panelButton('Details'))

    const controlled = document.getElementById(
      panelButton('Details').getAttribute('aria-controls') ?? '',
    )
    expect(controlled?.tagName).toBe('ASIDE')
    expect(controlled).not.toBeVisible()
  })

  it('works with the Enter and Space keys', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.tab()
    expect(panelButton('Sections')).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'false')
    expect(sectionsPanel()).toBeNull()
    await user.keyboard(' ')
    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'true')
    expect(sectionsPanel()).toBeVisible()

    await user.tab()
    expect(panelButton('Details')).toHaveFocus()
    await user.keyboard(' ')
    expect(panelButton('Details')).toHaveAttribute('aria-expanded', 'false')
    expect(detailsPanel()).toBeNull()
    await user.keyboard('{Enter}')
    expect(panelButton('Details')).toHaveAttribute('aria-expanded', 'true')
    expect(detailsPanel()).toBeVisible()
  })

  it('remembers closed panels when the page is loaded again in the same session', async () => {
    const user = userEvent.setup()
    const { unmount } = renderShell()

    await user.click(panelButton('Details'))
    unmount()
    renderShell()

    expect(panelButton('Details')).toHaveAttribute('aria-expanded', 'false')
    expect(detailsPanel()).toBeNull()
    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'true')
    expect(sectionsPanel()).toBeVisible()
  })

  it('remembers a panel that was closed and opened again as open', async () => {
    const user = userEvent.setup()
    const { unmount } = renderShell()

    await user.click(panelButton('Sections'))
    await user.click(panelButton('Sections'))
    unmount()
    renderShell()

    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'true')
    expect(sectionsPanel()).toBeVisible()
  })

  it('starts open when the remembered value is not one it wrote', () => {
    window.sessionStorage.setItem('motosphere.panel.sections', '<script>alert(1)</script>')
    window.sessionStorage.setItem('motosphere.panel.details', '')

    renderShell()

    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'true')
    expect(sectionsPanel()).toBeVisible()
    expect(panelButton('Details')).toHaveAttribute('aria-expanded', 'true')
    expect(detailsPanel()).toBeVisible()
  })

  it('starts open and still works when the browser refuses to store anything', async () => {
    const getItem = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage is disabled')
    })
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage is disabled')
    })
    const user = userEvent.setup()
    renderShell()

    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'true')
    expect(sectionsPanel()).toBeVisible()

    await user.click(panelButton('Sections'))

    expect(panelButton('Sections')).toHaveAttribute('aria-expanded', 'false')
    expect(sectionsPanel()).toBeNull()
    expect(getItem).toHaveBeenCalled()
    expect(setItem).toHaveBeenCalled()
  })
})
