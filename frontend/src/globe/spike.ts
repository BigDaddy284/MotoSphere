import {
  buildModuleUrl,
  CesiumWidget,
  ImageryLayer,
  TileMapServiceImageryProvider,
} from '@cesium/engine'

// The two rules of the engine's own stylesheet that give the surface its size.
const RULES = '.cesium-widget, .cesium-widget canvas { display: block; width: 100%; height: 100%; }'

export function start(container: Element): CesiumWidget {
  if (document.querySelector('style[data-spike]') === null) {
    const style = document.createElement('style')
    style.dataset['spike'] = ''
    style.textContent = RULES
    document.head.append(style)
  }
  const widget = new CesiumWidget(container, {
    baseLayer: ImageryLayer.fromProviderAsync(
      TileMapServiceImageryProvider.fromUrl(buildModuleUrl('Assets/Textures/NaturalEarthII/')),
    ),
    requestRenderMode: globalThis.location.search.includes('onrequest'),
  })
  Object.assign(globalThis, { spikeWidget: widget, spikeStart: start })
  return widget
}
