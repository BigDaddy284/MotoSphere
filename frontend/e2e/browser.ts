import type { LaunchOptions } from '@playwright/test'

/**
 * How the browser of the browser tests is started.
 *
 * The browser has a feature that is on by default on Windows 11 and Windows
 * Server 2025: for every connection it opens, it asks Windows for a local
 * port picked at random instead of the next free one. Now and then Windows
 * then refuses the connection, and the browser reports
 * `net::ERR_NO_BUFFER_SPACE` or `net::ERR_ADDRESS_IN_USE` although the
 * machine has room for thousands more. A browser test then fails in
 * `page.goto` for no fault of the application. The tests run with that
 * feature off (FND-054; TESTING.md has what was measured).
 *
 * A browser takes one list of features to turn off, and Playwright already
 * gives it one. So Playwright's own list is taken out and given again with
 * the one feature added. The list is written out here, as Playwright 1.63.0
 * has it; a browser test holds it to what Playwright really gives, so an
 * upgrade that changes the list fails that test until this one follows.
 */
export const PLAYWRIGHTS_OWN_FEATURES_OFF = [
  'AvoidUnnecessaryBeforeUnloadCheckSync',
  'DestroyProfileOnBrowserClose',
  'DialMediaRouteProvider',
  'GlobalMediaControls',
  'HttpsUpgrades',
  'LensOverlay',
  'MediaRouter',
  'PaintHolding',
  'ThirdPartyStoragePartitioning',
  'BlockOriginHeaderModificationOnRedirect',
  'Translate',
  'AutoDeElevate',
  'OptimizationHints',
  'msForceBrowserSignIn',
  'msEdgeUpdateLaunchServicesPreferredVersion',
] as const

/** The feature the tests run without. It exists on Windows only. */
export const RANDOM_PORTS_FEATURE = 'TcpPortRandomizationWin'

/** The word a browser is told its list of features to turn off with. */
export const FEATURES_OFF = '--disable-features='

/** What Playwright tells the browser by itself. */
export const PLAYWRIGHTS_OWN_SWITCH = `${FEATURES_OFF}${PLAYWRIGHTS_OWN_FEATURES_OFF.join(',')}`

/** What the browser of the tests is told instead. */
export const TEST_BROWSER_SWITCH = `${PLAYWRIGHTS_OWN_SWITCH},${RANDOM_PORTS_FEATURE}`

export const TEST_BROWSER: LaunchOptions = {
  ignoreDefaultArgs: [PLAYWRIGHTS_OWN_SWITCH],
  args: [TEST_BROWSER_SWITCH],
}

/**
 * The word a browser is told with to draw 3D pictures in software, with the
 * renderer that comes with it.
 *
 * The browser of the tests has no graphics card to draw with, on GitHub's
 * machines as little as on a developer's. Left to itself, it still draws a
 * 3D picture in software, but it shows the picture on the page by a way
 * round: for every page with a 3D picture it then logs four warnings of its
 * own ("GPU stall due to ReadPixels"), which the browser tests count as
 * problems of the page, and the Earth takes four to five times as long to
 * appear. Told this word, it does neither (FND-058; TESTING.md has what was
 * measured).
 */
export const SOFTWARE_3D_SWITCH = '--use-angle=swiftshader'

/**
 * How the browser of the globe tests is started: as the browser of every
 * test, and told to draw 3D pictures in software.
 */
export const GLOBE_BROWSER: LaunchOptions = {
  ...TEST_BROWSER,
  args: [TEST_BROWSER_SWITCH, SOFTWARE_3D_SWITCH],
}
