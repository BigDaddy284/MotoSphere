// WCAG 2 contrast maths, used only by tests.
// Definitions: https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio

const HEX_COLOUR = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i

function channelLuminance(value: number): number {
  const c = value / 255
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

/** Relative luminance of a six-digit hex colour such as `#0b0d10`. */
export function relativeLuminance(colour: string): number {
  const match = HEX_COLOUR.exec(colour)
  if (match === null) {
    throw new Error(`Not a six-digit hex colour: "${colour}"`)
  }
  const [red, green, blue] = match
    .slice(1)
    .map((hex) => channelLuminance(Number.parseInt(hex, 16))) as [number, number, number]
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

/** Contrast ratio between two six-digit hex colours, from 1 to 21. */
export function contrastRatio(first: string, second: string): number {
  const a = relativeLuminance(first)
  const b = relativeLuminance(second)
  const lighter = Math.max(a, b)
  const darker = Math.min(a, b)
  return (lighter + 0.05) / (darker + 0.05)
}
