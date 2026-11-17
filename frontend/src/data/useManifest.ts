import { useEffect, useState } from 'react'
import {
  loadManifest,
  type Manifest,
  type ManifestProblem,
  type ManifestResult,
} from './manifest.ts'

/** Where the application is with the published data's manifest. */
export type ManifestState =
  | { readonly status: 'loading' }
  | { readonly status: 'ready'; readonly manifest: Manifest }
  | { readonly status: 'failed'; readonly problem: ManifestProblem }

/** Loads the manifest; `signal` stops the request. */
export type ManifestLoader = (signal: AbortSignal) => Promise<ManifestResult>

/** Loads the manifest published next to the application. */
export const loadPublishedManifest: ManifestLoader = (signal) =>
  loadManifest(import.meta.env.BASE_URL, { signal })

/**
 * Loads the manifest once and says how far that has got. The request is
 * stopped, and its answer ignored, when the component that asked goes away.
 */
export function useManifest(load: ManifestLoader = loadPublishedManifest): ManifestState {
  const [state, setState] = useState<ManifestState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()

    function finish(result: ManifestResult) {
      if (controller.signal.aborted) {
        return
      }
      setState(
        result.ok
          ? { status: 'ready', manifest: result.manifest }
          : { status: 'failed', problem: result.problem },
      )
    }

    load(controller.signal).then(finish, () => {
      finish({ ok: false, problem: 'unavailable' })
    })

    return () => {
      controller.abort()
    }
  }, [load])

  return state
}
