import { mkdirSync, mkdtempSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, extname, join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  BROUGHT_IN,
  ENGINE_FOLDER,
  ENGINE_PACKAGE,
  engineFiles,
  EngineFilesError,
  engineFilesInTheSite,
  LEFT_OUT,
} from './engineFiles.ts'

// A computer gives the entries of a folder in an order of its own: Linux by
// their names, Windows without regard to capital letters. In these tests every
// folder gives them in an order that is neither that of the names nor its
// opposite, with the first entry last, so that the order of the files is the
// work of the step and of nothing else. Nothing but the order is changed.
vi.mock('node:fs', async (original) => {
  const fs = await original<typeof import('node:fs')>()
  return {
    ...fs,
    readdirSync: (path: string, options: { withFileTypes: true }) => {
      const entries = fs.readdirSync(path, options)
      return [...entries.slice(1), ...entries.slice(0, 1)]
    },
  }
})

// A folder of its own for every test, made up for the purpose and taken away
// afterwards. It stands for the folder of a project.
let project: string

beforeEach(() => {
  project = mkdtempSync(join(tmpdir(), 'motosphere-engine-'))
})

afterEach(() => {
  rmSync(project, { recursive: true, force: true })
})

/** Writes files into the test's project, each with the folders it needs. */
function put(files: readonly string[]): void {
  for (const name of files) {
    mkdirSync(dirname(join(project, name)), { recursive: true })
    writeFileSync(join(project, name), `the content of ${name}`)
  }
}

/** Writes files into the folder the engine of the test's project fetches from. */
function bring(files: readonly string[]): void {
  put(files.map((name) => `${ENGINE_PACKAGE}/${BROUGHT_IN}/${name}`))
}

const NOTHING_LEFT_OUT = {}

describe('the files of an engine that go into the site', () => {
  it('are every file beneath the folder it fetches from, each by its path with "/"', () => {
    bring(['Workers/one.js', 'Assets/table.json', 'Assets/Textures/Sky/px.jpg'])

    expect(engineFiles(project, NOTHING_LEFT_OUT)).toEqual([
      'Assets/table.json',
      'Assets/Textures/Sky/px.jpg',
      'Workers/one.js',
    ])
  })

  it('give the files of a folder before those of the folders in it, each by name', () => {
    // A capital letter comes before every small one, on every computer. No
    // two names here differ in their capitals alone: on Windows such names
    // are one name, and the second file would be written over the first.
    bring(['c/2.js', 'c/1.js', 'd.js', 'a.js', 'C.js', 'c/a/z.js', 'c/a/y.js', 'B/1.js', 'a/1.js'])

    expect(engineFiles(project, NOTHING_LEFT_OUT)).toEqual([
      'C.js',
      'a.js',
      'd.js',
      'B/1.js',
      'a/1.js',
      'c/1.js',
      'c/2.js',
      'c/a/y.js',
      'c/a/z.js',
    ])
  })

  it('are of every kind and name: none is left out for what it is called', () => {
    bring(['.hidden', 'NOEXTENSION', 'Workers/package.json', 'a.b.c.wasm', 'node_modules/x.js'])

    expect(engineFiles(project, NOTHING_LEFT_OUT)).toEqual([
      '.hidden',
      'NOEXTENSION',
      'a.b.c.wasm',
      'Workers/package.json',
      'node_modules/x.js',
    ])
  })

  it('are not the rest of the package, nor any other package', () => {
    bring(['Workers/one.js'])
    put([
      `${ENGINE_PACKAGE}/README.md`,
      `${ENGINE_PACKAGE}/LICENSE.md`,
      `${ENGINE_PACKAGE}/Source/Workers/one.js`,
      `${ENGINE_PACKAGE}/${BROUGHT_IN}Other/two.js`,
      `node_modules/another/${BROUGHT_IN}/three.js`,
      `${BROUGHT_IN}/four.js`,
    ])

    expect(engineFiles(project, NOTHING_LEFT_OUT)).toEqual(['Workers/one.js'])
  })

  it('leave out the files listed as left out, and no other of the same name', () => {
    bring(['Images/logo.png', 'Images/own.png', 'Other/Images/logo.png', 'logo.png'])

    expect(engineFiles(project, { 'Images/logo.png': 'The logo of another company.' })).toEqual([
      'logo.png',
      'Images/own.png',
      'Other/Images/logo.png',
    ])
  })

  it('are refused when a file listed as left out is not there', () => {
    bring(['Images/own.png'])

    expect(() =>
      engineFiles(project, { 'Images/logo.png': 'The logo of another company.' }),
    ).toThrow(
      new EngineFilesError(
        'Images/logo.png is listed as left out, and the engine does not bring it.',
      ),
    )
  })

  it('are refused when what is listed as left out is a folder', () => {
    bring(['Images/own.png'])

    expect(() => engineFiles(project, { Images: 'Every picture.' })).toThrow(
      new EngineFilesError('Images is listed as left out, and the engine does not bring it.'),
    )
  })

  it('are refused when the engine is not installed', () => {
    put(['node_modules/another/index.js'])
    const folder = join(project, ENGINE_PACKAGE, BROUGHT_IN)

    expect(() => engineFiles(project, NOTHING_LEFT_OUT)).toThrow(
      new EngineFilesError(`${folder} cannot be read. Run "npm ci" first.`),
    )
  })

  it('are refused when the folder holds no file, also when it holds folders', () => {
    const folder = join(project, ENGINE_PACKAGE, BROUGHT_IN)
    mkdirSync(join(folder, 'Workers', 'deeper'), { recursive: true })

    expect(() => engineFiles(project, NOTHING_LEFT_OUT)).toThrow(
      new EngineFilesError(`${folder} holds no file.`),
    )
  })

  it('are refused when a link is among them, which is named', () => {
    bring(['Workers/one.js', 'Assets/table.json'])
    const folder = join(project, ENGINE_PACKAGE, BROUGHT_IN)
    // A junction on Windows, where a link to a folder needs no special right.
    symlinkSync(join(folder, 'Workers'), join(folder, 'Assets', 'linked'), 'junction')

    expect(() => engineFiles(project, NOTHING_LEFT_OUT)).toThrow(
      new EngineFilesError(`${join(folder, 'Assets/', 'linked')} is neither a file nor a folder.`),
    )
  })
})

