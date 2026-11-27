import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  gather,
  LICENCES_FILE,
  licences,
  LicencesError,
  shippedIn,
  TEXT_GIVEN_WITH,
  textsOf,
  written,
} from './licences.ts'

// A folder of its own for every test, made up for the purpose and taken away
// afterwards.
let folder: string

beforeEach(() => {
  folder = mkdtempSync(join(tmpdir(), 'motosphere-licences-'))
})

afterEach(() => {
  rmSync(folder, { recursive: true, force: true })
})

/** Writes files into the test's folder, each with the folders it needs. */
function put(files: Record<string, string | Uint8Array>): void {
  for (const [name, content] of Object.entries(files)) {
    mkdirSync(dirname(join(folder, name)), { recursive: true })
    writeFileSync(join(folder, name), content)
  }
}

/** Writes a lock file into the test's folder that installs the packages given. */
function lock(packages: Record<string, Record<string, unknown>>): void {
  put({
    'package-lock.json': JSON.stringify({ packages: { '': { name: 'a project' }, ...packages } }),
  })
}

describe('the packages a lock file installs for the site', () => {
  it('are those that are not only for the work, by name', () => {
    const found = shippedIn({
      packages: {
        '': { name: 'a project', version: '1.0.0' },
        'node_modules/two': { version: '2.0.0', license: 'ISC' },
        'node_modules/tool': { version: '9.0.0', license: 'MIT', dev: true },
        'node_modules/@one/part': { version: '1.2.3', license: '(MIT AND Zlib)' },
        'node_modules/three': { version: '3.0.0', license: 'MIT', optional: true },
        'node_modules/tool/node_modules/inner': { version: '0.1.0', license: 'MIT', dev: true },
      },
    })

    expect(found).toEqual([
      {
        where: 'node_modules/@one/part',
        name: '@one/part',
        version: '1.2.3',
        licence: '(MIT AND Zlib)',
        optional: false,
      },
      {
        where: 'node_modules/three',
        name: 'three',
        version: '3.0.0',
        licence: 'MIT',
        optional: true,
      },
      { where: 'node_modules/two', name: 'two', version: '2.0.0', licence: 'ISC', optional: false },
    ])
  })

  it('include a package once for every place it is put', () => {
    const found = shippedIn({
      packages: {
        'node_modules/two/node_modules/@one/part': { version: '1.0.0', license: 'MIT' },
        'node_modules/two': { version: '2.0.0', license: 'ISC' },
        'node_modules/@one/part': { version: '1.2.3', license: 'MIT' },
      },
    })

    expect(found.map(({ name, version, where }) => [name, version, where])).toEqual([
      ['@one/part', '1.2.3', 'node_modules/@one/part'],
      ['@one/part', '1.0.0', 'node_modules/two/node_modules/@one/part'],
      ['two', '2.0.0', 'node_modules/two'],
    ])
  })

  it('count a package as only for the work when the lock file says exactly that', () => {
    const found = shippedIn({
      packages: {
        'node_modules/one': { version: '1.0.0', license: 'MIT', dev: false },
        'node_modules/two': { version: '1.0.0', license: 'MIT', dev: 'true' },
        'node_modules/three': { version: '1.0.0', license: 'MIT', devOptional: true },
      },
    })

    expect(found.map(({ name }) => name)).toEqual(['one', 'three', 'two'])
  })

  it.each([
    ['nothing', null],
    ['a text', 'packages'],
    ['a list', []],
    ['no packages', {}],
    ['packages that are a list', { packages: [] }],
    ['packages that are a text', { packages: 'none' }],
  ])('cannot be read from a lock file that is %s', (_, unusable) => {
    expect(() => shippedIn(unusable)).toThrow(
      new LicencesError('The lock file has no list of packages.'),
    )
  })

  it.each([
    ['none', { license: 'MIT' }],
    ['an empty one', { version: '', license: 'MIT' }],
    ['a number', { version: 1, license: 'MIT' }],
  ])('are refused when the version of one is %s', (_, said) => {
    expect(() => shippedIn({ packages: { 'node_modules/one': said } })).toThrow(
      new LicencesError('The lock file gives no version for node_modules/one.'),
    )
  })

  it.each([
    ['none', { version: '1.0.0' }],
    ['an empty one', { version: '1.0.0', license: '' }],
    ['only spaces', { version: '1.0.0', license: '  ' }],
    ['a list', { version: '1.0.0', license: ['MIT'] }],
  ])('are refused when the licence of one is %s', (_, said) => {
    expect(() => shippedIn({ packages: { 'node_modules/one': said } })).toThrow(
      new LicencesError('The lock file names no licence for node_modules/one.'),
    )
  })

  it('are not refused for what a package that is only for the work lacks', () => {
    expect(shippedIn({ packages: { 'node_modules/tool': { dev: true } } })).toEqual([])
  })
})

