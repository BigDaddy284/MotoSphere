import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { loadManifest, manifestUrl, parseManifest } from '../src/data/manifest.ts'
import { expect, test } from './fixtures'

/**
 * The built site under test carries published data that the real export
 * command wrote when the test server started (see `playwright.config.ts`).
 * No test here uses a hand-written copy of a published file.
 */

const REPOSITORY = path.resolve(import.meta.dirname, '..', '..')

/** The address the site under test is served from; it ends with the site's path. */
function siteAddress(baseURL: string | undefined): string {
  if (baseURL === undefined) {
    throw new Error('The browser tests have no base address.')
  }
  return baseURL
}

/** When this run started, to the second, because the manifest's time has no fractions. */
function runStarted(): number {
  const started = Number(process.env['MOTOSPHERE_E2E_STARTED'])
  expect(Number.isSafeInteger(started), 'the start of the run is known').toBe(true)
  return Math.floor(started / 1000) * 1000
}

test.describe('published data', () => {
  test('the built site serves the manifest as JSON', async ({ request }) => {
    const response = await request.get(manifestUrl('./'))

    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toMatch(/^application\/json/)
    expect((await response.text()).endsWith('}\n')).toBe(true)
  })

  test('the manifest reader accepts the served manifest', async ({ request, baseURL }) => {
    const response = await request.get(manifestUrl('./'))
    expect(parseManifest(await response.json()).ok).toBe(true)

    const result = await loadManifest(siteAddress(baseURL))
    expect(result.ok).toBe(true)
  })

  test('the manifest was exported for this run', async ({ baseURL }) => {
    const result = await loadManifest(siteAddress(baseURL))
    if (!result.ok) {
      throw new Error(`no manifest: ${result.problem}`)
    }

    const generated = Date.parse(result.manifest.generatedAt)
    expect(generated).toBeGreaterThanOrEqual(runStarted())
    expect(generated).toBeLessThanOrEqual(Date.now())
  })

  test('the manifest comes from this version of the pipeline', async ({ baseURL }) => {
    const project = await readFile(path.join(REPOSITORY, 'backend', 'pyproject.toml'), 'utf8')
    const version = /^version = "([^"]+)"$/m.exec(project)?.[1]
    expect(version, 'the version in backend/pyproject.toml').toBeDefined()

    const result = await loadManifest(siteAddress(baseURL))

    expect(result.ok && result.manifest.applicationVersion).toBe(version)
    expect(result.ok && result.manifest.formatVersion).toBe(1)
  })

  test('the page a browser loads can fetch and read the manifest', async ({ page }) => {
    await page.goto('./')

    const content: unknown = await page.evaluate(async (url) => {
      const response = await fetch(url, { cache: 'no-cache' })
      return response.json()
    }, manifestUrl('./'))

    expect(parseManifest(content).ok).toBe(true)
  })

  test('the export leaves nothing but the manifest in the data folder', async () => {
    const exported = await readdir(path.join(REPOSITORY, 'frontend', 'public', 'data'))

    expect(exported).toEqual(['manifest.json'])
  })
})
