/**
 * The path the application is served from. On GitHub Pages the site of a
 * project lives under the name of its repository, so every address the
 * application uses for its own files starts with this path.
 *
 * Development, the unit tests, the browser tests and the published site all
 * use this one path, so that none of them can work by accident at another.
 * If the site moves, to another repository name or to a domain of its own,
 * this is the one place to change.
 */
export const SITE_PATH = '/MotoSphere/'

/**
 * The folder of the site that holds the files the engine of the globe
 * fetches while it runs. The build puts them there, the development server
 * answers them there, and the application tells the engine to look there.
 */
export const ENGINE_FOLDER = 'cesium'
