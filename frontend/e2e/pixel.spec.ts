import { crc32, deflateSync } from 'node:zlib'
import type { Page } from '@playwright/test'
import { colourAt, colourOfOnePixel } from './pixel.ts'
import { expect, test } from './fixtures'

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
const DAMAGED = 'The PNG picture is damaged.'

/** One chunk of a PNG: its length, its kind, its data and its checksum. */
function chunk(kind: string, data: Buffer): Buffer {
  const kindAndData = Buffer.concat([Buffer.from(kind, 'latin1'), data])
  const length = Buffer.alloc(4)
  length.writeUInt32BE(data.length)
  const checksum = Buffer.alloc(4)
  checksum.writeUInt32BE(crc32(kindAndData))
  return Buffer.concat([length, kindAndData, checksum])
}

type Header = {
  width?: number
  height?: number
  depth?: number
  kind?: number
  interlace?: number
}

/**
 * The header of a PNG, of one pixel of red, green and blue unless said
 * otherwise, in a chunk of the kind a header has unless said otherwise.
 */
function header(
  { width = 1, height = 1, depth = 8, kind = 2, interlace = 0 }: Header = {},
  chunkKind = 'IHDR',
): Buffer {
  const data = Buffer.alloc(13)
  data.writeUInt32BE(width, 0)
  data.writeUInt32BE(height, 4)
  data.writeUInt8(depth, 8)
  data.writeUInt8(kind, 9)
  data.writeUInt8(interlace, 12)
  return chunk(chunkKind, data)
}

/** The data of a PNG whose one line is these bytes: its filter, then its pixels. */
function lineOf(...line: number[]): Buffer {
  return chunk('IDAT', deflateSync(Buffer.from(line)))
}

const END = chunk('IEND', Buffer.alloc(0))

/** A PNG made of these chunks. */
function png(...chunks: Buffer[]): Buffer {
  return Buffer.concat([SIGNATURE, ...chunks])
}

/** A picture of one pixel as the browser of the tests made it of a page (FND-060). */
const FROM_THE_BROWSER = Buffer.from(
  '89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de' +
    '0000000c49444154789c62e13a2107000000ffff9d4c6ca9' +
    '0000000649444154030001e000f56aebda38' +
    '0000000049454e44ae426082',
  'hex',
)

