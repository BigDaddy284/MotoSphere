import { Cartesian3, PerspectiveFrustum } from '@cesium/core'
import {
  buildModuleUrl,
  CesiumWidget,
  ImageryLayer,
  type Scene,
  TileMapServiceImageryProvider,
} from '@cesium/engine'
// The engine's own rules for its widget: the size of the drawing surface,
// and the look of what the engine itself puts over it.
import '@cesium/engine/Source/Widget/CesiumWidget.css'
import type { Start } from './Globe.tsx'
import { distanceOfTheWholeEarth, HOME, SHARE_OF_THE_SHORTER_SIDE } from './homeView.ts'
import { ANGLE_ACROSS_THE_SHORTER_SIDE, angleAcrossTheLongerSide } from './lens.ts'

/**
 * The pictures of the Earth that come with the engine (Natural Earth II),
 * as a folder of the engine's own files. They are files of this site: no
 * key, no account, and nothing is asked of another computer.
 */
const PICTURES_OF_THE_EARTH = 'Assets/Textures/NaturalEarthII/'

/**
 * Gives the engine the lens for its surface as it is now: the angle across
 * the longer side under which the shorter side is seen as the globe sees it
 * (see `lens.ts`).
 *
 * The engine sees in perspective when it starts. Were it ever to see
 * otherwise, its own lens would be left as it is.
 */
function seeByTheShorterSide(scene: Scene): void {
  const { camera, canvas } = scene
  const { frustum } = camera
  if (frustum instanceof PerspectiveFrustum) {
    frustum.fov = angleAcrossTheLongerSide(
      canvas.clientWidth,
      canvas.clientHeight,
      ANGLE_ACROSS_THE_SHORTER_SIDE,
    )
  }
}

/**
 * Puts the camera above the place the globe opens above, looking straight
 * down, north up, and as far away as it takes for the whole Earth to be in
 * view on the surface as it is now.
 *
 * The distance is worked out from the lens the engine has been given.
 * Were the engine ever to see otherwise than in perspective, its own view
 * would be left as it is.
 */
function lookAtTheWholeEarth(scene: Scene): void {
  const { camera, canvas, ellipsoid } = scene
  const { frustum } = camera
  if (frustum instanceof PerspectiveFrustum && frustum.fov !== undefined) {
    const distance = distanceOfTheWholeEarth(
      canvas.clientWidth,
      canvas.clientHeight,
      frustum.fov,
      SHARE_OF_THE_SHORTER_SIDE,
    )
    camera.setView({
      destination: Cartesian3.fromDegrees(
        HOME.longitude,
        HOME.latitude,
        (distance - 1) * ellipsoid.maximumRadius,
      ),
    })
  }
}

/**
 * Starts the engine of the globe in an element of the page: one widget of
 * the engine, which draws the Earth with the pictures that come with it.
 * The globe opens with the whole Earth in view (see `homeView.ts`).
 *
 * The engine itself keeps its surface as large as the element, looks at
 * that in every turn of its work, and draws anew when the size has
 * changed. Before each such turn it is given the lens for the surface as
 * it then is, so that what is in view keeps its size across the shorter
 * side when the element changes its shape, and the camera stays where it
 * is.
 *
 * The engine draws when something has changed and not all the time. It
 * draws the Earth in pieces and fetches the picture of each. When no piece
 * it needs is waiting any more, for its shape or for its picture, the
 * Earth is drawn complete, and the engine says so to the listener, once.
 * It says it when it has finished that picture and not in the middle of
 * its work, so whoever is told can stop the engine there and then.
 *
 * Stopping takes the widget away and gives the browser its 3D picture
 * back. The engine's own way of ending does not do the second, and a
 * browser keeps only so many 3D pictures for a page.
 */
export const start: Start = (surface, listener) => {
  const pictures = ImageryLayer.fromProviderAsync(
    TileMapServiceImageryProvider.fromUrl(buildModuleUrl(PICTURES_OF_THE_EARTH)),
  )
  const widget = new CesiumWidget(surface, { baseLayer: pictures, requestRenderMode: true })
  const { scene } = widget
  seeByTheShorterSide(scene)
  lookAtTheWholeEarth(scene)
  scene.preUpdate.addEventListener(() => {
    seeByTheShorterSide(scene)
  })

  const askNoMore = scene.postRender.addEventListener(() => {
    if (scene.globe.tilesLoaded) {
      askNoMore()
      queueMicrotask(listener.drawn)
    }
  })

  return () => {
    const picture = scene.canvas.getContext('webgl2')
    widget.destroy()
    picture?.getExtension('WEBGL_lose_context')?.loseContext()
  }
}
