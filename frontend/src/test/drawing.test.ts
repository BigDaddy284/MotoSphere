import { describe, expect, it } from 'vitest'
import { browserGives, installDrawing, picturesAskedFor, picturesHeld } from './drawing.ts'

/** Asks the stand-in browser for a picture of a kind, as a page would. */
function ask(kind: string) {
  return document.createElement('canvas').getContext(kind)
}

/** Asks it for the newer kind of 3D picture. */
function askNewer() {
  return document.createElement('canvas').getContext('webgl2')
}

/** Asks it for the older kind of 3D picture. */
function askOlder() {
  return document.createElement('canvas').getContext('webgl')
}

describe('the stand-in for the drawing surface', () => {
  it('is a current browser at the start of a test: both kinds of 3D picture', () => {
    expect(ask('webgl2')).not.toBeNull()
    expect(ask('webgl')).not.toBeNull()
  })

  it('gives no picture of a kind it was not told to give', () => {
    expect(ask('2d')).toBeNull()
    expect(ask('bitmaprenderer')).toBeNull()

    browserGives(['webgl'])
    expect(ask('webgl2')).toBeNull()
    expect(ask('webgl')).not.toBeNull()

    browserGives([])
    expect(ask('webgl2')).toBeNull()
    expect(ask('webgl')).toBeNull()
  })

  it('says which kinds the page asked for, in the order it asked, also those it did not give', () => {
    expect(picturesAskedFor()).toEqual([])

    ask('webgl2')
    ask('2d')
    ask('webgl2')

    expect(picturesAskedFor()).toEqual(['webgl2', '2d', 'webgl2'])
  })

  it('counts a picture as held until it is given back', () => {
    expect(picturesHeld()).toBe(0)

    const first = askNewer()
    const second = askNewer()
    ask('2d')
    expect(picturesHeld()).toBe(2)

    first?.getExtension('WEBGL_lose_context')?.loseContext()
    expect(picturesHeld()).toBe(1)

    second?.getExtension('WEBGL_lose_context')?.loseContext()
    expect(picturesHeld()).toBe(0)
  })

  it('takes a picture back once, however often that is said', () => {
    const first = askNewer()
    askNewer()

    const way = first?.getExtension('WEBGL_lose_context')
    way?.loseContext()
    way?.loseContext()
    first?.getExtension('WEBGL_lose_context')?.loseContext()

    expect(picturesHeld()).toBe(1)
  })

  it('hands out the way to give a picture back under its own name only', () => {
    const picture = askNewer()

    expect(picture?.getExtension('WEBGL_lose_context')).not.toBeNull()
    expect(picture?.getExtension('WEBGL_debug_renderer_info')).toBeNull()
  })

  it('can be a browser that takes no picture back', () => {
    browserGives(['webgl2'], false)

    const picture = askNewer()

    expect(picture).not.toBeNull()
    expect(picture?.getExtension('WEBGL_lose_context')).toBeNull()
    expect(picturesHeld()).toBe(1)
  })

  it('keeps for a picture what the browser was when it gave it', () => {
    const picture = askNewer()
    browserGives(['webgl2'], false)

    picture?.getExtension('WEBGL_lose_context')?.loseContext()

    expect(picturesHeld()).toBe(0)
  })

  it('is a current browser again that was asked for nothing, once it is put in place', () => {
    browserGives([], false)
    ask('webgl2')
    browserGives(['webgl2'], false)
    ask('webgl2')
    expect(picturesAskedFor()).toHaveLength(2)
    expect(picturesHeld()).toBe(1)

    installDrawing()

    expect(picturesAskedFor()).toEqual([])
    expect(picturesHeld()).toBe(0)
    expect(askOlder()?.getExtension('WEBGL_lose_context')).not.toBeNull()
  })
})
