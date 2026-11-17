import { describe, expect, it } from 'vitest'
import { contrastRatio, relativeLuminance } from './contrast.ts'

describe('contrast', () => {
  it('gives black on white the maximum ratio of 21', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 5)
  })

  it('gives identical colours the minimum ratio of 1', () => {
    expect(contrastRatio('#7f7f7f', '#7f7f7f')).toBe(2)
  })

  it('does not depend on the order of the colours', () => {
    expect(contrastRatio('#0b0d10', '#f2f4f7')).toBe(contrastRatio('#f2f4f7', '#0b0d10'))
  })

  it('matches the published ratio for grey #767676 on white', () => {
    expect(contrastRatio('#767676', '#ffffff')).toBeCloseTo(4.54, 2)
  })

  it('accepts upper-case hex digits', () => {
    expect(relativeLuminance('#FF7A1A')).toBe(relativeLuminance('#ff7a1a'))
  })

  it.each(['red', '#fff', '#12345g', 'rgb(0, 0, 0)', ''])('rejects %j', (colour) => {
    expect(() => relativeLuminance(colour)).toThrow(
      new Error(`Not a six-digit hex colour: "${colour}"`),
    )
  })
})
