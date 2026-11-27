import { readdirSync, readFileSync } from 'node:fs'
import { extname, join } from 'node:path'
import { BROUGHT_IN, ENGINE_FOLDER, ENGINE_PACKAGE, engineFiles } from '../sitebuild/engineFiles.ts'
import { LICENCES_FILE } from '../sitebuild/licences.ts'
import { SITE_PATH } from '../site.ts'
import { expect, test } from './fixtures'

/**
 * The engine of the globe fetches files of its own while it runs: background
 * scripts, programs, tables and pictures. The build puts them into the site
 * under one folder. These tests read the site that was built for this run,
 * on the disk and through its server, and hold it against the engine as it
 * is installed. The browser tests are run from the folder of the front end.
 */

const PROJECT = process.cwd()
const INSTALLED = join(PROJECT, ENGINE_PACKAGE)
const BUILT = join(PROJECT, 'dist', ENGINE_FOLDER)

/** Every file beneath a folder, each by its path from it with "/", by name. */
function allBeneath(folder: string): string[] {
  return readdirSync(folder, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) =>
      join(entry.parentPath, entry.name)
        .slice(folder.length + 1)
        .replaceAll('\\', '/'),
    )
    .toSorted()
}

const FILES = engineFiles(PROJECT)

// One file of each kind the engine brings, with what a browser must be told
// it is. A script or a program told to be anything else is not run.
const ONE_OF_EACH_KIND = [
  ['Workers/createTaskProcessorWorker.js', /^text\/javascript\b/],
  ['ThirdParty/draco_decoder.wasm', /^application\/wasm$/],
  ['Assets/approximateTerrainHeights.json', /^application\/json\b/],
  ['Widgets/CesiumWidget/CesiumWidget.css', /^text\/css\b/],
  ['Assets/Textures/NaturalEarthII/0/0/0.jpg', /^image\/jpeg$/],
  ['Assets/Textures/maki/marker.png', /^image\/png$/],
  ['Assets/Textures/pin.svg', /^image\/svg\+xml$/],
  ['Assets/Textures/NaturalEarthII/tilemapresource.xml', /^(text|application)\/xml\b/],
] as const

test.describe("the engine's own files in the built site", () => {
  test('are the files the engine brings, but for those left out, and no other', () => {
    expect(FILES.length).toBeGreaterThan(200)
    expect(allBeneath(BUILT)).toEqual(FILES.toSorted())
  })

  test('are each the file of the engine, byte for byte', () => {
    for (const file of FILES) {
      expect(
        readFileSync(join(BUILT, file)).equals(readFileSync(join(INSTALLED, BROUGHT_IN, file))),
        file,
      ).toBe(true)
    }
  })

  test('are in that one folder of the site and nowhere else', () => {
    const elsewhere = allBeneath(join(PROJECT, 'dist')).filter(
      (file) => !file.startsWith(`${ENGINE_FOLDER}/`),
    )

    expect(elsewhere.filter((file) => /\.(wasm|jpg|xml)$/.test(file))).toEqual([])
    expect(elsewhere.filter((file) => /(^|\/)(Workers|ThirdParty|Widgets)\//.test(file))).toEqual(
      [],
    )
    expect(elsewhere.length).toBeLessThan(20)
  })

  test('are of the kinds these tests ask the site for', () => {
    const kinds = new Set(FILES.map((file) => extname(file).toLowerCase()))

    expect([...kinds].toSorted()).toEqual(
      ONE_OF_EACH_KIND.map(([file]) => extname(file)).toSorted(),
    )
  })

  for (const [file, type] of ONE_OF_EACH_KIND) {
    test(`${file} is answered as what it is, under the site's path`, async ({ request }) => {
      const response = await request.get(`${ENGINE_FOLDER}/${file}`, { maxRedirects: 0 })

      expect(response.status()).toBe(200)
      expect(new URL(response.url()).pathname).toBe(`${SITE_PATH}${ENGINE_FOLDER}/${file}`)
      expect(response.headers()['content-type']).toMatch(type)
      expect((await response.body()).equals(readFileSync(join(INSTALLED, BROUGHT_IN, file)))).toBe(
        true,
      )
    })
  }

  test('are each answered with the bytes of the engine', async ({ request }) => {
    const wrong: string[] = []
    for (const file of FILES) {
      const response = await request.get(`${ENGINE_FOLDER}/${file}`, { maxRedirects: 0 })
      const same =
        response.status() === 200 &&
        (await response.body()).equals(readFileSync(join(INSTALLED, BROUGHT_IN, file)))
      if (!same) {
        wrong.push(`${file}: ${response.status()}`)
      }
    }

    expect(wrong).toEqual([])
  })

  test("the engine's licence is in the site's file of licences", async ({ request }) => {
    const response = await request.get(LICENCES_FILE)
    const licence = readFileSync(join(INSTALLED, 'LICENSE.md'), 'utf8')

    expect(response.status()).toBe(200)
    expect(licence).toContain('Apache License')
    expect(await response.text()).toContain(licence.replaceAll('\r\n', '\n').trim())
  })

  // Written out here, and not read from the list of the step: a logo that
  // is taken off that list is in the site, and these tests say so.
  for (const [whose, logo] of [
    ['Bing Maps', 'bing_maps_credit.png'],
    ['Google Earth', 'google_earth_credit.png'],
  ] as const) {
    test(`the logo of ${whose}, which the engine brings, is not in the site`, async ({
      request,
    }) => {
      const response = await request.get(`${ENGINE_FOLDER}/Assets/Images/${logo}`, {
        maxRedirects: 0,
      })

      expect(readdirSync(join(INSTALLED, BROUGHT_IN, 'Assets/Images'))).toContain(logo)
      expect(response.status()).toBe(404)
      expect(FILES).not.toContain(`Assets/Images/${logo}`)
    })
  }

  for (const [said, address] of [
    ['a file the engine does not bring', `${ENGINE_FOLDER}/Workers/nothing-here.js`],
    ["the rest of the engine's package", `${ENGINE_FOLDER}/package.json`],
    ["the engine's own code, which the build takes in", `${ENGINE_FOLDER}/index.js`],
    ['a file of the engine outside its folder', 'Workers/createTaskProcessorWorker.js'],
    [
      'the folder the engine keeps them in',
      `${ENGINE_FOLDER}/${BROUGHT_IN}/Workers/createTaskProcessorWorker.js`,
    ],
    [
      'the folder of the installed packages',
      `${ENGINE_PACKAGE}/${BROUGHT_IN}/Workers/createTaskProcessorWorker.js`,
    ],
  ] as const) {
    test(`${said} is not in the site`, async ({ request }) => {
      const response = await request.get(address, { maxRedirects: 0 })

      expect(response.status()).toBe(404)
    })
  }

  test('are not at the root of the server', async ({ request }) => {
    const response = await request.get(`/${ENGINE_FOLDER}/Workers/createTaskProcessorWorker.js`, {
      maxRedirects: 0,
    })

    expect(response.status()).toBe(404)
  })
})
