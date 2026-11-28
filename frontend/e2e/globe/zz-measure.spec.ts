import { expect, test } from './fixtures'

/**
 * A measurement of the planner's, not a test of the application and not
 * for merging: how long the globe takes to say that the Earth is drawn,
 * and what the engine does after it has said so, on this machine.
 */
const NOTE = `(() => {
  const note = { frames: [], workers: [], gaps: [], ticks: 0, last: 0, said: undefined }
  globalThis.__note = note
  let drawing = false
  const context = WebGL2RenderingContext.prototype
  for (const way of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced', 'drawRangeElements']) {
    const draw = context[way]
    context[way] = function (...given) {
      if (!drawing) {
        drawing = true
        note.frames.push([Math.round(performance.now()), note.ticks])
        queueMicrotask(() => {
          drawing = false
        })
      }
      return draw.apply(this, given)
    }
  }
  const TheWorker = globalThis.Worker
  globalThis.Worker = class extends TheWorker {
    constructor(url, ...rest) {
      super(url, ...rest)
      const name = String(url).split('/').slice(-1)[0].slice(0, 12)
      this.addEventListener('message', () => note.workers.push([Math.round(performance.now()), name]))
    }
  }
  const tick = (now) => {
    note.ticks += 1
    if (note.last > 0 && now - note.last > 500) note.gaps.push([Math.round(note.last), Math.round(now - note.last)])
    note.last = now
    requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
  new MutationObserver((changes) => {
    for (const { target } of changes) {
      if (
        note.said === undefined &&
        target instanceof Element &&
        target.closest('main') !== null &&
        target.getAttribute('aria-busy') === 'false'
      ) {
        note.said = [Math.round(performance.now()), note.ticks]
      }
    }
  }).observe(document, { subtree: true, attributes: true, attributeFilter: ['aria-busy'] })
})()`

const SUMMARY = `(() => {
  const note = globalThis.__note
  const [said, tick] = note.said
  const after = note.frames.filter(([time]) => time > said)
  return JSON.stringify({
    said,
    frames: note.frames.length,
    after: after.map(([time, at]) => [time - said, at - tick]),
    ticksSince: note.ticks - tick,
    gaps: note.gaps,
    picker: note.workers.filter(([, name]) => name.startsWith('incremental')).map(([time]) => time - said),
    workers: note.workers.length,
    lastWorker: Math.max(...note.workers.map(([time]) => time)) - said,
  })
})()`

for (const [name, width, height, times] of [
  ['a desktop', 1280, 720, 14],
  ['a tablet held upright', 768, 1024, 8],
] as const) {
  test(`MEASUREMENT: the Earth on ${name}, ${times} times`, async ({ browser, baseURL }) => {
    test.setTimeout(900_000)
    for (let round = 0; round < times; round += 1) {
      const page = await browser.newPage({
        viewport: { width, height },
        ...(baseURL === undefined ? {} : { baseURL }),
      })
      await page.addInitScript(NOTE)
      const began = Date.now()
      await page.goto('./')
      const arrived = Date.now() - began
      await expect(
        page.getByRole('main', { name: 'Globe' }).locator('[aria-busy]'),
      ).toHaveAttribute('aria-busy', 'false', { timeout: 150_000 })
      const drawn = Date.now() - began
      await page.waitForTimeout(4_000)
      const summary = await page.evaluate(SUMMARY)
      process.stdout.write(
        `MEASURED ${name} ${round}: page ${arrived} ms, drawn ${drawn} ms, ${String(summary)}\n`,
      )
      await page.close()
    }
  })
}
