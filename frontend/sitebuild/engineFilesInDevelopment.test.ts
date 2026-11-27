import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, extname, join } from 'node:path'
import { createServer, type ViteDevServer } from 'vite'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { SITE_PATH } from '../site.ts'
import {
  BROUGHT_IN,
  ENGINE_FOLDER,
  ENGINE_PACKAGE,
  engineFiles,
  EngineFilesError,
  engineFilesInDevelopment,
  engineFilesInTheSite,
  LEFT_OUT,
  SERVED_AS,
} from './engineFiles.ts'

// These tests start the development server itself, as `npm run dev` does,
// from the folder of the front end and with the project's own settings, on
// this computer only and on a port that is free. They ask it over the
// network and hold its answers against the engine as it is installed.

// The folder of the front end: the tests are run from it.
const PROJECT = process.cwd()
const INSTALLED = join(PROJECT, ENGINE_PACKAGE, BROUGHT_IN)

/** A development server on this computer, on a free port, that writes nothing to the screen. */
async function started(settings: Parameters<typeof createServer>[0]): Promise<ViteDevServer> {
  const server = await createServer({
    logLevel: 'silent',
    // The server is not asked to watch the files for changes: no test changes
    // one it would have to tell a browser about.
    server: { host: '127.0.0.1', port: 0, watch: null },
    ...settings,
  })
  await server.listen()
  return server
}

/** The address of the site's path on a server that was started. */
function siteOf(server: ViteDevServer): string {
  const address = server.httpServer?.address()
  if (address === null || address === undefined || typeof address === 'string') {
    throw new Error('The development server does not say which port it has.')
  }
  return `http://127.0.0.1:${address.port}${server.config.base}`
}