describe('the files of the engine of this project', () => {
  // The folder of the front end: the tests are run from it.
  const here = process.cwd()
  const folder = join(here, ENGINE_PACKAGE, BROUGHT_IN)

  /** Every file beneath the folder, found another way than the step finds them. */
  function allBrought(): string[] {
    return readdirSync(folder, { recursive: true, withFileTypes: true })
      .filter((entry) => entry.isFile())
      .map((entry) =>
        join(entry.parentPath, entry.name)
          .slice(folder.length + 1)
          .replaceAll('\\', '/'),
      )
  }

  it('are every file the engine brings but those left out', () => {
    const brought = allBrought()
    const files = engineFiles(here)

    expect(brought.length).toBeGreaterThan(200)
    expect(files.toSorted()).toEqual(
      brought.filter((name) => !Object.keys(LEFT_OUT).includes(name)).toSorted(),
    )
    expect(files).toHaveLength(brought.length - Object.keys(LEFT_OUT).length)
  })

  it('hold what the engine asks for by name', () => {
    // One of each thing the code of the engine fetches: a background script
    // and a piece of one, a program for the browser's own machine, a table,
    // the picture of the Earth it has with it and the file that describes
    // it, the stars, the logo it shows by default, and its style sheet.
    const files = engineFiles(here)

    expect(files).toEqual(
      expect.arrayContaining([
        'Workers/createTaskProcessorWorker.js',
        'Workers/createVerticesFromHeightmap.js',
        'ThirdParty/draco_decoder.wasm',
        'ThirdParty/Workers/zip-web-worker.js',
        'Assets/approximateTerrainHeights.json',
        'Assets/IAU2006_XYS/IAU2006_XYS_0.json',
        'Assets/Textures/NaturalEarthII/tilemapresource.xml',
        'Assets/Textures/NaturalEarthII/0/0/0.jpg',
        'Assets/Textures/SkyBox/tycho2t3_80_px.jpg',
        'Assets/Textures/maki/marker.png',
        'Assets/Textures/pin.svg',
        'Assets/Images/ion-credit.png',
        'Widgets/CesiumWidget/CesiumWidget.css',
      ]),
    )
  })

  it('are of eight kinds, and a kind the engine did not bring before is noticed', () => {
    // A person then says what a browser must be told such a file is, and
    // the tests of the built site ask for one of that kind too.
    const kinds = new Set(engineFiles(here).map((name) => extname(name).toLowerCase()))

    expect([...kinds].toSorted()).toEqual([
      '.css',
      '.jpg',
      '.js',
      '.json',
      '.png',
      '.svg',
      '.wasm',
      '.xml',
    ])
  })

  it('leave out two pictures of other companies, each with why', () => {
    expect(Object.keys(LEFT_OUT)).toEqual([
      'Assets/Images/bing_maps_credit.png',
      'Assets/Images/google_earth_credit.png',
    ])
    for (const why of Object.values(LEFT_OUT)) {
      expect(why).toMatch(/^The logo of [A-Z][A-Za-z ]+, shown with imagery of [A-Za-z ]+\.$/)
    }
    expect(allBrought()).toEqual(expect.arrayContaining(Object.keys(LEFT_OUT)))
  })

  it('go into one folder of the site', () => {
    expect(ENGINE_FOLDER).toBe('cesium')
  })
})

describe('the step of the build', () => {
  it('is for the build and not for the development server', () => {
    expect(engineFilesInTheSite().apply).toBe('build')
    expect(engineFilesInTheSite().name).toBe('motosphere:engine-files')
  })
})
