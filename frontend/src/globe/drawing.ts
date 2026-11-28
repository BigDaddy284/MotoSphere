/**
 * Asks the browser whether it gives the page a 3D picture.
 *
 * The engine of the globe draws the Earth as a 3D picture (WebGL 2). A
 * browser can be without one: it is too old, its 3D graphics are switched
 * off, or the computer has nothing to draw them with. Started there, the
 * engine puts up a panel of its own and logs an error. So the page asks
 * first, on a drawing surface of its own that no one sees, and gives the
 * picture back at once: a browser keeps only so many of them for a page.
 *
 * The function names nothing outside itself, so that a browser test can
 * hand it to a page as it stands.
 */
export function browserDraws3D(): boolean {
  const picture = document.createElement('canvas').getContext('webgl2')
  if (picture === null) {
    return false
  }
  picture.getExtension('WEBGL_lose_context')?.loseContext()
  return true
}