describe('the development server of this project', () => {
  let server: ViteDevServer
  let site: string
  let cache: string

  beforeAll(async () => {
    // What the server keeps for itself goes to a folder of its own, so that
    // a test leaves nothing in the folder of the project.
    cache = mkdtempSync(join(tmpdir(), 'motosphere-dev-cache-'))
    server = await started({ root: PROJECT, cacheDir: cache })
    site = siteOf(server)
  })

  afterAll(async () => {
    await server.close()
    rmSync(cache, { recursive: true, force: true })
  })

  /** Asks the server for an address beneath the site's path, and follows no redirect. */
  function ask(address: string, method = 'GET'): Promise<Response> {
    return fetch(`${site}${address}`, { method, redirect: 'manual' })
  }

  it("serves the site under the site's path, on this computer only", () => {
    expect(server.config.base).toBe(SITE_PATH)
    expect(site).toMatch(/^http:\/\/127\.0\.0\.1:\d+\/MotoSphere\/$/)
  })

  it('answers every file the built site has of the engine, each with the bytes of the engine', async () => {
    const files = engineFiles(PROJECT)
    expect(files.length).toBeGreaterThan(200)

    const answered: string[] = []
    for (const file of files) {
      const response = await ask(`${ENGINE_FOLDER}/${file}`)
      const content = Buffer.from(await response.arrayBuffer())
      if (response.status === 200 && content.equals(readFileSync(join(INSTALLED, file)))) {
        answered.push(file)
      }
    }

    expect(answered).toEqual(files)
  })

  it('says of every such file what kind it is, and how long', async () => {
    const said: Record<string, [string | null, string | null]> = {}
    const expected: Record<string, [string | null, string | null]> = {}
    for (const file of engineFiles(PROJECT)) {
      const response = await ask(`${ENGINE_FOLDER}/${file}`, 'HEAD')
      said[file] = [response.headers.get('content-type'), response.headers.get('content-length')]
      expected[file] = [
        SERVED_AS[extname(file)] ?? null,
        String(readFileSync(join(INSTALLED, file)).length),
      ]
    }

    expect(said).toEqual(expected)
  })

  // One file of each kind the engine brings, with what a browser must be
  // told it is. A script or a program told to be anything else is not run.
  it.each([
    ['Workers/createTaskProcessorWorker.js', 'text/javascript'],
    ['ThirdParty/draco_decoder.wasm', 'application/wasm'],
    ['Assets/approximateTerrainHeights.json', 'application/json'],
    ['Widgets/CesiumWidget/CesiumWidget.css', 'text/css'],
    ['Assets/Textures/NaturalEarthII/0/0/0.jpg', 'image/jpeg'],
    ['Assets/Textures/maki/marker.png', 'image/png'],
    ['Assets/Textures/pin.svg', 'image/svg+xml'],
    ['Assets/Textures/NaturalEarthII/tilemapresource.xml', 'application/xml'],
  ] as const)('answers %s as %s', async (file, kind) => {
    const response = await ask(`${ENGINE_FOLDER}/${file}`)

    expect(response.status).toBe(200)
    expect(new URL(response.url).pathname).toBe(`${SITE_PATH}${ENGINE_FOLDER}/${file}`)
    expect(response.headers.get('content-type')).toBe(kind)
    expect((await response.arrayBuffer()).byteLength).toBeGreaterThan(0)
  })

  it('answers a file that is asked for with a question after its name', async () => {
    const file = 'Assets/approximateTerrainHeights.json'

    const response = await ask(`${ENGINE_FOLDER}/${file}?v=1`)

    expect(response.status).toBe(200)
    expect(
      Buffer.from(await response.arrayBuffer()).equals(readFileSync(join(INSTALLED, file))),
    ).toBe(true)
  })

  it('answers a question about a file without the file', async () => {
    const response = await ask(`${ENGINE_FOLDER}/ThirdParty/draco_decoder.wasm`, 'HEAD')

    expect(response.status).toBe(200)
    expect((await response.arrayBuffer()).byteLength).toBe(0)
  })

  it.each(Object.keys(LEFT_OUT))(
    'answers "not found" for %s, which the engine brings and the site leaves out',
    async (file) => {
      expect(readFileSync(join(INSTALLED, file)).length).toBeGreaterThan(0)

      const response = await ask(`${ENGINE_FOLDER}/${file}`)

      expect(response.status).toBe(404)
      expect((await response.arrayBuffer()).byteLength).toBe(0)
    },
  )

  it.each([
    ['a file the engine does not bring', 'Workers/nothing-here.js'],
    ['a file of a kind the engine does not bring', 'Assets/nothing-here.webp'],
    ['the folder itself', ''],
    ['a folder in it', 'Workers/'],
    ['a folder in it, named without its last stroke', 'Workers'],
    ['the code of the engine, which is not among its files', 'Source/Core/buildModuleUrl.js'],
    ['a name that leaves the folder, written with "%"', '..%2F..%2Fpackage.json'],
    ['a name that leaves the folder for the rest of the package', 'Workers/..%2F..%2Fpackage.json'],
    ['a name with a stroke the other way', 'Workers%5CcreateTaskProcessorWorker.js'],
    ['a name that cannot be read', 'Workers/%E0%A4%A'],
    ['a file of the engine named in capitals', 'WORKERS/CREATETASKPROCESSORWORKER.JS'],
    ['a file of the engine named in small letters', 'workers/createtaskprocessorworker.js'],
  ] as const)('answers "not found" for %s', async (_, name) => {
    const response = await ask(`${ENGINE_FOLDER}/${name}`)

    expect(response.status).toBe(404)
  })

  it('answers no file of the engine to a request that would change something', async () => {
    const answers: Record<string, [number, number]> = {}
    for (const method of ['POST', 'PUT', 'DELETE']) {
      const response = await ask(`${ENGINE_FOLDER}/ThirdParty/draco_decoder.wasm`, method)
      answers[method] = [response.status, (await response.arrayBuffer()).byteLength]
    }

    expect(answers).toEqual({ POST: [404, 0], PUT: [404, 0], DELETE: [404, 0] })
  })

  // The published site is files, and an address that names no file is
  // answered "not found" there. The development server answers the same,
  // outside the engine's folder too (FND-052 asked this by hand).
  it.each([
    'nothing-here',
    'nothing-here.png',
    'nothing-here.html',
    'nothing/here/at-all.json',
    'assets/',
    `${ENGINE_FOLDER}-nothing/Workers/createTaskProcessorWorker.js`,
    'Workers/createTaskProcessorWorker.js',
  ])('answers "not found" for %s, which names no file, and not the page', async (address) => {
    const response = await ask(address)

    expect(response.status).toBe(404)
    expect(await response.text()).not.toContain('<div id="root">')
  })

  it("does not answer the engine's files at the root of the server", async () => {
    const response = await fetch(new URL(`/${ENGINE_FOLDER}/ThirdParty/draco_decoder.wasm`, site), {
      redirect: 'manual',
    })

    expect(response.status).not.toBe(200)
    expect(response.headers.get('content-type')).not.toBe('application/wasm')
  })

  it.each([
    ['the path itself', ''],
    ['the file of the page', 'index.html'],
    ['the path with a question after it', '?from=a-link'],
  ] as const)('still answers the page at %s', async (_, address) => {
    const response = await ask(address)

    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toMatch(/^text\/html\b/)
    expect(await response.text()).toContain('<div id="root">')
  })

  it('still answers the application and what it is made of', async () => {
    const code = await ask('src/main.tsx')
    const icon = await ask('favicon.svg')

    expect(code.status).toBe(200)
    expect(code.headers.get('content-type')).toMatch(/^text\/javascript\b/)
    expect(await code.text()).toContain('createRoot')
    expect(icon.status).toBe(200)
    expect(icon.headers.get('content-type')).toMatch(/^image\/svg\+xml\b/)
    expect(await icon.text()).toContain('<svg')
  })
})

