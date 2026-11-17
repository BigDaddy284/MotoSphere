import { formatDataDate } from './dataDate.ts'
import { useManifest, type ManifestLoader, type ManifestState } from './useManifest.ts'

interface DataStatusProps {
  /** Loads the manifest. Left out, the published manifest is loaded. */
  load?: ManifestLoader
}

function message(state: ManifestState) {
  switch (state.status) {
    case 'loading':
      return 'Loading data…'
    case 'ready':
      return (
        <>
          Data updated{' '}
          <time dateTime={state.manifest.generatedAt}>
            {formatDataDate(state.manifest.generatedAt)}
          </time>
        </>
      )
    case 'failed':
      // An application older than the data is put right by loading it again.
      return state.problem === 'unsupported'
        ? 'Reload the page to see the data'
        : 'Data unavailable'
  }
}

/**
 * One line that tells the user how current the data is, or that it could not
 * be loaded. Changes are announced to people who use a screen reader.
 */
export function DataStatus({ load }: DataStatusProps) {
  const state = useManifest(load)

  return <output>{message(state)}</output>
}
