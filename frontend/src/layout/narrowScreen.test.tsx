import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { screenWatchers, showScreen } from '../test/screen.ts'
import styleSheet from './AppShell.module.css?raw'
import { NARROW_SCREEN, useNarrowScreen } from './narrowScreen.ts'

function Probe() {
  return <p>{useNarrowScreen() ? 'narrow' : 'wide'}</p>
}

describe('useNarrowScreen', () => {
  it('says that a screen of 900 pixels is wide and one of 899 is narrow', () => {
    showScreen(900)
    const { unmount } = render(<Probe />)
    expect(screen.getByText('wide')).toBeVisible()
    unmount()

    showScreen(899)
    render(<Probe />)
    expect(screen.getByText('narrow')).toBeVisible()
  })

  it('follows the screen when its width changes', () => {
    render(<Probe />)
    expect(screen.getByText('wide')).toBeVisible()

    showScreen(390)
    expect(screen.getByText('narrow')).toBeVisible()

    showScreen(1366)
    expect(screen.getByText('wide')).toBeVisible()
  })

  it('watches the screen only while something on the page asks', () => {
    expect(screenWatchers()).toBe(0)

    const { unmount } = render(<Probe />)
    expect(screenWatchers()).toBe(1)

    unmount()
    expect(screenWatchers()).toBe(0)
  })

  it('draws the line where the style sheet of the layout draws it', () => {
    const questions = [...styleSheet.matchAll(/@media ([^{]+?) \{/g)].map((match) => match[1] ?? '')
    const aboutWidth = questions.filter((question) => question.includes('width'))

    expect(aboutWidth).toEqual([NARROW_SCREEN])
  })
})
