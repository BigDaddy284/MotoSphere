import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { formatDataDate } from './dataDate.ts'
import { DataStatus } from './DataStatus.tsx'
import type { ManifestResult } from './manifest.ts'
import type { ManifestLoader } from './useManifest.ts'

// Exactly what `python -m motosphere export` wrote on 17 November 2026.
const EXPORTED = `{
  "application_version": "0.1.0",
  "counts": {},
  "format_version": 1,
  "generated_at": "2026-11-17T12:53:59Z"
}
`
const GENERATED_AT = '2026-11-17T12:53:59Z'

function loaderGiving(result: ManifestResult): ManifestLoader {
  return () => Promise.resolve(result)
}

const READY: ManifestResult = {
  ok: true,
  manifest: {
    formatVersion: 1,
    generatedAt: GENERATED_AT,
    applicationVersion: '0.1.0',
    counts: new Map(),
  },
}

describe('DataStatus', () => {
  it('says the data is loading until it arrives', () => {
    render(<DataStatus load={() => new Promise(() => {})} />)

    expect(screen.getByRole('status')).toHaveTextContent(/^Loading data…$/)
  })

  it('says when the data was updated, with the moment in machine-readable form', async () => {
    render(<DataStatus load={loaderGiving(READY)} />)

    const date = await screen.findByText(formatDataDate(GENERATED_AT))
    expect(date.tagName).toBe('TIME')
    expect(date).toHaveAttribute('datetime', GENERATED_AT)
    expect(screen.getByRole('status')).toHaveTextContent(
      `Data updated ${formatDataDate(GENERATED_AT)}`,
    )
    expect(screen.getByRole('status').textContent).toContain('2026')
  })

  it.each(['unavailable', 'malformed'] as const)(
    'says the data is unavailable when the manifest is %s',
    async (problem) => {
      render(<DataStatus load={loaderGiving({ ok: false, problem })} />)

      expect(await screen.findByText('Data unavailable')).toBe(screen.getByRole('status'))
    },
  )

  it('asks for a reload when the data is in a newer format than the application reads', async () => {
    render(<DataStatus load={loaderGiving({ ok: false, problem: 'unsupported' })} />)

    expect(await screen.findByText('Reload the page to see the data')).toBe(
      screen.getByRole('status'),
    )
  })

  it('loads the published manifest when it is given no loader', async () => {
    const fetched = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(EXPORTED))

    render(<DataStatus />)

    expect(await screen.findByText(/^Data updated/)).toBe(screen.getByRole('status'))
    expect(fetched).toHaveBeenCalledTimes(1)
    expect(fetched.mock.calls[0]?.[0]).toBe('/data/manifest.json')
  })
})
