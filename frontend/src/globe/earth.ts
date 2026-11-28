import {
  buildModuleUrl,
  CesiumWidget,
  ImageryLayer,
  TileMapServiceImageryProvider,
} from '@cesium/engine'
// The engine's own rules for its widget: the size of the drawing surface,
// and the look of what the engine itself puts over it.
import '@cesium/engine/Source/Widget/CesiumWidget.css'
import type { Start } from './Globe.tsx'

/**
 * The pictures of the Earth that come with the engine (Natural Earth II),
 * as a folder of the engine's own files. They are files of this site: no
 * key, no account, and nothing is asked of another computer.
 */
const PICTURES_OF_THE_EARTH = 'Assets/Textures/NaturalEarthII/'

/**
 * Starts the engine of the globe in an element of the page: one widget of
 * the engine, which draws the Earth with the pictures that come with it.
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
