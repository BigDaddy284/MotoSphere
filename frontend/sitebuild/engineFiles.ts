import { readdirSync, readFileSync } from 'node:fs'
import { extname, join } from 'node:path'
import type { Plugin } from 'vite'

/**
 * The engine's own files, in the site.
 *
 * The engine of the globe does part of its work in background scripts, and
 * reads pictures and tables from files of its own. It fetches them while it
 * runs, each by its name beneath one address. They come with the package,
 * in its folder `Build`, and are not code the build takes in. This step puts
 * them into the site as they are, under one folder. The engine's licence is
 * in the site's file of licences, with those of the other packages.
 *
 * In development nothing is built, so a second step answers the same
 * addresses from the installed engine: the same files, and no other.
 */

/** The folder of the site that holds the engine's files. */
export const ENGINE_FOLDER = 'cesium'

/** The engine as it is installed, from the folder of the project. */
export const ENGINE_PACKAGE = 'node_modules/@cesium/engine'

/** The folder of the package that holds the files it fetches while it runs. */
export const BROUGHT_IN = 'Build'

/**
 * The files of the engine the site leaves out, each with why. A file is put
 * here by a person who has read what the engine does with it, never by the
 * build. Each is a picture of another company, which the engine shows only
 * with imagery of that company. The globe uses none, and a provider of
 * imagery is taken on with its terms read, its pictures with it.
 */
export const LEFT_OUT: Readonly<Record<string, string>> = {
  'Assets/Images/bing_maps_credit.png': 'The logo of Bing Maps, shown with imagery of Bing Maps.',
  'Assets/Images/google_earth_credit.png':
    'The logo of Google Earth, shown with imagery of a Google Earth server.',
}

/** The engine's files cannot be put into the site, and why. */
export class EngineFilesError extends Error {
  override name = 'EngineFilesError'
}

/**
 * Every file beneath a folder, each by its path from it, with `/` between the
 * parts on every computer. The files of a folder come before those of the
 * folders in it, each by name. Anything that is neither a file nor a folder,
 * a link among them, stops the build: the engine brings none, and the site
 * is to hold what the engine brings and nothing a link leads to.
 */
function filesBeneath(folder: string, beneath = ''): string[] {
  const entries = readdirSync(join(folder, beneath), { withFileTypes: true })
  const strange = entries.find((entry) => !entry.isFile() && !entry.isDirectory())
  if (strange !== undefined) {
    throw new EngineFilesError(
      `${join(folder, beneath, strange.name)} is neither a file nor a folder.`,
    )
  }
  const here = entries
    .filter((entry) => entry.isFile())
    .map(({ name }) => name)
    .toSorted()
    .map((name) => `${beneath}${name}`)
  const deeper = entries
    .filter((entry) => entry.isDirectory())
    .map(({ name }) => name)
    .toSorted()
    .flatMap((name) => filesBeneath(folder, `${beneath}${name}/`))
  return [...here, ...deeper]
}

/**
 * The files of the engine that go into the site, for the project given: each
 * by its path beneath the folder the engine fetches from.
 */
export function engineFiles(
  project: string,
  leftOut: Readonly<Record<string, string>> = LEFT_OUT,
): string[] {
  const folder = join(project, ENGINE_PACKAGE, BROUGHT_IN)
  let all: string[]
  try {
    all = filesBeneath(folder)
  } catch (error) {
    if (error instanceof EngineFilesError) {
      throw error
    }
    throw new EngineFilesError(`${folder} cannot be read. Run "npm ci" first.`)
  }
  if (all.length === 0) {
    throw new EngineFilesError(`${folder} holds no file.`)
  }
  for (const name of Object.keys(leftOut)) {
    if (!all.includes(name)) {
      throw new EngineFilesError(`${name} is listed as left out, and the engine does not bring it.`)
    }
  }
  return all.filter((name) => !Object.hasOwn(leftOut, name))
}

/** The step of the build that puts the engine's files into the site. */
export function engineFilesInTheSite(): Plugin {
  let project = process.cwd()
  return {
    name: 'motosphere:engine-files',
    apply: 'build',
    configResolved(config) {
      project = config.root
    },
    generateBundle() {
      const brought = join(project, ENGINE_PACKAGE, BROUGHT_IN)
      for (const file of engineFiles(project)) {
        this.emitFile({
          type: 'asset',
          fileName: `${ENGINE_FOLDER}/${file}`,
          source: readFileSync(join(brought, file)),
        })
      }
    },
  }
}

/**
 * What the development server says each kind of the engine's files is. A
 * browser runs a script and compiles a program only when it is told that
 * this is what arrives. A kind the engine did not bring before has no type
 * here, and the server does not start until a person has given it one.
 */
export const SERVED_AS: Readonly<Record<string, string>> = {
  '.css': 'text/css',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.wasm': 'application/wasm',
  '.xml': 'application/xml',
}

/**
 * The path an address asks for, without what follows a "?", and with what was
 * written as "%" and two figures read as the character it stands for. An
 * address that cannot be read so asks for nothing.
 */
function pathAsked(address: string | undefined): string | undefined {
  const path = (address ?? '').split('?', 1)[0] ?? ''
  try {
    return decodeURIComponent(path)
  } catch {
    return undefined
  }
}

/**
 * The step of the development server that answers the engine's files. The
 * development server builds nothing and answers from the folder of the
 * project, where the engine's files are not. This step answers the folder of
 * the site that holds them from the installed engine: each file the built
 * site has, with its bytes, and "not found" for every other address in that
 * folder, a file that is left out among them.
 */
export function engineFilesInDevelopment(): Plugin {
  return {
    name: 'motosphere:engine-files-in-development',
    apply: 'serve',
    configureServer(server) {
      const project = server.config.root
      const brought = join(project, ENGINE_PACKAGE, BROUGHT_IN)
      const folder = `${server.config.base}${ENGINE_FOLDER}/`
      const files = new Set(engineFiles(project))
      for (const file of files) {
        if (!Object.hasOwn(SERVED_AS, extname(file))) {
          throw new EngineFilesError(`${file} is of a kind the development server has no type for.`)
        }
      }
      server.middlewares.use((request, response, next) => {
        const path = pathAsked(request.url)
        const reads = request.method === 'GET' || request.method === 'HEAD'
        if (path === undefined || !reads || !path.startsWith(folder)) {
          next()
          return
        }
        const file = path.slice(folder.length)
        const kind = SERVED_AS[extname(file)]
        if (!files.has(file) || kind === undefined) {
          response.statusCode = 404
          response.end()
          return
        }
        const content = readFileSync(join(brought, file))
        response.statusCode = 200
        response.setHeader('Content-Type', kind)
        response.setHeader('Content-Length', content.length)
        // To a question about the file alone, the server sends no content.
        response.end(content)
      })
    },
  }
}