describe('the licence texts of an installed package', () => {
  it.each([
    'LICENSE',
    'LICENCE',
    'license',
    'License.md',
    'LICENSE.txt',
    'LICENSE.markdown',
    'LICENSE-MIT',
    'LICENSE-MIT.txt',
    'LICENSE-APACHE-2.0',
    'COPYING',
    'COPYING.txt',
    'NOTICE',
    'NOTICE.md',
  ])('include its file %s', (name) => {
    put({ [name]: 'The words of a licence.\n' })

    expect(textsOf(folder)).toEqual([{ file: name, text: 'The words of a licence.' }])
  })

  it.each([
    'license.js',
    'LICENSE.d.ts',
    'licence-check.sh',
    'LICENSES.json',
    'UNLICENSED',
    'README.md',
    'package.json',
    'my-license',
    'LICENSE.md.bak',
  ])('do not include its file %s', (name) => {
    put({ [name]: 'Something else.\n' })

    expect(textsOf(folder)).toEqual([])
  })

  it('do not include a folder, whatever its name', () => {
    put({ 'LICENSE/MIT.txt': 'The words of a licence.\n' })

    expect(textsOf(folder)).toEqual([])
  })

  it('come in the order of the names of the files', () => {
    put({ NOTICE: 'three', 'LICENSE-MPL': 'two', LICENSE: 'one' })

    expect(textsOf(folder)).toEqual([
      { file: 'LICENSE', text: 'one' },
      { file: 'LICENSE-MPL', text: 'two' },
      { file: 'NOTICE', text: 'three' },
    ])
  })

  it('are kept letter for letter, with plain line ends and no empty lines around them', () => {
    put({
      LICENSE:
        '\uFEFF\r\n  \r\n      The Licence\r\n\r\nCopyright (c) Jo Example\rAll  rights.  \n\tLast.\n\n \n',
    })

    expect(textsOf(folder)).toEqual([
      {
        file: 'LICENSE',
        text: '      The Licence\n\nCopyright (c) Jo Example\nAll  rights.  \n\tLast.',
      },
    ])
  })

  it('do not take the mark at the start of a file for part of its text', () => {
    put({ LICENSE: '\uFEFFThe words of a licence.\n' })

    expect(textsOf(folder)).toEqual([{ file: 'LICENSE', text: 'The words of a licence.' }])
  })

  it('are refused when a file is not text', () => {
    put({ LICENSE: Uint8Array.of(0x4d, 0x49, 0x54, 0xff, 0xfe) })

    expect(() => textsOf(folder)).toThrow(
      new LicencesError(`${join(folder, 'LICENSE')} is not text in UTF-8.`),
    )
  })

  it.each([
    ['nothing', ''],
    ['only empty lines', '\n  \n\r\n'],
  ])('are refused when a file holds %s', (_, content) => {
    put({ LICENSE: content })

    expect(() => textsOf(folder)).toThrow(new LicencesError(`${join(folder, 'LICENSE')} is empty.`))
  })
})

