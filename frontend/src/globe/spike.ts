import {
  buildModuleUrl,
  CesiumWidget,
  ImageryLayer,
  TileMapServiceImageryProvider,
} from '@cesium/engine'

// The two rules of the engine's own stylesheet that give the surface its size.
const RULES = '.cesium-widget, .cesium-widget canvas { display: block; width: 100%; height: 100%; }'

export function start(container: Element, times: Record<string, number>): CesiumWidget {
  if (document.querySelector('style[data-spike]') === null) {
    const style = document.createElement('style')
    style.dataset['spike'] = ''
    style.textContent = RULES
    document.head.append(style)
  }
  times['start'] = performance.now()
  const layer = ImageryLayer.fromProviderAsync(
    TileMapServiceImageryProvider.fromUrl(buildModuleUrl('Assets/Textures/NaturalEarthII/')),
  )
  const widget = new CesiumWidget(container, {
    baseLayer: layer,
    requestRenderMode: globalThis.location.search.includes('onrequest'),
  })
  times['widget'] = performance.now()
  layer.readyEvent.addEventListener(() => {
    times['layerReady'] = performance.now()
  })
  const frameAt: number[] = []
  const progress: [number, number][] = []
  widget.scene.globe.tileLoadProgressEvent.addEventListener((waiting: number) => {
    if (progress.length < 80) {
      progress.push([performance.now(), waiting])
    }
  })
  let frames = 0
  widget.scene.postRender.addEventListener(() => {
    frames += 1
    if (frameAt.length < 40) {
      frameAt.push(performance.now())
    }
    times['firstFrame'] ??= performance.now()
    if (layer.ready && widget.scene.globe.tilesLoaded && times['loaded'] === undefined) {
      times['loaded'] = performance.now()
      times['framesWhenLoaded'] = frames
    }
  })
  Object.assign(globalThis, {
    spikeWidget: widget,
    spikeStart: start,
    spikeTrace: { frameAt, progress },
  })
  return widget
}
