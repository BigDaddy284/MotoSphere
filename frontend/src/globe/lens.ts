/**
 * The lens of the globe: how wide an angle it sees. This module is
 * arithmetic only and knows nothing of the engine, so that it can be
 * tested where nothing is drawn.
 */

/**
 * The angle the globe sees across the shorter side of its drawing surface,
 * in radians: 36 degrees. On a surface 16 wide and 9 high that is 60
 * degrees across the longer side, the angle the engine takes by itself.
 */
export const ANGLE_ACROSS_THE_SHORTER_SIDE = Math.PI / 5

/**
 * The angle across the longer side of a surface of this width and height,
 * when its shorter side is seen under the angle given.
 *
 * The engine holds one angle, across the longer side of its surface, and
 * leaves it as it is when the surface changes its shape. What is drawn
 * then grows and shrinks with the longer side: when a panel beside the
 * globe closes, the Earth grows, and can outgrow the height of the
 * surface. With the angle of the longer side worked out anew from the
 * shape each time, the shorter side is always seen under the same angle,
 * and what was in view across it stays in view at the same size.
 *
 * A surface that has no size yet is taken for a square one.
 */
export function angleAcrossTheLongerSide(
  width: number,
  height: number,
  acrossTheShorterSide: number,
): number {
  const shorter = Math.min(width, height)
  const longer = Math.max(width, height)
  const longerOverShorter = shorter > 0 ? longer / shorter : 1
  // Half a side, as the tangent of the angle it is seen under: the longer
  // side is as many times the tangent as it is times the length.
  return 2 * Math.atan(Math.tan(acrossTheShorterSide / 2) * longerOverShorter)
}
