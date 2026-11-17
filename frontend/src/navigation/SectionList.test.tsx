import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SectionList } from './SectionList.tsx'
import { DEFAULT_SECTION, SECTIONS, type SectionId } from './sections.ts'

const LABELS = [
  'Explore',
  'Events',
  'Tracks',
  'Championships',
  'Riders',
  'Teams',
  'Results',
  'News',
  'Statistics',
]

describe('sections', () => {
  it('are the nine sections of the application, in order', () => {
    expect(SECTIONS.map((section) => section.label)).toEqual(LABELS)
  })

  it('have unique identifiers', () => {
    const ids = SECTIONS.map((section) => section.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('start with Explore', () => {
    expect(DEFAULT_SECTION).toBe('explore')
  })
})

describe('SectionList', () => {
  it('lists every section as a button, in order', () => {
    render(<SectionList current="explore" onSelect={() => {}} />)

    expect(screen.getAllByRole('listitem')).toHaveLength(9)
    expect(screen.getAllByRole('button').map((button) => button.textContent)).toEqual(LABELS)
  })

  it('marks only the current section as current', () => {
    render(<SectionList current="riders" onSelect={() => {}} />)

    const current = screen
      .getAllByRole('button')
      .filter((button) => button.hasAttribute('aria-current'))
    expect(current.map((button) => button.textContent)).toEqual(['Riders'])
    expect(current[0]).toHaveAttribute('aria-current', 'page')
  })

  it('reports the section that was clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn<(section: SectionId) => void>()
    render(<SectionList current="explore" onSelect={onSelect} />)

    await user.click(screen.getByRole('button', { name: 'Tracks' }))

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith('tracks')
  })

  it('reports the section chosen with the Enter key', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn<(section: SectionId) => void>()
    render(<SectionList current="explore" onSelect={onSelect} />)

    await user.tab()
    await user.tab()
    expect(screen.getByRole('button', { name: 'Events' })).toHaveFocus()
    await user.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith('events')
  })

  it('reports the section chosen with the Space key', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn<(section: SectionId) => void>()
    render(<SectionList current="riders" onSelect={onSelect} />)

    await user.tab()
    expect(screen.getByRole('button', { name: 'Explore' })).toHaveFocus()
    await user.keyboard(' ')

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith('explore')
  })
})
