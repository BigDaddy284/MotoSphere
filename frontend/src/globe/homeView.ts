/**
 * The view the globe opens with: the whole Earth, seen from above one place.
 * This module is arithmetic only and knows nothing of the engine, so that
 * it can be tested where nothing is drawn.
 */

/**
 * The place the globe is above when it opens, in degrees: the middle of the
 * North Atlantic. From there Europe and North Africa are in view on one
 * side and the Americas on the other.
 */
export const HOME = { longitude: -40, latitude: 30 } as const

/**
 * The share of the shorter side of the drawing surface that the Earth takes
 * when the globe opens. The rest is the space around it.
 */
export const SHARE_OF_THE_SHORTER_SIDE = 0.8

/**
 * How far from the middle of the Earth it has to be seen from, in radii of
 * the Earth, to take the share of the shorter side of a surface of this
 * width and height.
 *
 * The engine holds its field of view, an angle, across the longer side of
 * the surface. Seen from one fixed distance the Earth would take the same
 * share of the longer side whatever the shape of the surface, and on a
 * surface much longer than it is wide, a phone held upright, it would be
 * cut off at both sides.
 *
 * A surface that has no size yet is taken for a square one.
 */
export function distanceOfTheWholeEarth(
  width: number,
  height: number,
  fieldOfView: number,
  share: number,
): number {
  const shorter = Math.min(width, height)
  const longer = Math.max(width, height)
  const shorterOverLonger = shorter > 0 ? shorter / longer : 1
  // Half of the shorter side, as the tangent of the angle it is seen under.
  const halfTheShorterSide = Math.tan(fieldOfView / 2) * shorterOverLonger
  // The edge of a ball is seen under the angle whose sine is its radius
  // over the distance to its middle.
  return 1 / Math.sin(Math.atan(share * halfTheShorterSide))
}
