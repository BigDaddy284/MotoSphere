import type { Page } from '@playwright/test'
import { distanceOfTheWholeEarth, SHARE_OF_THE_SHORTER_SIDE } from '../../src/globe/homeView.ts'
import { type Colour, colourAt } from '../pixel.ts'
import { expect, test } from './fixtures'

/**
 * These tests run in the browser of the globe tests, on the site as it was
 * built, with the real engine, and read the picture itself: what a person
 * sees when the page opens.
 *
 * Around the Earth the engine draws the stars, the sun and the moon where
 * they stand at the time of the page. So every test here gives the page one
 * fixed time, and the sky of the test is the same sky on every day.
 */
const THE_TIME_OF_THE_TESTS = new Date('2026-06-21T12:00:00Z')

/**
 * The angle the globe sees across the shorter side of its stage: 36 degrees
 * (see size.spec.ts for what that is for). It is written here a second
 * time, and not taken from the application, so that the test holds the
 * angle itself.
 */
const SEEN_ACROSS_THE_SHORTER_SIDE = Math.PI / 5

/** How long the globe may take to say that the Earth is drawn (see earth.spec.ts). */
const DRAWN_WITHIN = 60_000

// The screens the layout knows, by the size of the window.
const SCREENS: [name: string, width: number, height: number][] = [
  ['a desktop', 1280, 720],
  ['a phone held upright', 390, 844],
  ['a phone lying', 844, 390],
  ['a tablet held upright', 768, 1024],
  ['the smallest phone', 320, 568],
]

/** The eight directions of a compass, as steps across and down the page. */
const DIRECTIONS: [name: string, across: number, down: number][] = [
  ['east', 1, 0],
  ['south-east', Math.SQRT1_2, Math.SQRT1_2],
  ['south', 0, 1],
  ['south-west', -Math.SQRT1_2, Math.SQRT1_2],
  ['west', -1, 0],
  ['north-west', -Math.SQRT1_2, -Math.SQRT1_2],
  ['north', 0, -1],
  ['north-east', Math.SQRT1_2, -Math.SQRT1_2],
]

/** A place of the Earth, in degrees. */
type Place = { longitude: number; latitude: number }

/**
 * The place the globe is to open above. It is written here a second time,
 * and not taken from the application, so that the test holds the place
 * itself and not whatever the application says the place is.
 */
const ABOVE: Place = { longitude: -40, latitude: 30 }

/** The sea is this much more blue than red, at the least. */
const SEA = 50

/** How much more blue than red a colour is. */
function blueOverRed([red, , blue]: Colour): number {
  return blue - red
}

/**
 * Where a place of the Earth is in the picture, seen from straight above
 * `ABOVE` with north up, from a distance given in radii of the Earth: how
 * far across and down from the middle of the Earth's disc, in radii of that
 * disc. The Earth is taken for a ball, which it is to a third of a percent.
 */
function inThePicture(place: Place, distance: number): [across: number, down: number] {
  const degrees = Math.PI / 180
  const east = (place.longitude - ABOVE.longitude) * degrees
  const north = place.latitude * degrees
  const northOfTheMiddle = ABOVE.latitude * degrees
  // The place as a point of a ball of radius 1, the viewer above its top.
  const right = Math.cos(north) * Math.sin(east)
  const up =
    Math.cos(northOfTheMiddle) * Math.sin(north) -
    Math.sin(northOfTheMiddle) * Math.cos(north) * Math.cos(east)
  const towardsTheViewer =
    Math.sin(northOfTheMiddle) * Math.sin(north) +
    Math.cos(northOfTheMiddle) * Math.cos(north) * Math.cos(east)
  if (towardsTheViewer * distance <= 1) {
    throw new Error('This place is behind the edge of the Earth as it is seen from there')
  }
  // What is nearer to the viewer looks larger, and the edge of the disc is 1.
  const scale = Math.sqrt(distance * distance - 1) / (distance - towardsTheViewer)
  return [right * scale, -up * scale]
}

/** How bright a colour is: its red, green and blue together, from 0 to 765. */
function brightness([red, green, blue]: Colour): number {
  return red + green + blue
}

/**
 * The sky is black but for its stars, and a star is a point or two wide.
 * So the sky at a place is read at three points two pixels apart, and the
 * darkest of them is the sky.
 */
