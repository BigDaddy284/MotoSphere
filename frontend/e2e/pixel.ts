import { crc32, inflateSync } from 'node:zlib'
import type { Page } from '@playwright/test'

/**
 * Reading what the page shows, from outside the page.
 *
 * A test that wants to know whether the globe is drawn has to look at the
 * picture. A page that reads its own 3D picture makes the browser log a
 * warning, and every browser test fails on a warning. So the picture is read
 * from outside: Playwright takes a picture of one pixel of the page as the
 * browser shows it, and the colour is read from that PNG here, with what
 * Node.js brings (FND-060; TESTING.md, "Reading what the page shows").
 */

/** A colour as the page shows it: red, green and blue, each from 0 to 255. */
export type Colour = readonly [red: number, green: number, blue: number]

/** What every PNG begins with. */
const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])

/** How many bytes a pixel has, for the kinds of PNG that are read here. */
const BYTES_OF_A_PIXEL = new Map([
  [2, 3], // red, green, blue
  [6, 4], // red, green, blue, and how opaque
])

/** The highest of the five ways a line of a PNG can be filtered. */
const LAST_FILTER = 4

const DAMAGED = 'The PNG picture is damaged.'

type Chunk = { readonly kind: string; readonly data: Buffer }

/** The chunks a PNG is made of, each checked against its checksum. */
function chunksOf(png: Buffer): Chunk[] {
  if (!png.subarray(0, SIGNATURE.length).equals(SIGNATURE)) {
    throw new Error('This is not a PNG picture.')
  }
  const chunks: Chunk[] = []
  let at = SIGNATURE.length
  while (at < png.length) {
    // A chunk is its length, its kind, its data and its checksum.
    if (at + 12 > png.length) {
      throw new Error(DAMAGED)
    }
    const end = at + 8 + png.readUInt32BE(at)
    if (end + 4 > png.length) {
      throw new Error(DAMAGED)
    }
    const kindAndData = png.subarray(at + 4, end)
    if (crc32(kindAndData) !== png.readUInt32BE(end)) {
      throw new Error(DAMAGED)
    }
    chunks.push({ kind: kindAndData.toString('latin1', 0, 4), data: kindAndData.subarray(4) })
    at = end + 4
  }
  return chunks
}

/**
 * The colour of a PNG picture of one pixel.
 *
 * Read are the two kinds a browser makes: eight bits for each of red, green
 * and blue, with or without a fourth for how opaque the pixel is, not
 * interlaced. Any other picture is refused with a sentence, and so is a
 * pixel that is not opaque: its colour is not what a person sees.
 */
export function colourOfOnePixel(png: Buffer): Colour {
  const chunks = chunksOf(png)
  // A PNG begins with its header and ends with its end.
  const header = chunks[0]
  if (
    header === undefined ||
    header.kind !== 'IHDR' ||
    header.data.length !== 13 ||
    chunks.at(-1)?.kind !== 'IEND'
  ) {
    throw new Error(DAMAGED)
  }
  const width = header.data.readUInt32BE(0)
  const height = header.data.readUInt32BE(4)
  if (width !== 1 || height !== 1) {
    throw new Error(`The PNG picture is ${width} by ${height} pixels, not one pixel.`)
  }
  const depth = header.data.readUInt8(8)
  const kind = header.data.readUInt8(9)
  const interlaced = header.data.readUInt8(12)
  const bytes = BYTES_OF_A_PIXEL.get(kind)
  if (depth !== 8 || bytes === undefined || interlaced !== 0) {
    throw new Error(
      `The PNG picture is of a kind that is not read here (bit depth ${depth}, colour type ${kind}, interlace ${interlaced}). Read are bit depth 8, colour type 2 or 6, interlace 0.`,
    )
  }
  const packed = Buffer.concat(
    chunks.filter((chunk) => chunk.kind === 'IDAT').map((chunk) => chunk.data),
  )
  let line: Buffer
  try {
    line = inflateSync(packed)
  } catch (error) {
    throw new Error(DAMAGED, { cause: error })
  }
  // A line is the way it is filtered and then its pixels. Every filter
  // leaves the first pixel of the first line as it is, so the one pixel of
  // this picture is read as it stands.
  if (line.length !== 1 + bytes || line.readUInt8(0) > LAST_FILTER) {
    throw new Error(DAMAGED)
  }
  if (bytes === 4 && line.readUInt8(4) !== 255) {
    throw new Error(
      `The pixel of the PNG picture is not opaque (${line.readUInt8(4)} of 255), so its colour is not what is seen.`,
    )
  }
  return [line.readUInt8(1), line.readUInt8(2), line.readUInt8(3)]
}

/**
 * The colour of the point of the page that is `x` pixels from its left edge
 * and `y` from its top, as the browser shows it.
 */
export async function colourAt(page: Page, x: number, y: number): Promise<Colour> {
  // The page is asked how large it is: Playwright knows the size only of a
  // page it gave one.
  const [width, height] = await page.evaluate(
    () => [window.innerWidth, window.innerHeight] as const,
  )
  const inside =
    Number.isInteger(x) && Number.isInteger(y) && x >= 0 && y >= 0 && x < width && y < height
  if (!inside) {
    throw new Error(
      `(${x}, ${y}) is not a point of the page, which is ${width} by ${height} pixels.`,
    )
  }
  // One pixel of the picture for one pixel of the page, whatever the screen.
  const png = await page.screenshot({ clip: { x, y, width: 1, height: 1 }, scale: 'css' })
  return colourOfOnePixel(png)
}
