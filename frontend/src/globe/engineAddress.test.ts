import { buildModuleUrl } from '@cesium/engine'
import { act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ENGINE_FOLDER, SITE_PATH } from '../../site.ts'
import { ENGINE_ADDRESS, tellTheEngineWhereItsFilesAre } from './engineAddress.ts'

// The engine reads the address the first time it builds the address of a
// file, and keeps it. So the address is told here before any test asks the
// engine for one, as the application tells it before anything is shown.
tellTheEngineWhereItsFilesAre()

// Every file of the application that could tell the engine an address: its
// code, the page, and the settings of the build. Tests are not among them.
const sources = {
  ...import.meta.glob<string>('../**/*.{ts,tsx}', {
    query: '?raw',
    import: 'default',
    eager: true,
  }),
  ...import.meta.glob<string>(['../../index.html', '../../vite.config.ts', '../../site.ts'], {
    query: '?raw',
    import: 'default',
    eager: true,
  }),
}
const application = Object.entries(sources).filter(([path]) => !/\.test\.tsx?$/.test(path))
// The steps of the build and of the development server, which put the
// engine's files where the address says they are.
const steps =
  import.meta.glob<string>('../../sitebuild/engineFiles.ts', {
    query: '?raw',
    import: 'default',
    eager: true,
  })['../../sitebuild/engineFiles.ts'] ?? ''
// The module the page starts with, as it is written.
const mainSource = sources['../main.tsx'] ?? ''

/** The files of the application whose text holds one of these words. */
function thatSay(...words: string[]): string[] {
  return application
    .filter(([, text]) => words.some((word) => text.includes(word)))
    .map(([path]) => path)
    .toSorted()
}

describe("the address of the engine's files", () => {
  it("is the folder of the engine's files beneath the site's path", () => {
    expect(ENGINE_ADDRESS).toBe(`${SITE_PATH}${ENGINE_FOLDER}/`)
    expect(ENGINE_ADDRESS).toBe('/MotoSphere/cesium/')
  })

  it('names no other computer', () => {
    // A path from the top of the site the page came from, and nothing else:
    // no scheme, no name of a computer, and no way up or out.
    expect(ENGINE_ADDRESS).toMatch(/^\/(?:[A-Za-z0-9-]+\/)+$/)
    for (const page of ['https://example.org/MotoSphere/', 'http://127.0.0.1:4173/MotoSphere/']) {
      const address = new URL(ENGINE_ADDRESS, page)
      expect(address.origin).toBe(new URL(page).origin)
      expect(address.pathname).toBe(ENGINE_ADDRESS)
    }
  })
})

describe('telling the engine where its files are', () => {
  it('puts the address under the name the engine reads', () => {
    globalThis.CESIUM_BASE_URL = undefined

    tellTheEngineWhereItsFilesAre()

    expect(globalThis.CESIUM_BASE_URL).toBe(ENGINE_ADDRESS)
  })

  it('puts it there again over another address', () => {
    globalThis.CESIUM_BASE_URL = 'https://elsewhere.example/engine/'

    tellTheEngineWhereItsFilesAre()

    expect(globalThis.CESIUM_BASE_URL).toBe(ENGINE_ADDRESS)
  })
})

describe('the engine, as installed, once it is told', () => {
  it.each([
    ['a background script', 'Workers/createTaskProcessorWorker.js'],
    ['a program', 'ThirdParty/draco_decoder.wasm'],
    ['a table', 'Assets/approximateTerrainHeights.json'],
    ['a picture of the Earth', 'Assets/Textures/NaturalEarthII/0/0/0.jpg'],
    ['the description of the pictures of the Earth', 'Assets/Textures/NaturalEarthII'],
  ])('builds the address of %s beneath the folder, on the computer of the page', (_what, file) => {
    const built = new URL(buildModuleUrl(file))

    expect(built.origin).toBe(window.location.origin)
    expect(built.pathname).toBe(`${ENGINE_ADDRESS}${file}`)
    expect(built.search).toBe('')
    expect(built.hash).toBe('')
  })
})

describe('the application', () => {
  it("names the engine's own word for the address in one module only", () => {
    expect(thatSay('CESIUM_BASE_URL', 'setBaseUrl')).toEqual(['./engineAddress.ts'])
  })

  it('builds the address in one module only', () => {
    expect(thatSay('ENGINE_FOLDER')).toEqual(['../../site.ts', './engineAddress.ts'])
    // The folder written out, which the name of the engine's package is not.
    expect(
      application.filter(([, text]) => /(?<!@)cesium\//.test(text)).map(([path]) => path),
    ).toEqual([])
  })

  it('takes the folder from where the build and the development server take it', () => {
    expect(steps).toContain("import { ENGINE_FOLDER } from '../site.ts'")
    expect(steps).not.toMatch(/ENGINE_FOLDER\s*=/)
    expect(steps.split('${ENGINE_FOLDER}/')).toHaveLength(3)
  })

  it('tells the engine in one place only, where it starts', () => {
    expect(thatSay('tellTheEngineWhereItsFilesAre')).toEqual(['../main.tsx', './engineAddress.ts'])
  })

  it('tells the engine before it shows anything', () => {
    const told = mainSource.indexOf('\ntellTheEngineWhereItsFilesAre()\n')
    const shown = mainSource.indexOf('createRoot(')

    expect(mainSource.split('tellTheEngineWhereItsFilesAre()')).toHaveLength(2)
    expect(told).toBeGreaterThan(-1)
    expect(shown).toBeGreaterThan(told)
    // Nothing before it but what the page is put together from.
    const before = mainSource.slice(0, told).split('\n')
    expect(before.filter((line) => line !== '' && !/^(import |\/\/ )/.test(line))).toEqual([])
  })

  it('has told the engine by the time it has started', async () => {
    vi.resetModules()
    globalThis.CESIUM_BASE_URL = undefined
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))
    const root = document.createElement('div')
    root.id = 'root'
    document.body.append(root)

    // Inside `act`, React does all it has to do before the test goes on:
    // the page is shown in full, and nothing of it is left waiting that
    // could run after the test's document is gone.
    await act(async () => {
      await import('../main.tsx')
    })
    // Out of the document again before anything is looked at, so that the
    // next test finds the document empty whatever this one finds.
    root.remove()

    expect(root).not.toBeEmptyDOMElement()
    expect(globalThis.CESIUM_BASE_URL).toBe(ENGINE_ADDRESS)
  })

  it('has told the engine even when it cannot start', async () => {
    vi.resetModules()
    globalThis.CESIUM_BASE_URL = undefined

    await expect(import('../main.tsx')).rejects.toThrow('no element with id "root"')

    expect(globalThis.CESIUM_BASE_URL).toBe(ENGINE_ADDRESS)
  })
})
