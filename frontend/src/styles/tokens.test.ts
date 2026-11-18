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

// The owner's Graphite theme (docs/design/graphite-theme/graphite-theme.css),
// written out here so a changed colour is caught.
const GRAPHITE_COLOURS: [string, string][] = [
  ['--color-bar', '#1b1c1f'],
  ['--color-canvas', '#1d1e21'],
  ['--color-panel', '#222327'],
  ['--color-window', '#2a2b2f'],
  ['--color-control', '#35373c'],
  ['--color-pressed', '#3d4046'],
  ['--color-border', '#383a40'],
  ['--color-control-border', '#4a4d54'],
  ['--color-text', '#ececee'],
  ['--color-subtext', '#a9acb3'],
  ['--color-disabled', '#75787f'],
  ['--color-accent', '#2580ee'],
  ['--color-on-accent', '#ffffff'],
  ['--color-accent-sky', '#5ea8ff'],
  ['--color-accent-light', '#8cc4ff'],
  ['--color-selection', '#2f4a6e'],
]

const EXPECTED_TOKENS = [
  '--color-bar',
  '--color-canvas',
  '--color-panel',
  '--color-window',
  '--color-control',
  '--color-pressed',
  '--color-border',
  '--color-control-border',
  '--color-text',
  '--color-subtext',
  '--color-disabled',
  '--color-accent',
  '--color-on-accent',
  '--color-accent-sky',
  '--color-accent-light',
  '--color-selection',
  '--gradient-accent',
  '--color-success',
  '--color-warning',
  '--color-danger',
  '--color-info',
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
  '--size-top-bar',
  '--size-sections-panel',
  '--size-details-panel',
  '--size-touch-target',
  '--radius-sm',
  '--radius-md',
  '--radius-lg',
  '--duration-fast',
  '--duration-normal',
  '--easing-standard',
]

// Surfaces that whole areas of the page sit on.
const PAGE_SURFACES = ['--color-bar', '--color-canvas', '--color-panel', '--color-window']
// Page surfaces plus the control and pressed states.
const ALL_SURFACES = [...PAGE_SURFACES, '--color-control', '--color-pressed']

type ContrastCase = [string, string, number]

function onEach(foreground: string, backgrounds: string[], minimum: number): ContrastCase[] {
  return backgrounds.map((background): ContrastCase => [foreground, background, minimum])
}

// 7:1 is WCAG AAA for text, 4.5:1 is AA for text, 3:1 is AA for large or
// bold text and for non-text parts such as the focus ring.
const CONTRAST_CASES: ContrastCase[] = [
  ...onEach('--color-text', [...ALL_SURFACES, '--color-selection'], 7),
  ...onEach('--color-subtext', ALL_SURFACES, 4.5),
  ...onEach('--color-accent-sky', [...PAGE_SURFACES, '--color-control'], 4.5),
  ...onEach('--color-accent-sky', ['--color-pressed', '--color-selection'], 3),
  ...onEach('--color-accent-light', ALL_SURFACES, 4.5),
  ...['--color-success', '--color-warning', '--color-danger', '--color-info'].flatMap((status) =>
    onEach(status, PAGE_SURFACES, 4.5),
  ),
  ...onEach('--color-disabled', PAGE_SURFACES, 3),
  // Deliberate: white on the owner's accent blue measures 3.89:1. That meets
  // 3:1 (large or bold text) but not 4.5:1. The owner has been told, and the
  // pair is used for bold button labels only. Do not raise this threshold and
  // do not change the colour.
  ['--color-on-accent', '--color-accent', 3],
]

const RAW_COLOUR = /#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\(/i

describe('design tokens', () => {
  it('defines exactly the agreed set of tokens', () => {
    expect([...tokens.keys()].toSorted()).toEqual(EXPECTED_TOKENS.toSorted())
  })

  it('defines each token only once', () => {
    expect(declarations).toHaveLength(tokens.size)
  })

  it("uses exactly the owner's Graphite colours", () => {
    for (const [name, value] of GRAPHITE_COLOURS) {
      expect({ name, value: token(name) }).toEqual({ name, value })
    }
  })

  it('writes every colour as a six-digit hex value', () => {
    const colours = declarations.filter(([name]) => name.startsWith('--color-'))
    expect(colours).toHaveLength(20)
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