async function darkestOfThree(page: Page, x: number, y: number): Promise<number> {
  const read: number[] = []
  for (const step of [-2, 0, 2]) {
    read.push(brightness(await colourAt(page, Math.round(x) + step, Math.round(y) + step)))
  }
  return Math.min(...read)
}

/**
 * Opens the page at a size of the window, waits until the globe says that
 * the Earth is drawn, and gives the middle of the stage and the radius the
 * Earth is to have in it, in pixels of the page, and the distance it is
 * then seen from, in radii of the Earth.
 */
async function openAt(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height })
  await page.clock.setFixedTime(THE_TIME_OF_THE_TESTS)
  await page.goto('./')
  const stage = page.getByRole('main', { name: 'Globe' })
  await expect(stage.locator('[aria-busy]')).toHaveAttribute('aria-busy', 'false', {
    timeout: DRAWN_WITHIN,
  })
  const box = await stage.boundingBox()
  if (box === null) {
    throw new Error('The globe stage has no place in the page: it is not visible')
  }
  return {
    x: box.x + box.width / 2,
    y: box.y + box.height / 2,
    radius: (SHARE_OF_THE_SHORTER_SIDE * Math.min(box.width, box.height)) / 2,
    // A square of the shorter side, seen under that angle.
    distance: distanceOfTheWholeEarth(
      1,
      1,
      SEEN_ACROSS_THE_SHORTER_SIDE,
      SHARE_OF_THE_SHORTER_SIDE,
    ),
  }
}

test.describe('the globe as it opens', () => {
  for (const [screen, width, height] of SCREENS) {
    test(`shows the whole Earth in the middle of the stage, with the sky around it, on ${screen}`, async ({
      page,
    }) => {
      const middle = await openAt(page, width, height)

      for (const [direction, across, down] of DIRECTIONS) {
        // A tenth of the radius inside the edge of the Earth there is Earth,
        const inside = await colourAt(
          page,
          Math.round(middle.x + 0.9 * middle.radius * across),
          Math.round(middle.y + 0.9 * middle.radius * down),
        )
        expect(brightness(inside), `inside, to the ${direction}`).toBeGreaterThan(300)
        // and a tenth of the radius outside it there is sky.
        const outside = await darkestOfThree(
          page,
          middle.x + 1.1 * middle.radius * across,
          middle.y + 1.1 * middle.radius * down,
        )
        expect(outside, `outside, to the ${direction}`).toBeLessThan(150)
      }
    })
  }

  // The place does not depend on the screen: two of them will do.
  for (const [screen, width, height] of SCREENS.slice(0, 2)) {
    test(`is above the North Atlantic at 30 north and 40 west, north up, on ${screen}`, async ({
      page,
    }) => {
      const { x, y, radius, distance } = await openAt(page, width, height)
      const at = async (place: Place) => {
        const [across, down] = inThePicture(place, distance)
        return colourAt(page, Math.round(x + across * radius), Math.round(y + down * radius))
      }

      // Below the middle of the picture is the sea: blue before all.
      expect(blueOverRed(await at(ABOVE)), 'the middle is sea').toBeGreaterThan(SEA)

      // How far north. On the line of 40 west the ice of Greenland begins
      // at 66 north: 72 north is ice, nearly white, and 62 north is sea.
      const ice = await at({ longitude: -40, latitude: 72 })
      expect(Math.min(...ice), '72 north is the ice of Greenland').toBeGreaterThan(180)
      const south = await at({ longitude: -40, latitude: 62 })
      expect(blueOverRed(south), '62 north is sea').toBeGreaterThan(SEA)

      // How far west. On the line of 23 north the Sahara begins at 17 west:
      // 11 west is desert, pale and no more blue than red, and 23 west is sea.
      const desert = await at({ longitude: -11, latitude: 23 })
      expect(brightness(desert), '11 west is the Sahara, pale').toBeGreaterThan(550)
      expect(blueOverRed(desert), '11 west is the Sahara, not sea').toBeLessThan(30)
      const west = await at({ longitude: -23, latitude: 23 })
      expect(blueOverRed(west), '23 west is sea').toBeGreaterThan(SEA)

      // And the Americas are in view on the other side: the forest of the
      // Amazon, 5 south and 62 west, is green before all.
      const [forestRed, forestGreen, forestBlue] = await at({ longitude: -62, latitude: -5 })
      expect(forestGreen, 'the Amazon is green').toBeGreaterThan(forestRed)
      expect(forestGreen, 'the Amazon is green').toBeGreaterThan(forestBlue)
    })
  }
})
