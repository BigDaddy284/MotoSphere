import { describe, expect, it } from 'vitest'
import type { Listener, Start } from '../globe/Globe.tsx'
import { noSuchEngine, noSuchLoading, standInEngine } from './engine.ts'

function inThePage(): HTMLElement {
  const element = document.createElement('div')
  document.body.append(element)
  return element
}

/** Somebody for an engine to say things to, where a test does not care what it says. */
const NOBODY: Listener = { drawn: () => undefined }

/** Somebody for an engine to say things to, and how often it was told the picture is drawn. */
function somebody() {
  const heard = { drawn: 0 }
  const listener: Listener = {
    drawn: () => {
      heard.drawn += 1
    },
  }
  return { heard, listener }
}

/** A stand-in that has arrived, and its way to start an engine. */
async function hasArrived() {
  const engine = standInEngine()
  const loaded = engine.load()
  await engine.arrives()
  return { engine, start: await loaded }
}

describe('the stand-in for the engine of the globe', () => {
  it('has been asked for nothing and has started nothing at first', () => {
    const engine = standInEngine()

    expect(engine.loadings()).toBe(0)
    expect(engine.engines()).toEqual([])
    expect(engine.running()).toEqual([])
  })

  it('counts every time it is asked for, and does not arrive by itself', async () => {
    const engine = standInEngine()
    const arrived: string[] = []

    const first = engine.load()
    const second = engine.load()
    void first.then(() => arrived.push('first'))
    void second.then(() => arrived.push('second'))
    await new Promise((resolve) => setTimeout(resolve, 20))

    expect(engine.loadings()).toBe(2)
    expect(arrived).toEqual([])
  })

  it('arrives when the test says so: the loading asked for first, or the one named', async () => {
    const engine = standInEngine()
    const arrived: string[] = []
    void engine.load().then(() => arrived.push('first'))
    void engine.load().then(() => arrived.push('second'))
    void engine.load().then(() => arrived.push('third'))

    await engine.arrives(1)
    expect(arrived).toEqual(['second'])

    await engine.arrives()
    expect(arrived).toEqual(['second', 'first'])

    await engine.arrives(2)
    expect(arrived).toEqual(['second', 'first', 'third'])
  })

  it('fails to load when the test says so, with what the test says went wrong', async () => {
    const engine = standInEngine()
    const why = new Error('The file could not be fetched.')
    const caught: unknown[] = []
    void engine.load().catch((reason: unknown) => caught.push(reason))
    void engine.load().catch(() => caught.push('the second'))

    await engine.fails(why)

    expect(caught).toEqual([why])
    expect(caught[0]).toBe(why)
    expect(engine.engines()).toEqual([])

    await engine.fails(why, 1)

    expect(caught).toEqual([why, 'the second'])
  })

  it.each([
    { how: 'arrives', ends: 'well' },
    { how: 'fails', ends: 'badly' },
  ] as const)(
    'comes back from a loading that $how only when everything that waited on it has run',
    async ({ how, ends }) => {
      const engine = standInEngine()
      const seen: string[] = []
      // Something that waits on the loading, and on twenty more things
      // after it, each of which is ready at once.
      let chain: Promise<unknown> = engine.load().then(
        () => 'well',
        () => 'badly',
      )
      for (let link = 0; link < 20; link += 1) {
        chain = chain.then((ended) => ended)
      }
      void chain.then((ended) => seen.push(`The loading ended ${String(ended)}.`))

      await (how === 'arrives' ? engine.arrives() : engine.fails(new Error('No.')))

      expect(seen).toEqual([`The loading ended ${ends}.`])
    },
  )

  it.each([
    { asked: 0, which: undefined, named: 0 },
    { asked: 0, which: 0, named: 0 },
    { asked: 2, which: 2, named: 2 },
    { asked: 1, which: -1, named: -1 },
  ])(
    'tells a test that names loading $which after $asked askings that there is none',
    async ({ asked, which, named }) => {
      const engine = standInEngine()
      for (let count = 0; count < asked; count += 1) {
        void engine.load()
      }

      await expect(engine.arrives(which)).rejects.toThrow(noSuchLoading(asked, named))
      await expect(engine.fails(new Error('No.'), which)).rejects.toThrow(
        noSuchLoading(asked, named),
      )
      expect(noSuchLoading(2, 2)).toBe(
        'The engine was asked for 2 times, so there is no loading number 2.',
      )
    },
  )

  it('remembers where each engine was started, and whether that was in the page', async () => {
    const engine = standInEngine()
    const here = inThePage()
    const nowhere = document.createElement('div')
    const loaded = engine.load()
    await engine.arrives()
    const start = await loaded

    start(here, NOBODY)
    start(nowhere, NOBODY)

    expect(engine.engines()).toEqual([
      { surface: here, inThePage: true, stops: 0 },
      { surface: nowhere, inThePage: false, stops: 0 },
    ])
    expect(engine.engines()[0]?.surface).toBe(here)
    expect(engine.running()).toEqual([here, nowhere])
  })

  it('counts how often each engine was stopped, and runs only what was never stopped', async () => {
    const engine = standInEngine()
    const first = inThePage()
    const second = inThePage()
    const loaded = engine.load()
    await engine.arrives()
    const start = await loaded
    const stopTheFirst = start(first, NOBODY)
    const stopTheSecond = start(second, NOBODY)

    stopTheFirst()

    expect(engine.engines().map(({ stops }) => stops)).toEqual([1, 0])
    expect(engine.running()).toEqual([second])

    stopTheFirst()
    stopTheSecond()

    expect(engine.engines().map(({ stops }) => stops)).toEqual([2, 1])
    expect(engine.running()).toEqual([])
  })

  it('gives every loading the same way to start, and keeps one list of engines', async () => {
    const engine = standInEngine()
    const ways: Start[] = []
    void engine.load().then((start) => ways.push(start))
    void engine.load().then((start) => ways.push(start))
    await engine.arrives(0)
    await engine.arrives(1)

    ways[0]?.(inThePage(), NOBODY)
    ways[1]?.(inThePage(), NOBODY)

    expect(ways).toHaveLength(2)
    expect(engine.engines()).toHaveLength(2)
  })

  it('cannot be started once the test has broken it, and says what the test says', async () => {
    const engine = standInEngine()
    const why = new Error('The browser gave no picture.')
    const loaded = engine.load()
    await engine.arrives()
    const start = await loaded
    start(inThePage(), NOBODY)

    engine.breaksAtTheStart(why)

    expect(() => start(inThePage(), NOBODY)).toThrow(why)
    expect(engine.engines()).toHaveLength(1)
    expect(engine.running()).toHaveLength(1)
  })

  it('hands out what it remembers as a copy that a test cannot change it by', async () => {
    const engine = standInEngine()
    const loaded = engine.load()
    await engine.arrives()
    ;(await loaded)(inThePage(), NOBODY)

    const [seen] = engine.engines()
    if (seen !== undefined) {
      seen.stops = 5
    }

    expect(engine.engines().map(({ stops }) => stops)).toEqual([0])
    expect(engine.running()).toHaveLength(1)
  })

  it('is each its own: two stand-ins share nothing', async () => {
    const one = standInEngine()
    const other = standInEngine()
    const loaded = one.load()
    await one.arrives()
    ;(await loaded)(inThePage(), NOBODY)

    expect(other.loadings()).toBe(0)
    expect(other.engines()).toEqual([])
  })

  it('says nothing by itself to whom an engine was handed', async () => {
    const { start } = await hasArrived()
    const { heard, listener } = somebody()

    start(inThePage(), listener)
    await new Promise((resolve) => setTimeout(resolve, 20))

    expect(heard.drawn).toBe(0)
  })

  it('has an engine say that its picture is drawn when the test says so: the one started first, or the one named', async () => {
    const { engine, start } = await hasArrived()
    const first = somebody()
    const second = somebody()
    const third = somebody()
    start(inThePage(), first.listener)
    start(inThePage(), second.listener)
    start(inThePage(), third.listener)

    engine.draws(1)
    expect([first.heard.drawn, second.heard.drawn, third.heard.drawn]).toEqual([0, 1, 0])

    engine.draws()
    expect([first.heard.drawn, second.heard.drawn, third.heard.drawn]).toEqual([1, 1, 0])

    engine.draws(2)
    expect([first.heard.drawn, second.heard.drawn, third.heard.drawn]).toEqual([1, 1, 1])
  })

  it('has an engine say it as often as the test says so, stopped or not', async () => {
    const { engine, start } = await hasArrived()
    const { heard, listener } = somebody()
    const stop = start(inThePage(), listener)

    engine.draws()
    engine.draws()
    expect(heard.drawn).toBe(2)

    stop()
    engine.draws()

    expect(heard.drawn).toBe(3)
    expect(engine.engines().map(({ stops }) => stops)).toEqual([1])
  })

  it('says it at once, before it comes back to the test', async () => {
    const { engine, start } = await hasArrived()
    const { heard, listener } = somebody()
    start(inThePage(), listener)

    engine.draws()

    expect(heard.drawn).toBe(1)
  })

  it('lets what the listener fails with come back to the test', async () => {
    const { engine, start } = await hasArrived()
    const why = new Error('The listener could not take it.')
    start(inThePage(), {
      drawn: () => {
        throw why
      },
    })

    expect(() => {
      engine.draws()
    }).toThrow(why)
  })

  it.each([
    { started: 0, which: undefined, named: 0 },
    { started: 0, which: 0, named: 0 },
    { started: 2, which: 2, named: 2 },
    { started: 1, which: -1, named: -1 },
  ])(
    'tells a test that names engine $which after $started starts that there is none',
    async ({ started, which, named }) => {
      const { engine, start } = await hasArrived()
      const { heard, listener } = somebody()
      for (let count = 0; count < started; count += 1) {
        start(inThePage(), listener)
      }

      expect(() => {
        engine.draws(which)
      }).toThrow(noSuchEngine(started, named))
      expect(heard.drawn).toBe(0)
      expect(noSuchEngine(2, 2)).toBe('2 engines were started, so there is no engine number 2.')
    },
  )

  it('gives an engine that could not be started no number', async () => {
    const { engine, start } = await hasArrived()
    const first = somebody()
    const never = somebody()
    start(inThePage(), first.listener)
    engine.breaksAtTheStart(new Error('The browser gave no picture.'))
    expect(() => start(inThePage(), never.listener)).toThrow('The browser gave no picture.')

    expect(() => {
      engine.draws(1)
    }).toThrow(noSuchEngine(1, 1))
    engine.draws(0)

    expect([first.heard.drawn, never.heard.drawn]).toEqual([1, 0])
  })

  it('keeps to itself whom its engines say things to: two stand-ins share nothing', async () => {
    const one = await hasArrived()
    const other = await hasArrived()
    const { heard, listener } = somebody()
    one.start(inThePage(), listener)

    expect(() => {
      other.engine.draws()
    }).toThrow(noSuchEngine(0, 0))
    expect(heard.drawn).toBe(0)
  })
})
