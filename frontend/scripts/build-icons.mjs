/**
 * Regenerates the icon files in `public/` from the two designs in
 * `docs/design/icon/`. Run it with `npm run icons` after a design changes, and
 * commit the result. It uses the browser that the browser tests use, so that
 * the images are drawn exactly as a browser draws the designs.
 */
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '@playwright/test'

const FRONTEND = path.resolve(import.meta.dirname, '..')
const DESIGNS = path.resolve(FRONTEND, '..', 'docs', 'design', 'icon')
const PUBLIC = path.join(FRONTEND, 'public')

/** Sizes, in pixels, of the images inside `favicon.ico`. Drawn from the small design. */
const ICO_SIZES = [16, 32, 48]
/** Size of `apple-touch-icon.png`. Drawn from the full design. */
const TOUCH_SIZE = 180
/** The lower colour of the tile. Phones show transparent corners as black. */
const TOUCH_BACKGROUND = '#1e1f22'

/** Draws an SVG at `size` pixels square and returns it as a PNG. */
async function drawPng(browser, svg, size, background) {
  const page = await browser.newPage({
    viewport: { width: size, height: size },
    deviceScaleFactor: 1,
    javaScriptEnabled: false,
  })
  try {
    const source = `data:image/svg+xml;base64,${svg.toString('base64')}`
    await page.setContent(
      `<body style="margin:0;background:${background ?? 'transparent'}">` +
        `<img src="${source}" width="${size}" height="${size}" style="display:block">`,
    )
    return await page.screenshot({ omitBackground: background === undefined })
  } finally {
    await page.close()
  }
}

/** Packs square PNG images into one ICO file. */
function packIco(images) {
  const HEADER_BYTES = 6
  const ENTRY_BYTES = 16
  const header = Buffer.alloc(HEADER_BYTES)
  header.writeUInt16LE(1, 2) // 1 = icon
  header.writeUInt16LE(images.length, 4)

  let offset = HEADER_BYTES + ENTRY_BYTES * images.length
  const entries = images.map(({ size, png }) => {
    const entry = Buffer.alloc(ENTRY_BYTES)
    entry.writeUInt8(size, 0) // width
    entry.writeUInt8(size, 1) // height
    entry.writeUInt16LE(1, 4) // colour planes
    entry.writeUInt16LE(32, 6) // bits per pixel
    entry.writeUInt32LE(png.length, 8)
    entry.writeUInt32LE(offset, 12)
    offset += png.length
    return entry
  })
  return Buffer.concat([header, ...entries, ...images.map(({ png }) => png)])
}

const full = await readFile(path.join(DESIGNS, 'motosphere-icon.svg'))
const small = await readFile(path.join(DESIGNS, 'motosphere-icon-small.svg'))

const browser = await chromium.launch()
try {
  const images = []
  for (const size of ICO_SIZES) {
    images.push({ size, png: await drawPng(browser, small, size) })
  }
  await writeFile(path.join(PUBLIC, 'favicon.svg'), small)
  await writeFile(path.join(PUBLIC, 'favicon.ico'), packIco(images))
  await writeFile(
    path.join(PUBLIC, 'apple-touch-icon.png'),
    await drawPng(browser, full, TOUCH_SIZE, TOUCH_BACKGROUND),
  )
} finally {
  await browser.close()
}

process.stdout.write('Wrote favicon.svg, favicon.ico and apple-touch-icon.png to public/\n')