describe('the packages a project ships, with their licences', () => {
  it('are read from its lock file and its installed packages', () => {
    lock({
      'node_modules/two': { version: '2.0.0', license: 'ISC' },
      'node_modules/tool': { version: '9.0.0', license: 'MIT', dev: true },
      'node_modules/@one/part': { version: '1.2.3', license: 'MIT' },
      'node_modules/two/node_modules/@one/part': { version: '1.0.0', license: 'ISC' },
    })
    put({
      'node_modules/two/LICENSE': 'The licence of two.\n',
      'node_modules/two/index.js': 'export {}\n',
      'node_modules/two/node_modules/@one/part/COPYING': 'The licence of the older part.\n',
      'node_modules/@one/part/LICENSE.md': 'The licence of the part.\n',
      'node_modules/@one/part/NOTICE': 'A notice.\n',
      'node_modules/tool/LICENSE': 'The licence of the tool.\n',
    })

    expect(gather(folder, {})).toEqual([
      {
        where: 'node_modules/@one/part',
        name: '@one/part',
        version: '1.2.3',
        licence: 'MIT',
        optional: false,
        texts: [
          { file: 'LICENSE.md', text: 'The licence of the part.' },
          { file: 'NOTICE', text: 'A notice.' },
        ],
      },
      {
        where: 'node_modules/two/node_modules/@one/part',
        name: '@one/part',
        version: '1.0.0',
        licence: 'ISC',
        optional: false,
        texts: [{ file: 'COPYING', text: 'The licence of the older part.' }],
      },
      {
        where: 'node_modules/two',
        name: 'two',
        version: '2.0.0',
        licence: 'ISC',
        optional: false,
        texts: [{ file: 'LICENSE', text: 'The licence of two.' }],
      },
    ])
  })

  it('leave out a package that may be left out and is not installed', () => {
    lock({
      'node_modules/one': { version: '1.0.0', license: 'MIT' },
      'node_modules/other-system': { version: '1.0.0', license: 'MIT', optional: true },
    })
    put({ 'node_modules/one/LICENSE': 'The licence of one.\n' })

    expect(gather(folder, {}).map(({ name }) => name)).toEqual(['one'])
  })

  it('are refused when a package that must be there is not installed', () => {
    lock({ 'node_modules/one': { version: '1.0.0', license: 'MIT' } })

    expect(() => gather(folder, {})).toThrow(
      new LicencesError('one is not installed. Run "npm ci" first.'),
    )
  })

  it('are refused when a package brings no licence text and nothing says who gives it', () => {
    lock({
      'node_modules/one': { version: '1.0.0', license: 'MIT' },
      'node_modules/bare': { version: '1.0.0', license: 'MIT' },
    })
    put({
      'node_modules/one/LICENSE': 'The licence of one.\n',
      'node_modules/bare/index.js': 'export {}\n',
    })

    expect(() => gather(folder, {})).toThrow(
      new LicencesError('bare brings no licence text, and nothing says which package gives it.'),
    )
  })

  it('take a package without a licence text when it is said which package gives it', () => {
    lock({
      'node_modules/one': { version: '1.0.0', license: 'MIT' },
      'node_modules/bare': { version: '1.0.0', license: 'MIT' },
    })
    put({
      'node_modules/one/LICENSE': 'The licence of one.\n',
      'node_modules/bare/index.js': 'export {}\n',
    })

    const found = gather(folder, { bare: 'one' })

    expect(found.map(({ name, texts }) => [name, texts.length])).toEqual([
      ['bare', 0],
      ['one', 1],
    ])
  })

  it('are refused when a package is said to bring no licence text and brings one', () => {
    lock({
      'node_modules/one': { version: '1.0.0', license: 'MIT' },
      'node_modules/two': { version: '1.0.0', license: 'MIT' },
    })
    put({
      'node_modules/one/LICENSE': 'The licence of one.\n',
      'node_modules/two/LICENSE': 'The licence of two.\n',
    })

    expect(() => gather(folder, { two: 'one' })).toThrow(
      new LicencesError(
        'two brings a licence text of its own and is still listed as bringing none.',
      ),
    )
  })

  it('are refused when a package is said to bring no licence text and is not shipped', () => {
    lock({
      'node_modules/one': { version: '1.0.0', license: 'MIT' },
      'node_modules/tool': { version: '1.0.0', license: 'MIT', dev: true },
    })
    put({ 'node_modules/one/LICENSE': 'The licence of one.\n', 'node_modules/tool/index.js': '' })

    expect(() => gather(folder, { tool: 'one' })).toThrow(
      new LicencesError('tool is listed as bringing no licence text and is not shipped.'),
    )
  })

  it.each([
    ['brings none itself', 'other'],
    ['is not shipped', 'tool'],
    ['is not installed at all', 'nothing'],
  ])('are refused when the package said to give a licence %s', (_, carrier) => {
    lock({
      'node_modules/bare': { version: '1.0.0', license: 'MIT' },
      'node_modules/other': { version: '1.0.0', license: 'MIT' },
      'node_modules/tool': { version: '1.0.0', license: 'MIT', dev: true },
    })
    put({
      'node_modules/bare/index.js': '',
      'node_modules/other/index.js': '',
      'node_modules/tool/LICENSE': 'The licence of the tool.\n',
    })

    expect(() => gather(folder, { bare: carrier, other: carrier })).toThrow(
      new LicencesError(
        `bare is said to have its licence given with ${carrier}, which brings no licence text.`,
      ),
    )
  })

  it.each([
    ['is not there', undefined],
    ['is not JSON', '{ "packages": '],
  ])('are refused when the lock file %s', (_, content) => {
    if (content !== undefined) {
      put({ 'package-lock.json': content })
    }

    expect(() => gather(folder, {})).toThrow(
      new LicencesError(`${join(folder, 'package-lock.json')} cannot be read.`),
    )
  })
})

