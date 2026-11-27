import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import type { Plugin } from 'vite'

/**
 * The licences of the packages the site ships.
 *
 * The site ships code of other people: React, the engine of the globe and the
 * packages those need. Each is used under a licence, and most licences ask
 * that their text go with every copy. The build takes such notices out of the
 * code it makes, so it writes them into one file of the site instead, as each
 * package brings them.
 *
 * Which packages: every one the lock file installs that is not only for the
 * work of building and testing. That is what the build may take code from.
 */

/** The name of the file in the site that holds the licences. */
export const LICENCES_FILE = 'licences.txt'

/**
 * The packages that bring no licence text of their own, each with the package
 * whose licence file gives its licence. A package is put here by a person who
 * has read both, never by the build.
 */
export const TEXT_GIVEN_WITH: Readonly<Record<string, string>> = {
  '@cesium/wasm-splats': '@cesium/engine',
  'bitmap-sdf': '@cesium/engine',
  draco3d: '@cesium/engine',
  lerc: '@cesium/engine',
  'mersenne-twister': '@cesium/engine',
}

/** A file of a package that holds a licence, or a notice that goes with one. */
const HOLDS_A_LICENCE =
  /^(licen[cs]e|copying|notice)(-[a-z0-9]+(\.[0-9]+)*)*(\.(md|txt|markdown))?$/i

/** The licences cannot be written, and why. */
export class LicencesError extends Error {
  override name = 'LicencesError'
}

/** A package the lock file installs for the site. */
export interface Locked {
  /** Where it is put, as the lock file says: `node_modules/react`. */
  where: string
  name: string
  version: string
  /** The licence as the package names it: `MIT`, `(MIT AND Zlib)`. */
  licence: string
  /** Whether it may be left out on a computer it is not made for. */
  optional: boolean
}

/** One file of a package with a licence in it. */
export interface LicenceText {
  file: string
  text: string
}

