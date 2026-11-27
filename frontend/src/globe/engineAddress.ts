import { ENGINE_FOLDER, SITE_PATH } from '../../site.ts'

declare global {
  /**
   * The name under which the engine of the globe looks for the address of
   * its own files. The name is the engine's, not this application's.
   */
  var CESIUM_BASE_URL: string | undefined
}

/**
 * The address beneath which the engine of the globe fetches its own files:
 * its background scripts, programs, tables and pictures. It is the folder of
 * this site that holds them, and it names no other computer, so the engine
 * asks the site the page came from and nobody else.
 *
 * Left to itself the engine works the address out from where its own code
 * was loaded. In the built site that is a file of the build, with a name of
 * its own, and the engine's files are not beside it.
 */
export const ENGINE_ADDRESS = `${SITE_PATH}${ENGINE_FOLDER}/`

/**
 * Tells the engine where its files are. The engine reads the address the
 * first time it needs a file and keeps it from then on, so this is done
 * before anything of the application is shown, and nowhere else.
 */
export function tellTheEngineWhereItsFilesAre(): void {
  globalThis.CESIUM_BASE_URL = ENGINE_ADDRESS
}