describe('the development server of a project made up for the test', () => {
  // A folder of its own for every test, taken away afterwards. It stands for
  // the folder of a project, and no settings file of this project is read.
  let project: string
  let server: ViteDevServer | undefined

  beforeEach(() => {
    project = mkdtempSync(join(tmpdir(), 'motosphere-dev-'))
    server = undefined
  })

  afterEach(async () => {
    await server?.close()
    rmSync(project, { recursive: true, force: true })
  })

  /** Writes files into the folder the engine of the test's project fetches from. */
  function bring(files: readonly string[]): void {
    for (const name of files) {
      const path = join(project, ENGINE_PACKAGE, BROUGHT_IN, name)
      mkdirSync(dirname(path), { recursive: true })
      writeFileSync(path, `the content of ${name}`)
    }
  }

  /** Starts the server of the test's project with the step and nothing else of this project. */
  function start(base = '/a-site/'): Promise<ViteDevServer> {
    return started({
      root: project,
      base,
      configFile: false,
      appType: 'mpa',
      cacheDir: join(project, 'cache'),
      plugins: [engineFilesInDevelopment()],
    })
  }

  it('answers the files of that project under the path of that site', async () => {
    bring([...Object.keys(LEFT_OUT), 'Workers/one.js', 'Assets/Deep/Down/table.json'])
    server = await start()
    const site = siteOf(server)

    const script = await fetch(`${site}${ENGINE_FOLDER}/Workers/one.js`)
    const table = await fetch(`${site}${ENGINE_FOLDER}/Assets/Deep/Down/table.json`)
    const logo = await fetch(`${site}${ENGINE_FOLDER}/${Object.keys(LEFT_OUT)[0]}`)

    expect(site).toMatch(/\/a-site\/$/)
    expect(script.status).toBe(200)
    expect(script.headers.get('content-type')).toBe('text/javascript')
    expect(await script.text()).toBe('the content of Workers/one.js')
    expect(table.status).toBe(200)
    expect(table.headers.get('content-type')).toBe('application/json')
    expect(await table.text()).toBe('the content of Assets/Deep/Down/table.json')
    expect(logo.status).toBe(404)
  })

  it('answers a file whose name the address writes with "%"', async () => {
    bring([...Object.keys(LEFT_OUT), 'Assets/a table.json'])
    server = await start()

    const table = await fetch(`${siteOf(server)}${ENGINE_FOLDER}/Assets/a%20table.json`)

    expect(table.status).toBe(200)
    expect(await table.text()).toBe('the content of Assets/a table.json')
  })

  it('answers nothing in that folder but the files of the engine, whatever the project has there', async () => {
    bring([...Object.keys(LEFT_OUT), 'Workers/one.js'])
    for (const beside of [
      `${ENGINE_FOLDER}/of-the-project.js`,
      `public/${ENGINE_FOLDER}/public.js`,
    ]) {
      mkdirSync(dirname(join(project, beside)), { recursive: true })
      writeFileSync(join(project, beside), 'not a file of the engine')
    }
    writeFileSync(join(project, 'beside.js'), 'a file of the project')
    mkdirSync(join(project, 'other', ENGINE_FOLDER), { recursive: true })
    writeFileSync(join(project, 'other', ENGINE_FOLDER, 'elsewhere.js'), 'a file of the project')
    server = await start()
    const site = siteOf(server)

    const ofTheProject = await fetch(`${site}${ENGINE_FOLDER}/of-the-project.js`)
    const ofThePublicFolder = await fetch(`${site}${ENGINE_FOLDER}/public.js`)
    const beside = await fetch(`${site}beside.js`)
    const elsewhere = await fetch(`${site}other/${ENGINE_FOLDER}/elsewhere.js`)

    expect(ofTheProject.status).toBe(404)
    expect(ofThePublicFolder.status).toBe(404)
    expect(beside.status).toBe(200)
    // A folder of the same name elsewhere is none of the step's business.
    expect(elsewhere.status).toBe(200)
  })

  it('answers a file as it is now, and not as it was when the server started', async () => {
    bring([...Object.keys(LEFT_OUT), 'Workers/one.js'])
    server = await start()
    const address = `${siteOf(server)}${ENGINE_FOLDER}/Workers/one.js`
    expect(await (await fetch(address)).text()).toBe('the content of Workers/one.js')

    writeFileSync(join(project, ENGINE_PACKAGE, BROUGHT_IN, 'Workers/one.js'), 'another content')

    expect(await (await fetch(address)).text()).toBe('another content')
  })

  it('does not start when the engine is not installed, and says so', async () => {
    await expect(start()).rejects.toThrow(EngineFilesError)
    await expect(start()).rejects.toThrow(
      `${join(project, ENGINE_PACKAGE, BROUGHT_IN)} cannot be read. Run "npm ci" first.`,
    )
  })

  it('does not start when a file listed as left out is not there', async () => {
    bring(['Workers/one.js'])

    await expect(start()).rejects.toThrow(
      'Assets/Images/bing_maps_credit.png is listed as left out, and the engine does not bring it.',
    )
  })

  it('does not start when the engine brings a file of a kind it has no type for, which is named', async () => {
    bring([...Object.keys(LEFT_OUT), 'Workers/one.js', 'Assets/picture.webp'])

    await expect(start()).rejects.toThrow(EngineFilesError)
    await expect(start()).rejects.toThrow(
      'Assets/picture.webp is of a kind the development server has no type for.',
    )
  })
})

describe('what the development server says a file of the engine is', () => {
  it('is said for each kind the engine brings, and for no other', () => {
    const kinds = new Set(engineFiles(PROJECT).map((name) => extname(name)))

    expect(Object.keys(SERVED_AS).toSorted()).toEqual([...kinds].toSorted())
  })

  it('is what a browser needs to be told', () => {
    expect(SERVED_AS).toEqual({
      '.css': 'text/css',
      '.jpg': 'image/jpeg',
      '.js': 'text/javascript',
      '.json': 'application/json',
      '.png': 'image/png',
      '.svg': 'image/svg+xml',
      '.wasm': 'application/wasm',
      '.xml': 'application/xml',
    })
  })
})

describe('the step of the development server', () => {
  it('is for the development server and not for the build', () => {
    expect(engineFilesInDevelopment().apply).toBe('serve')
    expect(engineFilesInDevelopment().name).toBe('motosphere:engine-files-in-development')
  })

  it('leaves the step of the build as it was', () => {
    expect(engineFilesInTheSite().apply).toBe('build')
    expect(Object.keys(engineFilesInTheSite())).not.toContain('configureServer')
    expect(Object.keys(engineFilesInDevelopment())).not.toContain('generateBundle')
  })
})
