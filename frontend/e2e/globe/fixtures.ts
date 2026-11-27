import { mkdirSync, openSync, closeSync, rmSync } from 'node:fs'
import path from 'node:path'
import { expect, test as base } from '../fixtures'

/** The file that says a globe test is running. */
export const TURN_FILE = 'one-globe-test-at-a-time'

/**
 * Takes the turn of the globe tests, and gives the way to hand it back.
 *
 * A turn is a file in `folder` that only one can make. Whoever finds it
 * there is running beside another globe test, and is told so.
 */
export function takeTheTurn(folder: string): () => void {
  mkdirSync(folder, { recursive: true })
  const file = path.join(folder, TURN_FILE)
  try {
    closeSync(openSync(file, 'wx'))
  } catch (error) {
    // What the system said goes with the sentence, in case it was something else.
    throw new Error(
      'Two globe tests ran at once. They must run one at a time: see the project "globe" in playwright.config.ts.',
      { cause: error },
    )
  }
  return () => {
    rmSync(file)
  }
}

type GlobeFixtures = {
  /** Where the turn of the globe tests is kept during this run. */
  turnFolder: string
  oneAtATime: undefined
}

/**
 * Every globe test uses this `test`. It is the `test` of all browser tests,
 * and it also holds the turn of the globe tests from the start of the test
 * to its end, so a globe test that runs beside another fails.
 */
export const test = base.extend<GlobeFixtures>({
  // The folder of the results of the whole run: every test of the run finds
  // the turn there, and Playwright empties it before a run starts. A fixture
  // is told about its test only after the fixtures it asks for, and has to
  // name one: the page, which every browser test has.
  turnFolder: async ({ page: _page }, provide, testInfo) => {
    await provide(testInfo.project.outputDir)
  },
  oneAtATime: [
    async ({ turnFolder }, provide) => {
      const handBack = takeTheTurn(turnFolder)
      // What follows runs when the test is over, however it ended.
      await provide(undefined)
      handBack()
    },
    { auto: true },
  ],
})

export { expect }
