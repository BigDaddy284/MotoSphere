import { Cartesian3, Cartographic, Ellipsoid, Math as EngineMath } from '@cesium/core'
import { GeographicTilingScheme, Globe } from '@cesium/engine'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// The engine of the globe is used here as it is installed, with nothing in
// its place. It keeps its arithmetic (positions, angles, the shape of the
// Earth) in a package of its own, `@cesium/core`, and asks that those names
// be taken from there and no longer from the engine.
//
// The numbers are those of the reference ellipsoid WGS84, by which positions
// on the Earth are given: 6378137 m from the centre to the equator and
// 6356752.314245179 m to a pole.
const TO_THE_EQUATOR = 6378137
const TO_A_POLE = 6356752.314245179

describe('the engine of the globe, as installed', () => {
  // The engine writes a warning the first time a name is used that it wants
  // taken from elsewhere. A test that brings one about fails.
  beforeEach(() => {
    vi.spyOn(console, 'warn').mockImplementation((...said: unknown[]) => {
      throw new Error(`The engine warned: ${said.join(' ')}`)
    })
  })

  it('goes by the reference ellipsoid WGS84', () => {
    expect(Ellipsoid.default).toBe(Ellipsoid.WGS84)
    expect(Ellipsoid.WGS84.radii.x).toBe(TO_THE_EQUATOR)
    expect(Ellipsoid.WGS84.radii.y).toBe(TO_THE_EQUATOR)
    expect(Ellipsoid.WGS84.radii.z).toBe(TO_A_POLE)
  })

  it.each([
    {
      where: 'where the equator meets the prime meridian',
      at: [0, 0],
      x: TO_THE_EQUATOR,
      y: 0,
      z: 0,
    },
    {
      where: 'on the equator, a quarter of the way round to the east',
      at: [90, 0],
      x: 0,
      y: TO_THE_EQUATOR,
      z: 0,
    },
    {
      where: 'on the equator, a quarter of the way round to the west',
      at: [-90, 0],
      x: 0,
      y: -TO_THE_EQUATOR,
      z: 0,
    },
    { where: 'on the equator, half the way round', at: [180, 0], x: -TO_THE_EQUATOR, y: 0, z: 0 },
    { where: 'at the north pole', at: [0, 90], x: 0, y: 0, z: TO_A_POLE },
    { where: 'at the south pole', at: [0, -90], x: 0, y: 0, z: -TO_A_POLE },
  ] as const)('puts a place $where', ({ at: [longitude, latitude], x, y, z }) => {
    const place = Cartesian3.fromDegrees(longitude, latitude)

    // To a thousandth of a millimetre.
    expect(place.x).toBeCloseTo(x, 6)
    expect(place.y).toBeCloseTo(y, 6)
    expect(place.z).toBeCloseTo(z, 6)
  })

  it('takes longitude first and latitude second', () => {
    const north = Cartesian3.fromDegrees(0, 45)
    const east = Cartesian3.fromDegrees(45, 0)

    expect(north.z).toBeGreaterThan(4_000_000)
    expect(north.y).toBeCloseTo(0, 6)
    expect(east.y).toBeGreaterThan(4_000_000)
    expect(east.z).toBeCloseTo(0, 6)
  })

  it('counts a height in metres above the ellipsoid', () => {
    expect(Cartesian3.fromDegrees(0, 0, 1000).x).toBeCloseTo(TO_THE_EQUATOR + 1000, 6)
    expect(Cartesian3.fromDegrees(0, 90, 1000).z).toBeCloseTo(TO_A_POLE + 1000, 6)
  })

  it('gives back the degrees and the height a place was made from', () => {
    const place = Cartesian3.fromDegrees(-122.5, 37.75, 250)

    const read = Cartographic.fromCartesian(place)

    expect(EngineMath.toDegrees(read.longitude)).toBeCloseTo(-122.5, 9)
    expect(EngineMath.toDegrees(read.latitude)).toBeCloseTo(37.75, 9)
    expect(read.height).toBeCloseTo(250, 6)
  })

  it('makes its globe on the same ellipsoid, the very one the application gets', () => {
    // Were there two copies of the arithmetic, the engine's ellipsoid would
    // be another object than the one the application is given.
    expect(new Globe().ellipsoid).toBe(Ellipsoid.WGS84)
    expect(new GeographicTilingScheme().ellipsoid).toBe(Ellipsoid.WGS84)
  })
})
