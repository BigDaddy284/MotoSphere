import { describe, expect, it } from 'vitest'
import { distanceOfTheWholeEarth, HOME, SHARE_OF_THE_SHORTER_SIDE } from './homeView.ts'

/** An angle given in degrees, as the engine and the arithmetic take it. */
function degrees(angle: number): number {
  return (angle * Math.PI) / 180
}

/**
 * The share of the shorter side of a surface that a ball of radius 1 takes
 * when it is seen from a distance, with the field of view held across the
 * longer side: worked out from the angle the ball is seen under.
 */
function shareSeen(distance: number, width: number, height: number, fieldOfView: number): number {
  const seenUnder = Math.asin(1 / distance)
  const halfTheLongerSide = Math.tan(fieldOfView / 2)
  const halfTheShorterSide = (halfTheLongerSide * Math.min(width, height)) / Math.max(width, height)
  return Math.tan(seenUnder) / halfTheShorterSide
}

// The stage at the screen sizes the layout knows, as the browser tests
// measure it: a desktop, a phone held upright and lying, a tablet, a wide
// screen, and the smallest phone.
const STAGES: [name: string, width: number, height: number][] = [
  ['a desktop', 700, 672],
  ['a phone held upright', 390, 745],
  ['a phone lying', 844, 312],
  ['a tablet', 768, 946],
  ['a wide screen', 1340, 1032],
  ['the smallest phone', 320, 469],
]

describe('the place the globe opens above', () => {
  it('is the middle of the North Atlantic', () => {
    expect(HOME).toEqual({ longitude: -40, latitude: 30 })
  })
})

describe('the share of the shorter side the Earth takes', () => {
  it('is four fifths', () => {
    expect(SHARE_OF_THE_SHORTER_SIDE).toBe(0.8)
  })
})

describe('distanceOfTheWholeEarth', () => {
  it('is two radii where the Earth is to fill a square surface seen under 60 degrees', () => {
    // Half the side is seen under 30 degrees, and the sine of 30 degrees is a half.
    expect(distanceOfTheWholeEarth(500, 500, degrees(60), 1)).toBeCloseTo(2, 12)
  })

  it('is the root of five radii where the surface is twice as wide as high, seen under 90 degrees', () => {
    // Half the height is seen under the angle whose tangent is a half.
    expect(distanceOfTheWholeEarth(1000, 500, degrees(90), 1)).toBeCloseTo(Math.sqrt(5), 12)
  })

  it('is the same root of five where the Earth is to take half of a square surface', () => {
    expect(distanceOfTheWholeEarth(500, 500, degrees(90), 0.5)).toBeCloseTo(Math.sqrt(5), 12)
  })

  it.each(STAGES)(
    'has the Earth take the share of the shorter side of %s',
    (_name, width, height) => {
      const distance = distanceOfTheWholeEarth(width, height, degrees(60), 0.8)

      expect(shareSeen(distance, width, height, degrees(60))).toBeCloseTo(0.8, 12)
    },
  )

  it('is the same for a surface held upright and the same surface lying', () => {
    expect(distanceOfTheWholeEarth(390, 745, degrees(60), 0.8)).toBe(
      distanceOfTheWholeEarth(745, 390, degrees(60), 0.8),
    )
  })

  it('goes by the shape of the surface and not by its size', () => {
    expect(distanceOfTheWholeEarth(1400, 1344, degrees(60), 0.8)).toBeCloseTo(
      distanceOfTheWholeEarth(700, 672, degrees(60), 0.8),
      12,
    )
  })

  it('is further away the narrower the surface is', () => {
    const square = distanceOfTheWholeEarth(500, 500, degrees(60), 0.8)
    const desktop = distanceOfTheWholeEarth(700, 672, degrees(60), 0.8)
    const phone = distanceOfTheWholeEarth(390, 745, degrees(60), 0.8)
    const lying = distanceOfTheWholeEarth(844, 312, degrees(60), 0.8)

    expect(desktop).toBeGreaterThan(square)
    expect(phone).toBeGreaterThan(desktop)
    expect(lying).toBeGreaterThan(phone)
  })

  it('is further away the smaller the share is', () => {
    const shares = [1, 0.9, 0.8, 0.5, 0.1]
    const distances = shares.map((share) => distanceOfTheWholeEarth(700, 672, degrees(60), share))

    expect(distances).toEqual(distances.toSorted((one, other) => one - other))
    expect(new Set(distances).size).toBe(shares.length)
  })

  it('is further away the narrower the field of view is', () => {
    expect(distanceOfTheWholeEarth(700, 672, degrees(30), 0.8)).toBeGreaterThan(
      distanceOfTheWholeEarth(700, 672, degrees(60), 0.8),
    )
  })

  it('is outside the Earth, whatever share is asked for', () => {
    for (const share of [0.8, 1, 2, 10, 1000]) {
      expect(distanceOfTheWholeEarth(700, 672, degrees(60), share)).toBeGreaterThan(1)
    }
  })

  it.each([
    ['neither width nor height', 0, 0],
    ['no width', 0, 500],
    ['no height', 500, 0],
  ])('takes a surface that has %s yet for a square one', (_name, width, height) => {
    const distance = distanceOfTheWholeEarth(width, height, degrees(60), 0.8)

    expect(distance).toBe(distanceOfTheWholeEarth(500, 500, degrees(60), 0.8))
    expect(Number.isFinite(distance)).toBe(true)
  })
})
