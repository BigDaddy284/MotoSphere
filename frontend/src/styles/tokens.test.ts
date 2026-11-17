import { describe, expect, it } from 'vitest'
import { contrastRatio } from '../test/contrast.ts'
import tokensCss from './tokens.css?raw'

// Every style sheet under src/, so style sheets added later are checked too.
const styleSheets = import.meta.glob<string>('../**/*.css', {
  query: '?raw',
  import: 'default',
  eager: true,
})

const TOKEN_DECLARATION = /(--[a-z0-9-]+)\s*:\s*([^;]+);/g

function stripComments(css: string): string {
  return css.replaceAll(/\/\*[\s\S]*?\*\//g, '')
}

function parseDeclarations(css: string): [string, string][] {
  return [...stripComments(css).matchAll(TOKEN_DECLARATION)].map((match): [string, string] => [
    match[1] ?? '',
    (match[2] ?? '').trim(),
  ])
}

const declarations = parseDeclarations(tokensCss)
const tokens = new Map(declarations)

function token(name: string): string {
  const value = tokens.get(name)
  if (value === undefined) {
    throw new Error(`Token ${name} is not defined in tokens.css`)
  }
  return value
}

const EXPECTED_TOKENS = [
  '--color-bg',
  '--color-surface',
  '--color-surface-raised',
  '--color-border',
  '--color-text',
  '--color-text-muted',
  '--color-accent',
  '--color-on-accent',
  '--color-success',
  '--color-warning',
  '--color-danger',
  '--color-info',
  '--color-focus',
  '--font-sans',
  '--font-mono',
  '--font-size-sm',
  '--font-size-md',
  '--font-size-lg',
  '--font-size-xl',
  '--font-size-2xl',
  '--font-weight-regular',
  '--font-weight-medium',
  '--font-weight-bold',
  '--line-height-tight',
  '--line-height-normal',
  '--space-1',
  '--space-2',
  '--space-3',
  '--space-4',
  '--space-5',
  '--space-6',
  '--space-7',
  '--radius-sm',
  '--radius-md',
  '--radius-lg',
  '--duration-fast',
  '--duration-normal',
  '--easing-standard',
]

const SURFACES = ['--color-bg', '--color-surface', '--color-surface-raised']

// 7:1 is WCAG AAA for text, 4.5:1 is AA for text, 3:1 is AA for non-text
// parts such as the focus ring.
const FOREGROUNDS: [string, number][] = [
  ['--color-text', 7],
  ['--color-text-muted', 4.5],
  ['--color-accent', 4.5],
  ['--color-success', 4.5],
  ['--color-warning', 4.5],
  ['--color-danger', 4.5],
  ['--color-info', 4.5],
  ['--color-focus', 3],
]

const CONTRAST_CASES: [string, string, number][] = [
  ...SURFACES.flatMap((surface) =>
    FOREGROUNDS.map(([foreground, minimum]): [string, string, number] => [
      foreground,
      surface,
      minimum,
    ]),
  ),
  ['--color-on-accent', '--color-accent', 4.5],
]

const RAW_COLOUR = /#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\(/i

describe('design tokens', () => {
  it('defines exactly the agreed set of tokens', () => {
    expect([...tokens.keys()].toSorted()).toEqual(EXPECTED_TOKENS.toSorted())
  })

  it('defines each token only once', () => {
    expect(declarations).toHaveLength(tokens.size)
  })

  it('writes every colour as a six-digit hex value', () => {
    const colours = declarations.filter(([name]) => name.startsWith('--color-'))
    expect(colours).toHaveLength(13)
    for (const [, value] of colours) {
      expect(value).toMatch(/^#[0-9a-f]{6}$/)
    }
  })

  it.each(CONTRAST_CASES)(
    '%s on %s has a contrast of at least %d',
    (foreground, background, minimum) => {
      expect(contrastRatio(token(foreground), token(background))).toBeGreaterThanOrEqual(minimum)
    },
  )
})

describe('style sheets', () => {
  it('finds the style sheets to check', () => {
    expect(Object.keys(styleSheets)).toEqual(expect.arrayContaining(['./tokens.css', './base.css']))
  })

  it('keep raw colours in the token file only', () => {
    const offenders = Object.entries(styleSheets)
      .filter(([path]) => path !== './tokens.css')
      .filter(([, css]) => RAW_COLOUR.test(stripComments(css)))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('only use tokens that exist', () => {
    const offenders = Object.entries(styleSheets).flatMap(([path, css]) =>
      [...stripComments(css).matchAll(/var\(\s*(--[a-z0-9-]+)/gi)]
        .map((match) => match[1] ?? '')
        .filter((name) => !tokens.has(name))
        .map((name) => `${path}: ${name}`),
    )
    expect(offenders).toEqual([])
  })
})