describe('the file of licences', () => {
  const one = {
    where: 'node_modules/@one/part',
    name: '@one/part',
    version: '1.2.3',
    licence: '(MIT AND Zlib)',
    optional: false,
    texts: [
      { file: 'LICENSE', text: 'The licence of the part.\n\nIts second paragraph.' },
      { file: 'NOTICE', text: 'A notice.' },
    ],
  }
  const bare = {
    where: 'node_modules/bare',
    name: 'bare',
    version: '0.1.0',
    licence: 'MIT',
    optional: false,
    texts: [],
  }
  const rule = '='.repeat(78)
  const line = '-'.repeat(78)

  it('names every package with its version and its licence, and gives the texts it brings', () => {
    expect(written([one, bare], { bare: '@one/part' })).toBe(
      [
        'MotoSphere is built with the packages listed below. Each is used under its',
        'own licence, and the licence is given here as the package itself brings it.',
        '',
        'Packages: 2',
        '',
        rule,
        '@one/part 1.2.3',
        'Licence: (MIT AND Zlib)',
        line,
        'From its file LICENSE:',
        line,
        'The licence of the part.',
        '',
        'Its second paragraph.',
        line,
        'From its file NOTICE:',
        line,
        'A notice.',
        '',
        rule,
        'bare 0.1.0',
        'Licence: MIT',
        'The package brings no licence text of its own. Its licence is given with',
        '@one/part, in this file.',
        '',
      ].join('\n'),
    )
  })

  it('says so when there is no package', () => {
    expect(written([], {})).toBe(
      [
        'MotoSphere is built with the packages listed below. Each is used under its',
        'own licence, and the licence is given here as the package itself brings it.',
        '',
        'Packages: 0',
        '',
      ].join('\n'),
    )
  })

  it('is not written for a package without a text when nothing says who gives it', () => {
    expect(() => written([one, bare], {})).toThrow(
      new LicencesError('bare has no licence text to write.'),
    )
  })

  it('has one name in the site', () => {
    expect(LICENCES_FILE).toBe('licences.txt')
  })
})

