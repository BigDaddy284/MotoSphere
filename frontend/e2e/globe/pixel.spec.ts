import { colourAt } from '../pixel.ts'
import { expect, test } from './fixtures'

/**
 * Covers the page with a 3D picture and shows it: the upper half in one
 * colour and the lower half in another. A 3D picture counts its lines from
 * the bottom, a page from the top.
 */
const SHOW_3D_COLOURS = `new Promise((resolve, reject) => {
  const canvas = document.createElement('canvas')
  canvas.width = innerWidth
  canvas.height = innerHeight
  canvas.style.cssText = 'position: fixed; left: 0; top: 0; z-index: 2147483647'
  document.body.append(canvas)
  const gl = canvas.getContext('webgl2')
  if (gl === null) {
    reject(new Error('the browser gives no 3D picture'))
    return
  }
  const half = canvas.height / 2
  let frames = 0
  const draw = () => {
    gl.enable(gl.SCISSOR_TEST)
    gl.scissor(0, half, canvas.width, half)
    gl.clearColor(0.2, 0.4, 0.6, 1)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.scissor(0, 0, canvas.width, half)
    gl.clearColor(1, 0.6, 0.2, 1)
    gl.clear(gl.COLOR_BUFFER_BIT)
    frames += 1
    if (frames < 3) {
      requestAnimationFrame(draw)
    } else {
      requestAnimationFrame(() => resolve([canvas.width, canvas.height]))
    }
  }
  requestAnimationFrame(draw)
})`

test.describe('the colour of a point of a 3D picture', () => {
  test('is read from outside the page, without a word of the browser', async ({ page }) => {
    // The fixture of every browser test fails this test for any warning or
    // error on the console. A page that reads its own 3D picture gets one.
    await page.goto('./')
    expect(await page.evaluate(SHOW_3D_COLOURS)).toEqual([1280, 720])
    const upper: [number, number, number] = [51, 102, 153]
    const lower: [number, number, number] = [255, 153, 51]
    const points: [number, number, [number, number, number]][] = [
      [0, 0, upper],
      [1279, 0, upper],
      [640, 180, upper],
      [0, 359, upper],
      [1279, 359, upper],
      [0, 360, lower],
      [1279, 360, lower],
      [640, 540, lower],
      [0, 719, lower],
      [1279, 719, lower],
    ]
    for (const [x, y, colour] of points) {
      expect(await colourAt(page, x, y), `at (${x}, ${y})`).toEqual(colour)
    }
  })
})
