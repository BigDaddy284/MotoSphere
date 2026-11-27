import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { chromium } from '@playwright/test'
import {
  FEATURES_OFF,
  GLOBE_BROWSER,
  SOFTWARE_3D_SWITCH,
  TEST_BROWSER,
  TEST_BROWSER_SWITCH,
} from '../browser.ts'
import { expect, takeTheTurn, test, TURN_FILE } from './fixtures'

/** Has the page show a 3D picture in each of some frames, one colour after another. */
const SHOW_3D_PICTURES = `new Promise((resolve, reject) => {
  const canvas = document.createElement('canvas')
  canvas.width = 300
  canvas.height = 200
  canvas.style.cssText = 'position: fixed; left: 0; top: 0; z-index: 99'
  document.body.append(canvas)
  const gl = canvas.getContext('webgl2')
  if (gl === null) {
    reject(new Error('the browser gives no 3D picture'))
    return
  }
  let frames = 0
  const draw = () => {
    gl.clearColor(frames / 30, 0.5, 1, 1)
    gl.clear(gl.COLOR_BUFFER_BIT)
    frames += 1
    if (frames < 30) {
      requestAnimationFrame(draw)
    } else {
      const names = gl.getExtension('WEBGL_debug_renderer_info')
      resolve({
        frames,
        size: [gl.drawingBufferWidth, gl.drawingBufferHeight],
        renderer: names === null ? '' : String(gl.getParameter(names.UNMASKED_RENDERER_WEBGL)),
        lost: gl.isContextLost(),
      })
    }
  }
  requestAnimationFrame(draw)
})`

test.describe('the browser of the globe tests', () => {
  test('is started as the browser of every test, and told to draw 3D pictures in software', async () => {
    // Inside a test, Playwright starts a browser with the options of the
    // project unless the call says otherwise.
    const started = await chromium.launchServer()
    try {
      const told = started.process().spawnargs
      expect(told.filter((word) => word.startsWith(FEATURES_OFF))).toEqual([TEST_BROWSER_SWITCH])
      expect(told.filter((word) => word.startsWith('--use-angle'))).toEqual([SOFTWARE_3D_SWITCH])
    } finally {
      await started.close()
    }
    expect(SOFTWARE_3D_SWITCH).toBe('--use-angle=swiftshader')
    expect(GLOBE_BROWSER).toEqual({
      ...TEST_BROWSER,
      args: [TEST_BROWSER_SWITCH, SOFTWARE_3D_SWITCH],
    })
  })

  test('shows 3D pictures, drawn in software, without a word of its own', async ({ page }) => {
    // The fixture of every browser test fails this test for any warning or
    // error on the console. A browser that is not told how to draw says four.
    await page.goto('./')
    const shown = await page.evaluate(SHOW_3D_PICTURES)
    expect(shown).toEqual({
      frames: 30,
      size: [300, 200],
      renderer: expect.stringContaining('SwiftShader'),
      lost: false,
    })
  })
})

test.describe('the globe tests', () => {
  test('are in a project of their own, after the project of the other tests', ({
    browserName,
  }, testInfo) => {
    expect(browserName).toBe('chromium')
    expect(testInfo.project.name).toBe('globe')
    expect(testInfo.config.projects.map((project) => project.name)).toEqual(['chromium', 'globe'])
    expect(testInfo.project.use.launchOptions).toEqual(GLOBE_BROWSER)
  })

  test('hold the turn while they run, where every test of the run finds it', ({
    turnFolder,
  }, testInfo) => {
    // The folder of this test's own results lies in the folder of the turn.
    expect(path.dirname(testInfo.outputDir)).toBe(turnFolder)
    expect(existsSync(path.join(turnFolder, TURN_FILE))).toBe(true)
    expect(() => takeTheTurn(turnFolder)).toThrow(
      'Two globe tests ran at once. They must run one at a time: see the project "globe" in playwright.config.ts.',
    )
    // The one who was refused has not taken the turn away.
    expect(existsSync(path.join(turnFolder, TURN_FILE))).toBe(true)
  })

  test('take the turn where nobody has it, and hand it back', () => {
    const folder = mkdtempSync(path.join(tmpdir(), 'turn-'))
    try {
      const inside = path.join(folder, 'not', 'there', 'yet')
      const handBack = takeTheTurn(inside)
      expect(existsSync(path.join(inside, TURN_FILE))).toBe(true)
      // The one who is refused is told what the system said, too.
      let refusal: unknown = null
      try {
        takeTheTurn(inside)
      } catch (error) {
        refusal = error
      }
      expect(refusal).toMatchObject({
        message: expect.stringContaining('Two globe tests ran at once.'),
        cause: { code: 'EEXIST' },
      })
      handBack()
      expect(existsSync(path.join(inside, TURN_FILE))).toBe(false)
      takeTheTurn(inside)()
      expect(existsSync(path.join(inside, TURN_FILE))).toBe(false)
    } finally {
      rmSync(folder, { recursive: true })
    }
  })

  // Four tests that do nothing but take their time. With one worker for the
  // project they run one after another. Were the project given two, two of
  // them would run at once, and the second would not get the turn.
  for (const number of [1, 2, 3, 4]) {
    test(`run one at a time (${number} of 4)`, async ({ page }) => {
      await page.goto('./')
      await page.waitForTimeout(300)
      expect(await page.title()).toBe('MotoSphere')
    })
  }
})
