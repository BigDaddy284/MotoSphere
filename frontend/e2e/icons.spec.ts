import { readFile } from 'node:fs/promises'
import path from 'node:path'
import type { APIRequestContext, Page } from '@playwright/test'
import { SITE_PATH } from '../site.ts'
import { expect, test } from './fixtures'

const DESIGNS = path.resolve(import.meta.dirname, '..', '..', 'docs', 'design', 'icon')
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])

/** The colours of the Sky Classic tile and its sky-blue gradient. */
const TILE_TOP = '#34363b'
const TILE_BOTTOM = '#1e1f22'
const TILE_BORDER = '#45484f'
const SKY_FROM = '#3d8bff'
const SKY_TO = '#8cc4ff'

type Rgba = [number, number, number, number]

async function served(request: APIRequestContext, url: string): Promise<Buffer> {
  const response = await request.get(url)
  expect(response.status(), url).toBe(200)
  return response.body()
}

function pngSize(png: Buffer): { width: number; height: number } {
  expect(png.subarray(0, 8).equals(PNG_SIGNATURE), 'starts as a PNG file').toBe(true)
  expect(png.toString('latin1', 12, 16)).toBe('IHDR')
  return { width: png.readUInt32BE(16), height: png.readUInt32BE(20) }
}

/** The PNG images inside an ICO file, in the order of its directory. */
function icoImages(ico: Buffer): { width: number; height: number; png: Buffer }[] {
  expect(ico.readUInt16LE(0), 'reserved field').toBe(0)
  expect(ico.readUInt16LE(2), 'file type: icon').toBe(1)
  const count = ico.readUInt16LE(4)
  const images = []
  for (let index = 0; index < count; index += 1) {
    const entry = 6 + 16 * index
    const length = ico.readUInt32LE(entry + 8)
    const offset = ico.readUInt32LE(entry + 12)
    expect(ico.readUInt16LE(entry + 6), 'bits per pixel').toBe(32)
    expect(offset + length, 'image lies inside the file').toBeLessThanOrEqual(ico.length)
    images.push({
      width: ico.readUInt8(entry),
      height: ico.readUInt8(entry + 1),
      png: ico.subarray(offset, offset + length),
    })
  }
  return images
}

/** Lets the browser decode a PNG and returns the colour of each point asked for. */
async function pixels(page: Page, png: Buffer, points: [number, number][]): Promise<Rgba[]> {
  return page.evaluate(
    async ({ base64, wanted }) => {
      const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0))
      const bitmap = await createImageBitmap(new Blob([bytes], { type: 'image/png' }))
      const canvas = new OffscreenCanvas(bitmap.width, bitmap.height)
      const context = canvas.getContext('2d')
      if (context === null) {
        throw new Error('no drawing context')
      }
      context.drawImage(bitmap, 0, 0)
      // One read of the whole image; the browser warns about repeated small reads.
      const { data } = context.getImageData(0, 0, bitmap.width, bitmap.height)
      return wanted.map(([x, y]) => {
        const start = 4 * (y * bitmap.width + x)
        const [red = 0, green = 0, blue = 0, alpha = 0] = data.slice(start, start + 4)
        return [red, green, blue, alpha] satisfies [number, number, number, number]
      })
    },
    { base64: png.toString('base64'), wanted: points },
  )
}

