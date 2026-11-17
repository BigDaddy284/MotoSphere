/**
 * The manifest is the first published data file the application reads. It
 * says which version of the data format the files use, when they were
 * generated and how many records of each kind they hold.
 *
 * The file is written by the data pipeline (`python -m motosphere export`).
 * Nothing in it is trusted: every field is checked before it is used.
 */

/** The version of the published data format this application can read. */
export const SUPPORTED_FORMAT_VERSION = 1

export type Manifest = {
  readonly formatVersion: number
  /** When the data was generated: a moment in UTC, to the second, as `YYYY-MM-DDTHH:MM:SSZ`. */
  readonly generatedAt: string
  /** The MotoSphere version that generated the data. */
  readonly applicationVersion: string
  /** The number of published records of each kind, for example `tracks`. */
  readonly counts: ReadonlyMap<string, number>
}

/**
 * Why there is no manifest to show:
 * - `unavailable`: the file could not be fetched.
 * - `malformed`: the file is not a manifest.
 * - `unsupported`: the file is a manifest in a data format this application
 *   cannot read, usually because the application is older than the data.
 */
export type ManifestProblem = 'unavailable' | 'malformed' | 'unsupported'

export type ManifestResult =
  | { readonly ok: true; readonly manifest: Manifest }
  | { readonly ok: false; readonly problem: ManifestProblem }

const MOMENT_LENGTH = 'YYYY-MM-DDTHH:MM:SSZ'.length
const RECORD_KIND = /^[a-z][a-z_]*$/

function failed(problem: ManifestProblem): ManifestResult {
  return { ok: false, problem }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
}

/** True for a real moment written exactly as `YYYY-MM-DDTHH:MM:SSZ`. */
function isMoment(value: unknown): value is string {
  if (typeof value !== 'string' || value.length !== MOMENT_LENGTH) {
    return false
  }
  const time = Date.parse(value)
  // Writing the moment out again and comparing accepts this one spelling only,
  // and rejects dates that do not exist, such as 30 February.
  return !Number.isNaN(time) && new Date(time).toISOString() === value.replace('Z', '.000Z')
}

function readCounts(value: unknown): ReadonlyMap<string, number> | undefined {
  if (!isRecord(value)) {
    return undefined
  }
  const counts = new Map<string, number>()
  for (const [kind, count] of Object.entries(value)) {
    if (!RECORD_KIND.test(kind) || !isCount(count)) {
      return undefined
    }
    counts.set(kind, count)
  }
  return counts
}

/**
 * Checks a parsed JSON value and returns the manifest it holds.
 *
 * The format version is checked first: a manifest in another version of the
 * format is `unsupported` whatever else it contains. Fields this application
 * does not know are ignored.
 */
export function parseManifest(value: unknown): ManifestResult {
  if (!isRecord(value)) {
    return failed('malformed')
  }
  const formatVersion = value['format_version']
  if (
    typeof formatVersion !== 'number' ||
    !Number.isSafeInteger(formatVersion) ||
    formatVersion < 1
  ) {
    return failed('malformed')
  }
  if (formatVersion !== SUPPORTED_FORMAT_VERSION) {
    return failed('unsupported')
  }

  const generatedAt = value['generated_at']
  const applicationVersion = value['application_version']
  const counts = readCounts(value['counts'])
  if (
    !isMoment(generatedAt) ||
    typeof applicationVersion !== 'string' ||
    applicationVersion === '' ||
    counts === undefined
  ) {
    return failed('malformed')
  }
  return { ok: true, manifest: { formatVersion, generatedAt, applicationVersion, counts } }
}

/**
 * The address of the manifest for an application served from `baseUrl`
 * (Vite's `import.meta.env.BASE_URL`, for example `/` or `/MotoSphere/`).
 */
export function manifestUrl(baseUrl: string): string {
  return `${baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`}data/manifest.json`
}

export type LoadManifestOptions = {
  /** Stops the request, for example when the part of the page that asked for it goes away. */
  readonly signal?: AbortSignal
  /** The function that fetches; the browser's `fetch` unless a test passes its own. */
  readonly fetcher?: typeof fetch
}

/**
 * Fetches and checks the manifest. Never throws: every failure is a result
 * with the reason.
 */
export async function loadManifest(
  baseUrl: string,
  { signal, fetcher = fetch }: LoadManifestOptions = {},
): Promise<ManifestResult> {
  // `no-cache` makes the browser ask the server whether its copy is still
  // current, so newly published data is seen without a forced reload.
  const init: RequestInit =
    signal === undefined ? { cache: 'no-cache' } : { cache: 'no-cache', signal }
  let response: Response
  try {
    response = await fetcher(manifestUrl(baseUrl), init)
  } catch {
    return failed('unavailable')
  }
  if (!response.ok) {
    return failed('unavailable')
  }
  let content: unknown
  try {
    content = await response.json()
  } catch {
    return failed('malformed')
  }
  return parseManifest(content)
}
