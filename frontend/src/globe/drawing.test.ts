import { describe, expect, it } from 'vitest'
import { browserGives, picturesAskedFor, picturesHeld } from '../test/drawing.ts'
import { browserDraws3D } from './drawing.ts'

describe('browserDraws3D', () => {
  it('says yes where the browser gives a 3D picture', () => {
    expect(browserDraws3D()).toBe(true)
  })

  it('says no where the browser gives no picture at all', () => {
    browserGives([])

    expect(browserDraws3D()).toBe(false)
  })

  it('says no where the browser gives only the older kind of 3D picture', () => {
    browserGives(['webgl'])

    expect(browserDraws3D()).toBe(false)
  })

  it('says yes where the browser gives the newer kind and not the older', () => {
    browserGives(['webgl2'])

    expect(browserDraws3D()).toBe(true)
  })

  it('asks once, for the kind the engine draws with, whatever the answer', () => {
    browserDraws3D()
    expect(picturesAskedFor()).toEqual(['webgl2'])

    browserGives(['webgl'])
    browserDraws3D()
    expect(picturesAskedFor()).toEqual(['webgl2', 'webgl2'])
  })

  it('gives the picture back', () => {
    browserDraws3D()
    browserDraws3D()
    browserDraws3D()

    expect(picturesHeld()).toBe(0)
  })

  it('says yes also where the browser takes no picture back', () => {
    browserGives(['webgl2'], false)

    expect(browserDraws3D()).toBe(true)
    expect(picturesHeld()).toBe(1)
  })
})