describe('the licences of this project', () => {
  // The folder of the front end: the tests are run from it.
  const project = process.cwd()
  const lockFile: unknown = JSON.parse(readFileSync(join(project, 'package-lock.json'), 'utf-8'))
  const packageFile: unknown = JSON.parse(readFileSync(join(project, 'package.json'), 'utf-8'))

  /** The names of the packages the project names in one group of its package file. */
  function namesUnder(group: 'dependencies' | 'devDependencies'): string[] {
    const named: unknown = Object.entries(Object(packageFile)).find(([key]) => key === group)?.[1]
    if (typeof named !== 'object' || named === null) {
      throw new Error(`package.json has no ${group}`)
    }
    return Object.keys(named)
  }

  it('are gathered for every package the lock file installs for the site', () => {
    const shipped = gather(project)

    expect(shipped.map(({ where }) => where)).toEqual(shippedIn(lockFile).map(({ where }) => where))
    expect(shipped.length).toBeGreaterThanOrEqual(namesUnder('dependencies').length)
  })

  it('include every package the project names as shipped, each with a text of its own', () => {
    const withText = gather(project)
      .filter(({ texts }) => texts.length > 0)
      .map(({ name }) => name)

    expect(namesUnder('dependencies').length).toBeGreaterThan(0)
    expect(namesUnder('dependencies').filter((name) => !withText.includes(name))).toEqual([])
  })

  it('include no package that is only for the work', () => {
    const names = gather(project).map(({ name }) => name)

    expect(namesUnder('devDependencies').length).toBeGreaterThan(0)
    expect(namesUnder('devDependencies').filter((name) => names.includes(name))).toEqual([])
  })

  it('give the words of the licence of React', () => {
    const react = gather(project).find(({ name }) => name === 'react')

    expect(react?.licence).toBe('MIT')
    expect(react?.texts.map(({ file }) => file)).toEqual(['LICENSE'])
    expect(react?.texts[0]?.text).toContain('MIT License')
    expect(react?.texts[0]?.text).toContain('Permission is hereby granted, free of charge')
  })

  it('have five packages without a text of their own, each read by a person', () => {
    // The engine's own licence file gives the licences of the code of others
    // that it uses, and these are among them or are the engine's own. A
    // package is added here only by someone who has read both.
    expect(TEXT_GIVEN_WITH).toEqual({
      '@cesium/wasm-splats': '@cesium/engine',
      'bitmap-sdf': '@cesium/engine',
      draco3d: '@cesium/engine',
      lerc: '@cesium/engine',
      'mersenne-twister': '@cesium/engine',
    })
  })

  it('name, for each package without a text of its own, a package that gives it', () => {
    const shipped = gather(project)
    const without = shipped.filter(({ texts }) => texts.length === 0).map(({ name }) => name)
    const withText = shipped.filter(({ texts }) => texts.length > 0).map(({ name }) => name)

    expect(without).toEqual(Object.keys(TEXT_GIVEN_WITH).toSorted())
    expect(Object.values(TEXT_GIVEN_WITH).filter((carrier) => !withText.includes(carrier))).toEqual(
      [],
    )
  })

  it('are written with one heading for every package', () => {
    const shipped = gather(project)
    const text = written(shipped)
    const rule = '='.repeat(78)

    expect(text).toContain(`Packages: ${shipped.length}\n`)
    expect(text.split('\n').filter((line) => line === rule)).toHaveLength(shipped.length)
    expect(
      shipped.filter(
        ({ name, version, licence }) =>
          !text.includes(`\n${rule}\n${name} ${version}\nLicence: ${licence}\n`),
      ),
    ).toEqual([])
  })
})

describe('the step of the build', () => {
  it('is for the build and not for the development server', () => {
    expect(licences().apply).toBe('build')
    expect(licences().name).toBe('motosphere:licences')
  })
})
