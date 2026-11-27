import { inflateSync } from 'node:zlib'
import { chromium } from '@playwright/test'
import { TEST_BROWSER } from './browser.ts'
import { expect, test } from './fixtures'

// A measurement of the planner's, not a test of the application: what a
// picture taken of the page shows of the globe, at several moments, with the
// browser of the tests started in two ways and the engine drawing in two.
// Every result is written to the log on a line that begins MEASURE.
const BROWSERS: Record<string, string[]> = {
  'as the tests start it': [],
  'use-angle=swiftshader': ['--use-angle=swiftshader'],
}
const DRAWING: Record<string, string> = {
  'every frame': '',
  'on request': '&onrequest',
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

const STATE = `(() => {
  const widget = globalThis.spikeWidget
  const gl = widget.scene.context._gl
  const position = widget.camera.positionCartographic
  return {
    lost: gl.isContextLost(),
    canvas: [widget.canvas.width, widget.canvas.height, widget.canvas.clientWidth, widget.canvas.clientHeight],
    frames: widget.scene.frameState.frameNumber,
    loaded: widget.scene.globe.tilesLoaded,
    camera: [Math.round((position.longitude * 180) / Math.PI), Math.round((position.latitude * 180) / Math.PI), Math.round(position.height / 1000)],
    hidden: document.hidden,
  }
})()`

const DRAWN = `(() => {
  const widget = globalThis.spikeWidget
  const gl = widget.scene.context._gl
  const names = gl.getExtension('WEBGL_debug_renderer_info')
  widget.scene.render()
  const pixel = new Uint8Array(4)
  gl.readPixels(Math.round(widget.canvas.width / 2), Math.round(widget.canvas.height / 2), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel)
  return { drawn: [...pixel], renderer: names ? gl.getParameter(names.UNMASKED_RENDERER_WEBGL) : '' }
})()`

for (const round of [1, 2, 3]) {
  for (const [browserName, extra] of Object.entries(BROWSERS)) {
    for (const [drawing, how] of Object.entries(DRAWING)) {
      test(`measure: ${browserName}, ${drawing}, round ${round}`, async ({ baseURL }) => {
        test.setTimeout(180_000)
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
            await page.goto(`${baseURL ?? ''}?spike${how}`)
            await page.waitForFunction(
              `globalThis.spikeWidget !== undefined && globalThis.spikeWidget.scene.globe.tilesLoaded`,
              null,
              { timeout: 60_000 },
            )
            found['shownAfterMs'] = Date.now() - started
            const box = await page.locator('main').boundingBox()
            const x = Math.round((box?.x ?? 0) + (box?.width ?? 0) / 2)
            const y = Math.round((box?.y ?? 0) + (box?.height ?? 0) / 2)
            found['at'] = [x, y]
            const seen: unknown[] = []
            for (const wait of [0, 1000, 2000, 3000]) {
              await page.waitForTimeout(wait)
              const before = Date.now()
              const middle = firstPixel(
                await page.screenshot({ clip: { x, y, width: 1, height: 1 } }),
              )
              seen.push({
                afterMs: before - started,
                tookMs: Date.now() - before,
                middle,
                state: await page.evaluate(STATE),
              })
            }
            found['seen'] = seen
            found['saidBeforeReading'] = said.length
            Object.assign(found, await page.evaluate(DRAWN))
            const whole = await page.screenshot()
            found['wholePictureBytes'] = whole.length
          } catch (error) {
            found['failed'] = String(error).slice(0, 200)
          }
          found['ms'] = Date.now() - started
        } finally {
          await browser.close()
        }
        process.stdout.write(
          `MEASURE ${process.platform} | ${browserName} | ${drawing} | ${round} | ${JSON.stringify(found)} | ${said.length} said | ${JSON.stringify([...new Set(said)])}\n`,
        )
        expect(true).toBe(true)
      })
    }
  }
}
