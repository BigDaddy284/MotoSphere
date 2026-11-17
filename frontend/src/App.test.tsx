import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { APP_NAME, APP_TAGLINE, App } from './App.tsx'

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
})
