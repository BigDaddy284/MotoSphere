import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Manifest, ManifestResult } from './manifest.ts'
import { loadPublishedManifest, useManifest, type ManifestLoader } from './useManifest.ts'

const MANIFEST: Manifest = {
  formatVersion: 1,
  generatedAt: '2026-11-17T12:53:59Z',
  applicationVersion: '0.1.0',
  counts: new Map(),
}
const READY: ManifestResult = { ok: true, manifest: MANIFEST }

/** A loader whose answer the test gives when it chooses. */
function heldLoader() {
  const signals: AbortSignal[] = []
  const waiting: {
    resolve: (result: ManifestResult) => void
    reject: (reason: unknown) => void
  }[] = []
  const load = vi.fn<ManifestLoader>((signal) => {
    signals.push(signal)
    return new Promise<ManifestResult>((resolve, reject) => {
      waiting.push({ resolve, reject })
    })
  })
  return {
    load,
    signals,
    answer: (result: ManifestResult) => act(async () => waiting[0]?.resolve(result)),
    refuse: (reason: unknown) => act(async () => waiting[0]?.reject(reason)),
  }
}

describe('useManifest', () => {
  it('is loading until the manifest arrives', () => {
    const { load } = heldLoader()

    const { result } = renderHook(() => useManifest(load))

    expect(result.current).toEqual({ status: 'loading' })
  })

  it('is ready with the manifest once it has arrived', async () => {
    const loader = heldLoader()
    const { result } = renderHook(() => useManifest(loader.load))

    await loader.answer(READY)

    expect(result.current).toEqual({ status: 'ready', manifest: MANIFEST })
  })

  it.each(['unavailable', 'malformed', 'unsupported'] as const)(
    'has failed with the reason when the manifest is %s',
    async (problem) => {
      const loader = heldLoader()
      const { result } = renderHook(() => useManifest(loader.load))

      await loader.answer({ ok: false, problem })

      expect(result.current).toEqual({ status: 'failed', problem })
    },
  )

  it('treats a loader that throws as unavailable data', async () => {
    const loader = heldLoader()
    const { result } = renderHook(() => useManifest(loader.load))

    await loader.refuse(new Error('boom'))

    expect(result.current).toEqual({ status: 'failed', problem: 'unavailable' })
  })

  it('loads once, however often the component is drawn again', () => {
    const { load } = heldLoader()
    const { rerender } = renderHook(() => useManifest(load))

    rerender()
    rerender()

    expect(load).toHaveBeenCalledTimes(1)
  })

  it('stops the request when the component goes away', () => {
    const loader = heldLoader()
    const { unmount } = renderHook(() => useManifest(loader.load))
    expect(loader.signals[0]?.aborted).toBe(false)

    unmount()

    expect(loader.signals[0]?.aborted).toBe(true)
  })

  it('ignores the answer to a request it has stopped', async () => {
    const first = heldLoader()
    const second = heldLoader()
    const { result, rerender } = renderHook(({ load }) => useManifest(load), {
      initialProps: { load: first.load },
    })

    rerender({ load: second.load })
    expect(first.signals[0]?.aborted).toBe(true)
    await second.answer(READY)
    await first.answer({ ok: false, problem: 'unavailable' })

    expect(result.current).toEqual({ status: 'ready', manifest: MANIFEST })
  })
})

describe('loadPublishedManifest', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("fetches the manifest under the application's base path, with the signal", async () => {
    // Not the path of the real site, so that no fixed address can pass.
    vi.stubEnv('BASE_URL', '/served/from/here/')
    const fetched = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response('{"format_version": 2}'))
    const { signal } = new AbortController()

    const result = await loadPublishedManifest(signal)

    expect(fetched).toHaveBeenCalledWith('/served/from/here/data/manifest.json', {
      cache: 'no-cache',
      signal,
    })
    expect(result).toEqual({ ok: false, problem: 'unsupported' })
  })
})