test.describe('the colour of a PNG picture of one pixel', () => {
  test('is read from red, green and blue', () => {
    expect(colourOfOnePixel(png(header(), lineOf(0, 10, 200, 30), END))).toEqual([10, 200, 30])
    expect(colourOfOnePixel(png(header(), lineOf(0, 0, 0, 0), END))).toEqual([0, 0, 0])
    expect(colourOfOnePixel(png(header(), lineOf(0, 255, 255, 255), END))).toEqual([255, 255, 255])
  })

  test('is read from red, green, blue and a fourth that says the pixel is opaque', () => {
    expect(colourOfOnePixel(png(header({ kind: 6 }), lineOf(0, 1, 2, 3, 255), END))).toEqual([
      1, 2, 3,
    ])
  })

  test('is the same however the line is filtered', () => {
    for (const filter of [0, 1, 2, 3, 4]) {
      expect(colourOfOnePixel(png(header(), lineOf(filter, 10, 200, 30), END))).toEqual([
        10, 200, 30,
      ])
      expect(
        colourOfOnePixel(png(header({ kind: 6 }), lineOf(filter, 10, 200, 30, 255), END)),
      ).toEqual([10, 200, 30])
    }
  })

  test('is read from data in several pieces, with other chunks between', () => {
    const data = deflateSync(Buffer.from([0, 10, 200, 30]))
    const made = png(
      header(),
      chunk('tEXt', Buffer.from('Software\0a test', 'latin1')),
      chunk('IDAT', data.subarray(0, 3)),
      chunk('IDAT', data.subarray(3, 4)),
      chunk('IDAT', data.subarray(4)),
      END,
    )
    expect(colourOfOnePixel(made)).toEqual([10, 200, 30])
  })

  test('is read from a picture as the browser made it', () => {
    expect(colourOfOnePixel(FROM_THE_BROWSER)).toEqual([10, 200, 30])
  })

  test('is not read from what is no PNG', () => {
    for (const other of [
      Buffer.alloc(0),
      Buffer.from('not a picture'),
      Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46]),
      SIGNATURE.subarray(0, 7),
    ]) {
      expect(() => colourOfOnePixel(other)).toThrow('This is not a PNG picture.')
    }
  })

  test('is not read from a picture of more or fewer pixels than one', () => {
    const sizes: [number, number][] = [
      [2, 1],
      [1, 2],
      [0, 0],
      [1280, 720],
    ]
    for (const [width, height] of sizes) {
      expect(() =>
        colourOfOnePixel(png(header({ width, height }), lineOf(0, 10, 200, 30), END)),
      ).toThrow(`The PNG picture is ${width} by ${height} pixels, not one pixel.`)
    }
  })

  test('is not read from a picture of another kind', () => {
    const kinds: [Header, string][] = [
      [{ depth: 16 }, 'bit depth 16, colour type 2, interlace 0'],
      [{ kind: 0 }, 'bit depth 8, colour type 0, interlace 0'],
      [{ kind: 3 }, 'bit depth 8, colour type 3, interlace 0'],
      [{ kind: 4 }, 'bit depth 8, colour type 4, interlace 0'],
      [{ depth: 16, kind: 6 }, 'bit depth 16, colour type 6, interlace 0'],
      [{ interlace: 1 }, 'bit depth 8, colour type 2, interlace 1'],
    ]
    for (const [kind, said] of kinds) {
      expect(() => colourOfOnePixel(png(header(kind), lineOf(0, 10, 200, 30), END))).toThrow(
        `The PNG picture is of a kind that is not read here (${said}). Read are bit depth 8, colour type 2 or 6, interlace 0.`,
      )
    }
  })

  test('is not read from a pixel that is not opaque', () => {
    for (const opaque of [254, 128, 0]) {
      expect(() =>
        colourOfOnePixel(png(header({ kind: 6 }), lineOf(0, 10, 200, 30, opaque), END)),
      ).toThrow(
        `The pixel of the PNG picture is not opaque (${opaque} of 255), so its colour is not what is seen.`,
      )
    }
  })

  test('is not read from a picture whose parts are not as a PNG has them', () => {
    const line = lineOf(0, 10, 200, 30)
    const damaged: Buffer[] = [
      // No header, a header that is not the first chunk, a header of another length.
      png(line, END),
      png(line, header(), END),
      // A first chunk that reads as a header and is none, before the header.
      png(header({}, 'tEXt'), header(), line, END),
      png(header({}, 'tEXt'), line, END),
      png(chunk('IHDR', Buffer.alloc(12)), line, END),
      // No end, and an end that is not the last chunk.
      png(header(), line),
      png(header(), END, line),
      // No data, data that is not packed, a line that is too short or too long.
      png(header(), END),
      png(header(), chunk('IDAT', Buffer.from([0, 10, 200, 30])), END),
      png(header(), lineOf(0, 10, 200), END),
      png(header(), lineOf(0, 10, 200, 30, 255), END),
      png(header({ kind: 6 }), lineOf(0, 10, 200, 30), END),
      // A filter there is none of.
      png(header(), lineOf(5, 10, 200, 30), END),
    ]
    for (const made of damaged) {
      expect(() => colourOfOnePixel(made)).toThrow(DAMAGED)
    }
  })

  test('says what the unpacking said of data that cannot be unpacked', () => {
    let refusal: unknown = null
    try {
      colourOfOnePixel(png(header(), chunk('IDAT', Buffer.from([0, 10, 200, 30])), END))
    } catch (error) {
      refusal = error
    }
    expect(refusal).toMatchObject({ message: DAMAGED, cause: { code: 'Z_DATA_ERROR' } })
  })

  test('is not read from a picture that is cut short anywhere', () => {
    for (const whole of [png(header(), lineOf(0, 10, 200, 30), END), FROM_THE_BROWSER]) {
      for (let length = 0; length < whole.length; length += 1) {
        expect(() => colourOfOnePixel(whole.subarray(0, length))).toThrow(
          length < SIGNATURE.length ? 'This is not a PNG picture.' : DAMAGED,
        )
      }
    }
  })

  test('is not read from a picture in which any one byte is another', () => {
    for (const whole of [png(header(), lineOf(0, 10, 200, 30), END), FROM_THE_BROWSER]) {
      for (let at = 0; at < whole.length; at += 1) {
        const changed = Buffer.from(whole)
        changed.writeUInt8(whole.readUInt8(at) ^ 0xff, at)
        expect(() => colourOfOnePixel(changed)).toThrow(
          at < SIGNATURE.length ? 'This is not a PNG picture.' : DAMAGED,
        )
      }
    }
  })
})

/**
 * Covers the page with a flat picture: four quarters of four colours, and a
 * colour of its own for the one pixel in each corner.
 */