/** Every colour written in a design file, each once, in order. */
async function coloursIn(name: string): Promise<string[]> {
  const svg = await readFile(path.join(DESIGNS, name), 'utf8')
  return [...new Set(svg.match(/#[0-9a-f]{3,8}\b/gi))].toSorted()
}

function expectSkyBlue([red, green, blue, alpha]: Rgba, where: string) {
  expect(alpha, `${where}: opaque`).toBe(255)
  expect(blue, `${where}: strongly blue`).toBeGreaterThan(200)
  expect(blue - red, `${where}: more blue than red`).toBeGreaterThan(80)
  expect(green, `${where}: green between red and blue`).toBeGreaterThan(red)
}

function expectTile([red, green, blue, alpha]: Rgba, where: string) {
  expect(alpha, `${where}: opaque`).toBe(255)
  for (const channel of [red, green, blue]) {
    expect(channel, `${where}: dark`).toBeGreaterThanOrEqual(0x1e)
    expect(channel, `${where}: dark`).toBeLessThanOrEqual(0x3b)
  }
}

test.describe('application icon', () => {
  test('the page links the three icon files', async ({ page }) => {
    await page.goto('./')
    const links = page.locator('head > link[rel~="icon"], head > link[rel="apple-touch-icon"]')
    await expect(links).toHaveCount(3)
    await expect(page.locator('link[rel="icon"][sizes="32x32"]')).toHaveAttribute(
      'href',
      `${SITE_PATH}favicon.ico`,
    )
    await expect(page.locator('link[rel="icon"][type="image/svg+xml"]')).toHaveAttribute(
      'href',
      `${SITE_PATH}favicon.svg`,
    )
    await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveAttribute(
      'href',
      `${SITE_PATH}apple-touch-icon.png`,
    )
  })

  for (const [url, type] of [
    ['favicon.svg', /^image\/svg\+xml/],
    ['favicon.ico', /^image\/(x-icon|vnd\.microsoft\.icon)$/],
    ['apple-touch-icon.png', /^image\/png$/],
  ] as const) {
    test(`${url} is served as an image`, async ({ request }) => {
      const response = await request.get(url)
      expect(response.status()).toBe(200)
      expect(response.headers()['content-type']).toMatch(type)
    })
  }

  test('the vector icon is the small design, byte for byte', async ({ request }) => {
    const design = await readFile(path.join(DESIGNS, 'motosphere-icon-small.svg'))
    expect((await served(request, 'favicon.svg')).equals(design)).toBe(true)
  })

  for (const name of ['motosphere-icon.svg', 'motosphere-icon-small.svg']) {
    test(`${name} holds nothing that runs or loads`, async () => {
      const svg = await readFile(path.join(DESIGNS, name), 'utf8')
      expect(
        svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"'),
      ).toBe(true)
      expect(svg).not.toMatch(/<\s*(script|foreignObject|image|use|a|style|iframe)[\s>/]/i)
      expect(svg).not.toMatch(/\son[a-z]+\s*=/i)
      expect(svg).not.toMatch(/href\s*=/i)
      expect(svg).not.toMatch(/javascript:|data:|@import/i)
      // Addresses appear only as the names of XML vocabularies, which are never fetched.
      const addresses = [...svg.matchAll(/(\S*)="(https?:[^"]*)"/g)].map((match) => match[1])
      expect(addresses.every((attribute) => attribute?.startsWith('xmlns'))).toBe(true)
      expect(svg.match(/https?:/g)?.length).toBe(addresses.length)
      // url(...) may only point at something inside the same file.
      const targets = [...svg.matchAll(/url\(([^)]*)\)/g)].map((match) => match[1])
      expect(targets.every((target) => target?.startsWith('#'))).toBe(true)
    })
  }

  test('both designs use the Sky Classic colours', async () => {
    expect(await coloursIn('motosphere-icon-small.svg')).toEqual(
      [TILE_BOTTOM, TILE_TOP, SKY_FROM, SKY_TO].toSorted(),
    )
    // The full design also has the tile's border, and black and white inside a mask.
    expect(await coloursIn('motosphere-icon.svg')).toEqual(
      ['#000', '#fff', TILE_BOTTOM, TILE_TOP, TILE_BORDER, SKY_FROM, SKY_TO].toSorted(),
    )
  })

  test('the fallback icon holds 16, 32 and 48 pixel images', async ({ request }) => {
    const images = icoImages(await served(request, 'favicon.ico'))

    expect(images.map(({ width }) => width)).toEqual([16, 32, 48])
    for (const { width, height, png } of images) {
      expect(height).toBe(width)
      expect(pngSize(png)).toEqual({ width, height })
    }
  })

  for (const [index, size] of [16, 32, 48].entries()) {
    test(`the ${size} pixel image shows the globe on its tile`, async ({ page, request }) => {
      const image = icoImages(await served(request, 'favicon.ico'))[index]
      if (image === undefined) {
        throw new Error(`no image ${index} in the icon file`)
      }
      await page.goto('./')
      const middle = size / 2
      const [corner, rim, inside, outside] = await pixels(page, image.png, [
        [0, 0],
        [Math.floor(size * (0.5 + 400 / 1024)), middle],
        [Math.floor(size * 0.4), Math.floor(size * 0.33)],
        [Math.floor(size * 0.12), Math.floor(size * 0.12)],
      ])
      if (!corner || !rim || !inside || !outside) {
        throw new Error('a pixel is missing')
      }

      expect(corner[3], 'the corner outside the rounded tile is see-through').toBeLessThan(64)
      expectSkyBlue(rim, 'the rim of the globe')
      expectTile(inside, 'between the lines of the globe')
      expectTile(outside, 'the tile beside the globe')
    })
  }

  test('the touch icon is 180 pixels square, with the globe and no see-through corners', async ({
    page,
    request,
  }) => {
    const png = await served(request, 'apple-touch-icon.png')
    expect(pngSize(png)).toEqual({ width: 180, height: 180 })

    await page.goto('./')
    // In the full design the rim of the globe is 330 units from the centre of
    // a 1024 unit square, and 400 units from the centre there is only the tile.
    const [topLeft, bottomRight, rim, tile] = await pixels(page, png, [
      [0, 0],
      [179, 179],
      [Math.round(90 + (330 / 1024) * 180), 90],
      [Math.round(90 + (400 / 1024) * 180), 90],
    ])
    if (!topLeft || !bottomRight || !rim || !tile) {
      throw new Error('a pixel is missing')
    }

    expect(topLeft).toEqual([0x1e, 0x1f, 0x22, 255])
    expect(bottomRight).toEqual([0x1e, 0x1f, 0x22, 255])
    expectSkyBlue(rim, 'the rim of the globe')
    expectTile(tile, 'the tile beside the globe')
  })
})
