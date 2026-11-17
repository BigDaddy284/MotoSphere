import { describe, expect, it, vi } from 'vitest'
import {
  loadManifest,
  manifestUrl,
  parseManifest,
  SUPPORTED_FORMAT_VERSION,
  type ManifestResult,
} from './manifest.ts'

// Exactly what `python -m motosphere export` wrote on 17 November 2026.
const EXPORTED = `{
  "application_version": "0.1.0",
  "counts": {},
  "format_version": 1,
  "generated_at": "2026-11-17T12:53:59Z"
}
`

function valid(changes: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    format_version: 1,
    generated_at: '2026-11-17T12:53:59Z',
    application_version: '0.1.0',
    counts: { tracks: 3, events: 12 },
    ...changes,
  }
}

function without(field: string): Record<string, unknown> {
  return Object.fromEntries(Object.entries(valid()).filter(([name]) => name !== field))
}

const MALFORMED: ManifestResult = { ok: false, problem: 'malformed' }
const UNAVAILABLE: ManifestResult = { ok: false, problem: 'unavailable' }
const UNSUPPORTED: ManifestResult = { ok: false, problem: 'unsupported' }

function jsonResponse(content: unknown, status = 200): Response {
  return new Response(JSON.stringify(content), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function fetcherGiving(response: Response) {
  return vi.fn<typeof fetch>().mockResolvedValue(response)
}

describe('parseManifest', () => {
  it('reads the manifest the export command writes', () => {
    const result = parseManifest(JSON.parse(EXPORTED))

    expect(result).toEqual({
      ok: true,
      manifest: {
        formatVersion: 1,
        generatedAt: '2026-11-17T12:53:59Z',
        applicationVersion: '0.1.0',
        counts: new Map(),
      },
    })
  })

  it('reads the number of records of each kind', () => {
    const result = parseManifest(valid())

    expect(result.ok && [...result.manifest.counts]).toEqual([
      ['tracks', 3],
      ['events', 12],
    ])
  })

  it('reads the format version this application supports', () => {
    expect(SUPPORTED_FORMAT_VERSION).toBe(1)
    expect(parseManifest(valid({ format_version: SUPPORTED_FORMAT_VERSION })).ok).toBe(true)
  })

  it('ignores fields it does not know', () => {
    const result = parseManifest(valid({ files: ['tracks.json'] }))

    expect(result.ok && Object.keys(result.manifest).toSorted()).toEqual([
      'applicationVersion',
      'counts',
      'formatVersion',
      'generatedAt',
    ])
  })

  it.each([
    ['nothing', null],
    ['a list', [valid()]],
    ['a text', EXPORTED],
    ['a number', 1],
    ['a yes or no', true],
  ])('rejects %s in place of a manifest', (_name, value) => {
    expect(parseManifest(value)).toEqual(MALFORMED)
  })

  it.each(['format_version', 'generated_at', 'application_version', 'counts'])(
    'rejects a manifest without %s',
    (field) => {
      expect(parseManifest(without(field))).toEqual(MALFORMED)
    },
  )

  it.each([
    ['zero', 0],
    ['a negative number', -1],
    ['a fraction', 1.5],
    ['a text', '1'],
    ['nothing', null],
  ])('rejects a format version that is %s', (_name, value) => {
    expect(parseManifest(valid({ format_version: value }))).toEqual(MALFORMED)
  })

  it.each([
    ['with a time zone offset', '2026-11-17T12:53:59+00:00'],
    ['with fractions of a second', '2026-11-17T12:53:59.000Z'],
    ['without the T', '2026-11-17 12:53:59Z'],
    ['without a time', '2026-11-17'],
    ['on a day that does not exist', '2026-02-30T00:00:00Z'],
    ['in a month that does not exist', '2026-13-01T00:00:00Z'],
    ['at an hour that does not exist', '2026-11-17T24:00:00Z'],
    ['in a year of more than four digits', '+010000-01-01T00:00:00Z'],
    ['in small letters', '2026-11-17t12:53:59z'],
    ['in words', 'yesterday'],
    ['that is empty', ''],
    ['as a number', 1_763_384_039],
    ['with something after it', '2026-11-17T12:53:59Z\n<script>'],
  ])('rejects a generation time %s', (_name, value) => {
    expect(parseManifest(valid({ generated_at: value }))).toEqual(MALFORMED)
  })

  it.each([
    ['empty', ''],
    ['a number', 5],
    ['nothing', null],
  ])('rejects an application version that is %s', (_name, value) => {
    expect(parseManifest(valid({ application_version: value }))).toEqual(MALFORMED)
  })

  it.each([
    ['nothing', null],
    ['a list', [3]],
    ['an empty list', []],
    ['a text', 'none'],
    ['a negative number', { tracks: -1 }],
    ['a fraction', { tracks: 1.5 }],
    ['a number written as text', { tracks: '3' }],
    ['a number too large to be exact', { tracks: 2 ** 53 }],
    ['a kind with a capital letter', { Tracks: 1 }],
    ['a kind with no name', { '': 1 }],
    ['a kind with spaces', { 'tracks per country': 1 }],
    ['a kind that starts with an underscore', JSON.parse('{"__proto__": 1}')],
  ])('rejects counts holding %s', (_name, value) => {
    expect(parseManifest(valid({ counts: value }))).toEqual(MALFORMED)
  })

  it('says a newer data format is unsupported', () => {
    expect(parseManifest(valid({ format_version: 2 }))).toEqual(UNSUPPORTED)
  })

  it('checks the format version before anything else', () => {
    expect(parseManifest({ format_version: 2, layout: 'something new' })).toEqual(UNSUPPORTED)
  })
})

describe('manifestUrl', () => {
  it.each([
    ['/', '/data/manifest.json'],
    ['/MotoSphere/', '/MotoSphere/data/manifest.json'],
    ['/MotoSphere', '/MotoSphere/data/manifest.json'],
  ])('for the base path %s is %s', (baseUrl, expected) => {
    expect(manifestUrl(baseUrl)).toBe(expected)
  })
})

describe('loadManifest', () => {
  it('fetches the manifest under the base path, asking the server for the current copy', async () => {
    const fetcher = fetcherGiving(jsonResponse(valid()))

    await loadManifest('/MotoSphere/', { fetcher })

    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(fetcher).toHaveBeenCalledWith('/MotoSphere/data/manifest.json', { cache: 'no-cache' })
  })

  it('returns the manifest it fetched', async () => {
    const fetcher = fetcherGiving(new Response(EXPORTED))

    const result = await loadManifest('/', { fetcher })

    expect(result.ok && result.manifest.generatedAt).toBe('2026-11-17T12:53:59Z')
  })

  it('passes on the signal that stops the request', async () => {
    const fetcher = fetcherGiving(jsonResponse(valid()))
    const { signal } = new AbortController()

    await loadManifest('/', { fetcher, signal })

    expect(fetcher).toHaveBeenCalledWith('/data/manifest.json', { cache: 'no-cache', signal })
  })

  it("uses the browser's fetch unless it is given another", async () => {
    const browserFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(valid()))

    const result = await loadManifest('/')

    expect(result.ok).toBe(true)
    expect(browserFetch).toHaveBeenCalledWith('/data/manifest.json', { cache: 'no-cache' })
  })

  it('is unavailable when the request fails', async () => {
    const fetcher = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(loadManifest('/', { fetcher })).resolves.toEqual(UNAVAILABLE)
  })

  it('is unavailable when the request is stopped', async () => {
    const stopped = new DOMException('The operation was aborted.', 'AbortError')
    const fetcher = vi.fn<typeof fetch>().mockRejectedValue(stopped)

    await expect(loadManifest('/', { fetcher })).resolves.toEqual(UNAVAILABLE)
  })

  it.each([404, 500])(
    'is unavailable when the server answers %d, whatever it sends',
    async (status) => {
      const fetcher = fetcherGiving(jsonResponse(valid(), status))

      await expect(loadManifest('/', { fetcher })).resolves.toEqual(UNAVAILABLE)
    },
  )

  it('is malformed when the answer is a web page instead of data', async () => {
    const page = new Response('<!doctype html><title>MotoSphere</title>', {
      headers: { 'Content-Type': 'text/html' },
    })

    await expect(loadManifest('/', { fetcher: fetcherGiving(page) })).resolves.toEqual(MALFORMED)
  })

  it('is malformed when the data is not a manifest', async () => {
    const fetcher = fetcherGiving(jsonResponse({ tracks: [] }))

    await expect(loadManifest('/', { fetcher })).resolves.toEqual(MALFORMED)
  })

  it('is unsupported when the data is in a newer format', async () => {
    const fetcher = fetcherGiving(jsonResponse(valid({ format_version: 2 })))

    await expect(loadManifest('/', { fetcher })).resolves.toEqual(UNSUPPORTED)
  })
})