const SHOW_COLOURS = `(() => {
  const canvas = document.createElement('canvas')
  canvas.width = innerWidth
  canvas.height = innerHeight
  canvas.style.cssText = 'position: fixed; left: 0; top: 0; z-index: 2147483647'
  document.body.append(canvas)
  const pen = canvas.getContext('2d')
  const [w, h] = [canvas.width, canvas.height]
  const fill = (colour, x, y, width, height) => {
    pen.fillStyle = colour
    pen.fillRect(x, y, width, height)
  }
  fill('rgb(200, 30, 40)', 0, 0, w / 2, h / 2)
  fill('rgb(30, 160, 60)', w / 2, 0, w / 2, h / 2)
  fill('rgb(20, 60, 220)', 0, h / 2, w / 2, h / 2)
  fill('rgb(240, 220, 10)', w / 2, h / 2, w / 2, h / 2)
  fill('rgb(1, 2, 3)', 0, 0, 1, 1)
  fill('rgb(4, 5, 6)', w - 1, 0, 1, 1)
  fill('rgb(7, 8, 9)', 0, h - 1, 1, 1)
  fill('rgb(255, 255, 255)', w - 1, h - 1, 1, 1)
})()`

/** Covers the page with one colour, or gives the cover that is there another. */
async function cover(page: Page, colour: string): Promise<void> {
  await page.evaluate((background) => {
    const there = document.querySelector<HTMLElement>('#cover')
    const over = there ?? document.createElement('div')
    over.id = 'cover'
    over.style.cssText = `position: fixed; inset: 0; z-index: 2147483647; background: ${background}`
    document.body.append(over)
  }, colour)
}

test.describe('the colour of a point of the page', () => {
  test('is the colour the page shows there, at its corners and edges too', async ({ page }) => {
    await page.goto('./')
    await page.evaluate(SHOW_COLOURS)
    expect(page.viewportSize()).toEqual({ width: 1280, height: 720 })
    const points: [number, number, [number, number, number]][] = [
      // The one pixel in each corner, and its neighbours.
      [0, 0, [1, 2, 3]],
      [1, 0, [200, 30, 40]],
      [0, 1, [200, 30, 40]],
      [1279, 0, [4, 5, 6]],
      [1278, 0, [30, 160, 60]],
      [0, 719, [7, 8, 9]],
      [0, 718, [20, 60, 220]],
      [1279, 719, [255, 255, 255]],
      [1278, 719, [240, 220, 10]],
      [1279, 718, [240, 220, 10]],
      // Where the four quarters meet.
      [639, 359, [200, 30, 40]],
      [640, 359, [30, 160, 60]],
      [639, 360, [20, 60, 220]],
      [640, 360, [240, 220, 10]],
      // The middle of each edge.
      [300, 0, [200, 30, 40]],
      [1279, 500, [240, 220, 10]],
      [900, 719, [240, 220, 10]],
      [0, 500, [20, 60, 220]],
    ]
    for (const [x, y, colour] of points) {
      expect(await colourAt(page, x, y), `at (${x}, ${y})`).toEqual(colour)
    }
  })

  test('is what the page shows when it is asked for', async ({ page }) => {
    await page.goto('./')
    await cover(page, 'rgb(250, 128, 114)')
    expect(await colourAt(page, 640, 360)).toEqual([250, 128, 114])
    await cover(page, 'rgb(0, 0, 0)')
    expect(await colourAt(page, 640, 360)).toEqual([0, 0, 0])
    // What lies on top is what is seen: here a fifth of white over what was
    // under the black, the dark surface of the page.
    await cover(page, 'rgba(255, 255, 255, 0.2)')
    const seen = await colourAt(page, 640, 360)
    expect(seen).not.toEqual([0, 0, 0])
    expect(seen).not.toEqual([255, 255, 255])
  })

  test('is not given for a point that is not a point of the page', async ({ page }) => {
    await page.goto('./')
    const points: [number, number][] = [
      [-1, 0],
      [0, -1],
      [1280, 0],
      [0, 720],
      [1280, 720],
      [0.5, 0],
      [0, 10.25],
      [Number.NaN, 0],
      [0, Number.POSITIVE_INFINITY],
    ]
    for (const [x, y] of points) {
      await expect(colourAt(page, x, y)).rejects.toThrow(
        `(${x}, ${y}) is not a point of the page, which is 1280 by 720 pixels.`,
      )
    }
  })

  test('is one pixel for one pixel of the page on a screen with more', async ({ browser }) => {
    // The page is smaller than the screen it is on, and twice as sharp.
    const context = await browser.newContext({
      screen: { width: 1920, height: 1080 },
      viewport: { width: 200, height: 100 },
      deviceScaleFactor: 2,
    })
    try {
      const sharp = await context.newPage()
      await sharp.setContent('<body style="margin: 0; background: rgb(10, 200, 30)"></body>')
      expect(await sharp.evaluate('[devicePixelRatio, screen.width, screen.height]')).toEqual([
        2, 1920, 1080,
      ])
      expect(await colourAt(sharp, 0, 0)).toEqual([10, 200, 30])
      expect(await colourAt(sharp, 199, 99)).toEqual([10, 200, 30])
      await expect(colourAt(sharp, 200, 99)).rejects.toThrow(
        '(200, 99) is not a point of the page, which is 200 by 100 pixels.',
      )
    } finally {
      await context.close()
    }
  })
})
