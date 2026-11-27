import { inflateSync } from 'node:zlib'
import { chromium } from '@playwright/test'
import { TEST_BROWSER } from './browser.ts'
import { expect, test } from './fixtures'

// A measurement of the planner's, not a test of the application: how the
// browser of the tests draws a 3D picture on this machine, started in several
// ways. Every result is written to the log on a line that begins MEASURE.
const MAIN: Record<string, string[]> = {
  'as the tests start it': [],
  'use-angle=swiftshader': ['--use-angle=swiftshader'],
}
const OTHERS: Record<string, string[]> = {
  'use-angle=swiftshader-webgl': ['--use-angle=swiftshader-webgl'],
  'use-angle=d3d11': ['--use-angle=d3d11'],
  'use-angle=d3d11-warp': ['--use-angle=d3d11-warp'],
  'use-angle=gl': ['--use-angle=gl'],
  'use-angle=vulkan': ['--use-angle=vulkan'],
  'enable-unsafe-swiftshader': ['--enable-unsafe-swiftshader'],
  'disable-gpu': ['--disable-gpu'],
  'ignore-gpu-blocklist': ['--ignore-gpu-blocklist'],
}

/** The first pixel of a picture in the PNG form, as the browser gave it. */
function firstPixel(png: Buffer): number[] {
  let at = 8
  let type = 0
  const data: Buffer[] = []
  while (at < png.length) {
    const length = png.readUInt32BE(at)
    const name = png.toString('latin1', at + 4, at + 8)
    if (name === 'IHDR') {
      type = png.readUInt8(at + 8 + 9)
    }
    if (name === 'IDAT') {
      data.push(png.subarray(at + 8, at + 8 + length))
    }
    at += 12 + length
  }
  const raw = inflateSync(Buffer.concat(data))
  return [...raw.subarray(1, 1 + (type === 6 ? 4 : 3))]
}

const RENDERER = `(() => {
  const gl = document.createElement('canvas').getContext('webgl2')
  if (gl === null) return 'no webgl2'
  const names = gl.getExtension('WEBGL_debug_renderer_info')
  const said = names ? gl.getParameter(names.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
  gl.getExtension('WEBGL_lose_context')?.loseContext()
  return said
})()`

