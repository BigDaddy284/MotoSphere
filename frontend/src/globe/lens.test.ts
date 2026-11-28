import { describe, expect, it } from 'vitest'
import { distanceOfTheWholeEarth, SHARE_OF_THE_SHORTER_SIDE } from './homeView.ts'
import { ANGLE_ACROSS_THE_SHORTER_SIDE, angleAcrossTheLongerSide } from './lens.ts'

/** An angle given in degrees, as the engine and the arithmetic take it. */
function degrees(angle: number): number {
  return (angle * Math.PI) / 180
}

/**
 * The angle the shorter side of a surface is seen under when the engine
 * holds an angle across the longer side: what the engine itself works out
 * for the side its angle is not across.
 */
function acrossTheShorterSide(width: number, height: number, acrossTheLonger: number): number {
  const shorterOverLonger = Math.min(width, height) / Math.max(width, height)
  return 2 * Math.atan(Math.tan(acrossTheLonger / 2) * shorterOverLonger)
}

// The stage at the screen sizes the layout knows, as the browser tests
// measure it, with the panels beside it open and closed.
const STAGES: [name: string, width: number, height: number][] = [
  ['a desktop with both panels open', 700, 672],
  ['a desktop with one panel open', 920, 672],
  ['a desktop with both panels closed', 1280, 672],
  ['a phone held upright', 390, 745],
  ['a phone lying', 844, 312],
  ['a tablet', 768, 946],
  ['a wide screen', 1340, 1032],
  ['the smallest phone', 320, 469],
]

describe('the angle the globe sees across the shorter side', () => {
  it('is 36 degrees', () => {
    expect(ANGLE_ACROSS_THE_SHORTER_SIDE).toBeCloseTo(degrees(36), 15)
  })
})

describe('angleAcrossTheLongerSide', () => {
  it('is the same angle on a square surface', () => {
    expect(angleAcrossTheLongerSide(500, 500, degrees(36))).toBeCloseTo(degrees(36), 12)
  })

  it('is 90 degrees where the surface is twice as wide as high and the height is seen under the angle whose half has the tangent a half', () => {
    const height = 2 * Math.atan(0.5)
    expect(angleAcrossTheLongerSide(1000, 500, height)).toBeCloseTo(degrees(90), 12)
  })

  it('is 60 degrees, the angle of the engine, on a surface 16 by 9 seen under 36 degrees, to a twentieth of a degree', () => {
    const angle = angleAcrossTheLongerSide(1600, 900, ANGLE_ACROSS_THE_SHORTER_SIDE)
    expect(Math.abs(angle - degrees(60))).toBeLessThan(degrees(0.05))
  })

  it('does not ask which side is the longer one', () => {
    expect(angleAcrossTheLongerSide(390, 745, degrees(36))).toBe(
      angleAcrossTheLongerSide(745, 390, degrees(36)),
    )
  })

  it('is wider the longer the surface is for its shorter side', () => {
    const square = angleAcrossTheLongerSide(672, 672, degrees(36))
    const wide = angleAcrossTheLongerSide(920, 672, degrees(36))
    const wider = angleAcrossTheLongerSide(1280, 672, degrees(36))
    expect(square).toBeLessThan(wide)
    expect(wide).toBeLessThan(wider)
  })

  it('stays under a half turn however long the surface is', () => {
    const angle = angleAcrossTheLongerSide(100_000, 1, degrees(36))
    expect(angle).toBeGreaterThan(degrees(179))
    expect(angle).toBeLessThan(Math.PI)
  })

  it('takes a surface that has no size yet for a square one', () => {
    expect(angleAcrossTheLongerSide(0, 0, degrees(36))).toBeCloseTo(degrees(36), 12)
    expect(angleAcrossTheLongerSide(300, 0, degrees(36))).toBeCloseTo(degrees(36), 12)
    expect(angleAcrossTheLongerSide(0, 300, degrees(36))).toBeCloseTo(degrees(36), 12)
  })

  it.each(STAGES)(
    'has the engine see the shorter side of %s under 36 degrees',
    (_name, width, height) => {
      const longer = angleAcrossTheLongerSide(width, height, ANGLE_ACROSS_THE_SHORTER_SIDE)
      expect(acrossTheShorterSide(width, height, longer)).toBeCloseTo(degrees(36), 12)
    },
  )

  it.each(STAGES)(
    'puts the whole Earth as far away on %s as on any other stage',
    (_name, width, height) => {
      const longer = angleAcrossTheLongerSide(width, height, ANGLE_ACROSS_THE_SHORTER_SIDE)
      const distance = distanceOfTheWholeEarth(width, height, longer, SHARE_OF_THE_SHORTER_SIDE)
      // Four fifths of a side seen under 36 degrees: the Earth is seen
      // under the angle whose tangent is four fifths of that of 18 degrees.
      const everywhere = 1 / Math.sin(Math.atan(0.8 * Math.tan(degrees(18))))
      expect(distance).toBeCloseTo(everywhere, 10)
      expect(distance).toBeCloseTo(3.9749, 3)
    },
  )
})