/** A package the site ships, with the licence texts it brings. */
export interface Shipped extends Locked {
  texts: LicenceText[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** The name of a package from where the lock file puts it. */
function nameAt(where: string): string {
  const marker = 'node_modules/'
  return where.slice(where.lastIndexOf(marker) + marker.length)
}

/** The packages a lock file installs that are not only for the work, by name. */
export function shippedIn(lock: unknown): Locked[] {
  if (!isRecord(lock) || !isRecord(lock['packages'])) {
    throw new LicencesError('The lock file has no list of packages.')
  }
  const found: Locked[] = []
  for (const [where, said] of Object.entries(lock['packages'])) {
    if (where === '' || !isRecord(said) || said['dev'] === true) {
      continue
    }
    const { version, license: licence } = said
    if (typeof version !== 'string' || version === '') {
      throw new LicencesError(`The lock file gives no version for ${where}.`)
    }
    if (typeof licence !== 'string' || licence.trim() === '') {
      throw new LicencesError(`The lock file names no licence for ${where}.`)
    }
    found.push({
      where,
      name: nameAt(where),
      version,
      licence,
      optional: said['optional'] === true,
    })
  }
  // By name, and the copies of one package by where they are put. No two
  // packages are put in one place, so no two of these keys are the same.
  const byKey = new Map(found.map((one) => [`${one.name}\n${one.where}`, one]))
  return [...byKey.keys()].toSorted().flatMap((key) => byKey.get(key) ?? [])
}

/**
 * The files of an installed package that hold a licence, each by its path
 * from the package's folder, with `/` between the parts on every computer.
 * A package may bring code of others in a folder of its own, with their
 * licence beside it, so every folder is looked into. The files of a folder
 * come before those of the folders in it, each by name. A folder
 * `node_modules` is not gone into: what is put there is another package,
 * which the lock file names by itself. Nor is a link to a folder.
 */
function licenceFilesOf(folder: string, beneath = ''): string[] {
  const entries = readdirSync(join(folder, beneath), { withFileTypes: true })
  const here = entries
    .map(({ name }) => name)
    .filter((name) => HOLDS_A_LICENCE.test(name) && statSync(join(folder, beneath, name)).isFile())
    .toSorted()
    .map((name) => `${beneath}${name}`)
  const deeper = entries
    .filter((entry) => entry.isDirectory() && entry.name !== 'node_modules')
    .map(({ name }) => name)
    .toSorted()
    .flatMap((name) => licenceFilesOf(folder, `${beneath}${name}/`))
  return [...here, ...deeper]
}

/** The licence files of an installed package, as text with plain line ends. */
export function textsOf(folder: string): LicenceText[] {
  const reader = new TextDecoder('utf-8', { fatal: true })
  return licenceFilesOf(folder).map((file) => {
    let text: string
    try {
      text = reader.decode(readFileSync(join(folder, file)))
    } catch {
      throw new LicencesError(`${join(folder, file)} is not text in UTF-8.`)
    }
    // Plain line ends, and no empty lines before or after; the rest is
    // kept letter for letter.
    text = text
      .replaceAll('\r\n', '\n')
      .replaceAll('\r', '\n')
      .replace(/^(\s*\n)+/, '')
      .trimEnd()
    if (text === '') {
      throw new LicencesError(`${join(folder, file)} is empty.`)
    }
    return { file, text }
  })
}

/**
 * The packages a project ships, each with its licence texts, read from the
 * project's lock file and its installed packages.
 */
export function gather(
  project: string,
  givenWith: Readonly<Record<string, string>> = TEXT_GIVEN_WITH,
): Shipped[] {
  const lockFile = join(project, 'package-lock.json')
  let lock: unknown
  try {
    lock = JSON.parse(readFileSync(lockFile, 'utf-8'))
  } catch {
    throw new LicencesError(`${lockFile} cannot be read.`)
  }
  const shipped: Shipped[] = []
  for (const locked of shippedIn(lock)) {
    const folder = join(project, locked.where)
    if (!existsSync(folder)) {
      if (locked.optional) {
        continue
      }
      throw new LicencesError(`${locked.name} is not installed. Run "npm ci" first.`)
    }
    shipped.push({ ...locked, texts: textsOf(folder) })
  }
  const withText = new Set(shipped.filter((one) => one.texts.length > 0).map((one) => one.name))
  const names = new Set(shipped.map((one) => one.name))
  for (const one of shipped) {
    const carrier = givenWith[one.name]
    if (one.texts.length === 0 && carrier === undefined) {
      throw new LicencesError(
        `${one.name} brings no licence text, and nothing says which package gives it.`,
      )
    }
    if (one.texts.length > 0 && carrier !== undefined) {
      throw new LicencesError(
        `${one.name} brings a licence text of its own and is still listed as bringing none.`,
      )
    }
  }
  for (const [name, carrier] of Object.entries(givenWith)) {
    if (!names.has(name)) {
      throw new LicencesError(`${name} is listed as bringing no licence text and is not shipped.`)
    }
    if (!withText.has(carrier)) {
      throw new LicencesError(
        `${name} is said to have its licence given with ${carrier}, which brings no licence text.`,
      )
    }
  }
  return shipped
}

const RULE = '='.repeat(78)
const LINE = '-'.repeat(78)

/** The file of licences, for the packages given. */
export function written(
  shipped: readonly Shipped[],
  givenWith: Readonly<Record<string, string>> = TEXT_GIVEN_WITH,
): string {
  const parts = [
    [
      'MotoSphere is built with the packages listed below. Each is used under its',
      'own licence, and the licence is given here as the package itself brings it.',
      '',
      `Packages: ${shipped.length}`,
    ].join('\n'),
  ]
  for (const one of shipped) {
    const head = [RULE, `${one.name} ${one.version}`, `Licence: ${one.licence}`]
    if (one.texts.length === 0) {
      const carrier = givenWith[one.name]
      if (carrier === undefined) {
        throw new LicencesError(`${one.name} has no licence text to write.`)
      }
      head.push(
        'The package brings no licence text of its own. Its licence is given with',
        `${carrier}, in this file.`,
      )
      parts.push(head.join('\n'))
      continue
    }
    parts.push(
      [
        head.join('\n'),
        ...one.texts.map(({ file, text }) =>
          [LINE, `From its file ${file}:`, LINE, text].join('\n'),
        ),
      ].join('\n'),
    )
  }
  return `${parts.join('\n\n')}\n`
}

/** The step of the build that writes the file of licences into the site. */
export function licences(): Plugin {
  let project = process.cwd()
  return {
    name: 'motosphere:licences',
    apply: 'build',
    configResolved(config) {
      project = config.root
    },
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: LICENCES_FILE, source: written(gather(project)) })
    },
  }
}