async function measure(
  baseURL: string | undefined,
  extra: string[],
  what: 'engine' | 'engine, pixels read' | 'engine, twenty lives' | 'plain canvas',
): Promise<string> {
  const browser = await chromium.launch({
    ...TEST_BROWSER,
    args: [...(TEST_BROWSER.args ?? []), ...extra],
  })
  const said: string[] = []
  const found: Record<string, unknown> = {}
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
    page.on('console', (message) => {
      if (message.type() === 'warning' || message.type() === 'error') {
        said.push(
          `${message.type()}: ${message
            .text()
            .replace(/0x[0-9a-f]+/, '0x…')
            .slice(0, 170)}`,
        )
      }
    })
    page.on('pageerror', (error) => said.push(`uncaught: ${error.message.slice(0, 200)}`))
    const started = Date.now()
    try {
      if (what === 'plain canvas') {
        await page.goto(baseURL ?? '')
        found['renderer'] = await page.evaluate(RENDERER)
        found['frames'] = await page.evaluate(`(async () => {
          const canvas = document.createElement('canvas')
          canvas.width = 640
          canvas.height = 360
          canvas.style.cssText = 'position:fixed;left:0;top:0;z-index:99'
          document.body.append(canvas)
          const gl = canvas.getContext('webgl2')
          if (gl === null) return 'no webgl2'
          let frames = 0
          await new Promise((done) => {
            const frame = () => {
              gl.clearColor(0.2, 0.6, (frames % 10) / 10, 1)
              gl.clear(gl.COLOR_BUFFER_BIT)
              frames += 1
              if (frames < 60) requestAnimationFrame(frame)
              else done(undefined)
            }
            requestAnimationFrame(frame)
          })
          return frames
        })()`)
        await page.waitForTimeout(500)
        found['seen'] = firstPixel(
          await page.screenshot({ clip: { x: 10, y: 10, width: 1, height: 1 } }),
        )
      } else {
        await page.goto(`${baseURL ?? ''}?spike`)
        await page.waitForFunction(
          `globalThis.spikeWidget !== undefined && globalThis.spikeWidget.scene.globe.tilesLoaded`,
          null,
          { timeout: 30_000 },
        )
        found['shownAfterMs'] = Date.now() - started
        found['renderer'] = await page.evaluate(RENDERER)
        await page.waitForTimeout(2000)
        found['frames'] = await page.evaluate(`globalThis.spikeWidget.scene.frameState.frameNumber`)
        found['canvas'] = await page.evaluate(
          `[globalThis.spikeWidget.canvas.width, globalThis.spikeWidget.canvas.height]`,
        )
        const box = await page.locator('main').boundingBox()
        if (box !== null) {
          const x = Math.round(box.x + box.width / 2)
          const y = Math.round(box.y + box.height / 2)
          found['seenInTheMiddle'] = firstPixel(
            await page.screenshot({ clip: { x, y, width: 1, height: 1 } }),
          )
          found['seenInTheCorner'] = firstPixel(
            await page.screenshot({
              clip: { x: Math.round(box.x) + 8, y: Math.round(box.y) + 8, width: 1, height: 1 },
            }),
          )
        }
        found['saidBefore'] = said.length
        if (what === 'engine, pixels read') {
          found['read'] = await page.evaluate(`(() => {
            const widget = globalThis.spikeWidget
            const gl = widget.scene.context._gl
            widget.scene.render()
            const pixel = new Uint8Array(4)
            gl.readPixels(Math.round(widget.canvas.width / 2), Math.round(widget.canvas.height / 2), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel)
            return [...pixel]
          })()`)
          await page.waitForTimeout(300)
        }
        if (what === 'engine, twenty lives') {
          found['lives'] = await page.evaluate(`(async () => {
            const main = document.querySelector('main')
            globalThis.spikeWidget.destroy()
            let good = 0
            for (let i = 0; i < 20; i++) {
              const widget = globalThis.spikeStart(main)
              const gl = widget.scene.context._gl
              const began = performance.now()
              while (!widget.scene.globe.tilesLoaded && performance.now() - began < 20000) {
                await new Promise((resolve) => setTimeout(resolve, 50))
              }
              if (widget.scene.globe.tilesLoaded) good += 1
              widget.destroy()
              gl.getExtension('WEBGL_lose_context')?.loseContext()
            }
            return [good, main.children.length]
          })()`)
          await page.waitForTimeout(300)
        }
      }
    } catch (error) {
      found['failed'] = String(error).slice(0, 200)
    }
    found['ms'] = Date.now() - started
  } finally {
    await browser.close()
  }
  return `${JSON.stringify(found)} | ${said.length} said | ${JSON.stringify([...new Set(said)])}`
}

for (const round of [1, 2, 3]) {
  for (const [name, extra] of Object.entries(MAIN)) {
    for (const what of ['engine', 'plain canvas'] as const) {
      test(`measure: ${name}, ${what}, round ${round}`, async ({ baseURL }) => {
        test.setTimeout(120_000)
        process.stdout.write(
          `MEASURE ${process.platform} | ${name} | ${what} | ${round} | ${await measure(baseURL, extra, what)}\n` +
            '\n',
        )
        expect(true).toBe(true)
      })
    }
  }
}
for (const [name, extra] of Object.entries(MAIN)) {
  for (const what of ['engine, pixels read', 'engine, twenty lives'] as const) {
    test(`measure: ${name}, ${what}`, async ({ baseURL }) => {
      test.setTimeout(180_000)
      process.stdout.write(
        `MEASURE ${process.platform} | ${name} | ${what} | 1 | ${await measure(baseURL, extra, what)}\n` +
          '\n',
      )
      expect(true).toBe(true)
    })
  }
}
for (const [name, extra] of Object.entries(OTHERS)) {
  for (const what of ['engine', 'plain canvas'] as const) {
    test(`measure: ${name}, ${what}`, async ({ baseURL }) => {
      test.setTimeout(120_000)
      process.stdout.write(
        `MEASURE ${process.platform} | ${name} | ${what} | 1 | ${await measure(baseURL, extra, what)}\n` +
          '\n',
      )
      expect(true).toBe(true)
    })
  }
}
