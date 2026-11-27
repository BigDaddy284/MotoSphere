import { createRoot } from 'react-dom/client'
import { describe, expect, it } from 'vitest'
import {
  endEveryTestSettled,
  leftWaiting,
  REACTS_WORK,
  reactsWork,
  STILL_WAITING,
  TURNS,
  watchReactsWork,
} from './reactsWork.ts'
import type { Hooks, Host, Work } from './reactsWork.ts'

/**
 * A stand-in for the system: it runs what it is asked for a moment later,
 * in the order it was asked, and writes down the name of each piece. Like
 * the system, it runs what a piece asks for only after everything that was
 * asked for before.
 */
function standIn(): { host: Host; asked: string[]; own: Host['setImmediate'] } {
  const asked: string[] = []
  const own = (work: Work, ...given: unknown[]): unknown => {
    asked.push(work.name)
    setTimeout(() => {
      work(...given)
    }, 0)
    return `handle ${asked.length}`
  }
  return { host: { setImmediate: own }, asked, own }
}

/** A piece of work under the name React's scheduler gives its own. */
function ofReact(work: Work): Work {
  Object.defineProperty(work, 'name', { value: REACTS_WORK })
  return work
}

/** Lets everything run that the stand-in was asked for so far. */
async function aMoment(): Promise<void> {
  await new Promise<void>((resolve) => {
    setTimeout(resolve, 0)
  })
}

describe("the watch of React's work, over a stand-in for the system", () => {
  it('has a piece waiting from when React asks for it until it runs', async () => {
    const { host } = standIn()
    const watch = watchReactsWork(host)
    const ran: string[] = []

    host.setImmediate(ofReact(() => ran.push('first')))
    host.setImmediate(ofReact(() => ran.push('second')))

    expect(watch.waiting()).toBe(2)
    expect(ran).toEqual([])
    await aMoment()
    expect(ran).toEqual(['first', 'second'])
    expect(watch.waiting()).toBe(0)
  })

  it('does not count what somebody else asks for', async () => {
    const { host, asked } = standIn()
    const watch = watchReactsWork(host)
    let ran = 0

    host.setImmediate(function somethingElse() {
      ran += 1
    })
    host.setImmediate(() => {
      ran += 1
    })

    expect(watch.waiting()).toBe(0)
    await aMoment()
    expect(ran).toBe(2)
    expect(asked).toEqual(['somethingElse', ''])
  })

  it('hands on what the work is to be given, and hands back what the system answers', async () => {
    const { host } = standIn()
    watchReactsWork(host)
    const given: unknown[][] = []

    const first = host.setImmediate(
      ofReact((...all) => given.push(all)),
      'one',
      2,
    )
    const second = host.setImmediate((...all) => given.push(all), 'three')

    expect([first, second]).toEqual(['handle 1', 'handle 2'])
    await aMoment()
    expect(given).toEqual([['one', 2], ['three']])
  })

  it('no longer has a piece waiting that failed when it ran', async () => {
    const { host } = standIn()
    const watch = watchReactsWork(host)
    const failures: unknown[] = []
    // The stand-in runs the work the watch hands it; what that throws is
    // caught here, as the system would report it.
    const own = host.setImmediate
    host.setImmediate = (work, ...given) =>
      own(() => {
        try {
          work(...given)
        } catch (failure) {
          failures.push(failure)
        }
      })

    const later = watchReactsWork(host)
    host.setImmediate(
      ofReact(() => {
        throw new Error('the work failed')
      }),
    )

    expect([watch.waiting(), later.waiting()]).toEqual([0, 1])
    await aMoment()
    expect(failures).toEqual([new Error('the work failed')])
    expect(later.waiting()).toBe(0)
  })

  it('is settled at once when nothing is waiting, and asks the system for nothing', async () => {
    const { host, asked } = standIn()
    const watch = watchReactsWork(host)

    await watch.settled()

    expect(asked).toEqual([])
  })

  it('is settled only when the work has run, and the work that work asked for', async () => {
    const { host } = standIn()
    const watch = watchReactsWork(host)
    const ran: number[] = []
    const piece = (number: number): Work =>
      ofReact(() => {
        ran.push(number)
        if (number < 3) {
          host.setImmediate(piece(number + 1))
        }
      })

    host.setImmediate(piece(1))
    await watch.settled()

    expect(ran).toEqual([1, 2, 3])
    expect(watch.waiting()).toBe(0)
  })

  it(`lets the work run ${TURNS} times before it gives up`, async () => {
    const { host } = standIn()
    const watch = watchReactsWork(host)
    let ran = 0
    const piece: Work = ofReact(() => {
      ran += 1
      if (ran < TURNS) {
        host.setImmediate(piece)
      }
    })

    host.setImmediate(piece)
    await watch.settled()

    expect(ran).toBe(TURNS)
  })

  it('fails with a sentence when the work has still asked for more after that', async () => {
    const { host } = standIn()
    const watch = watchReactsWork(host)
    let ran = 0
    const piece: Work = ofReact(() => {
      ran += 1
      if (ran < TURNS + 1) {
        host.setImmediate(piece)
      }
    })

    host.setImmediate(piece)

    await expect(watch.settled()).rejects.toThrow(STILL_WAITING)
    expect(ran).toBe(TURNS)
    expect(watch.waiting()).toBe(1)
    expect(STILL_WAITING).toBe(
      'React still has work waiting after it was let run 100 times: something asks it for more work without end.',
    )
  })

  it('gives the system its own back when the file is over, with all it had on it', () => {
    const { host, own } = standIn()
    Object.assign(own, { mark: 'of the system' })

    const watch = watchReactsWork(host)
    expect(host.setImmediate).not.toBe(own)
    expect(host.setImmediate).toHaveProperty('mark', 'of the system')
    watch.close()

    expect(host.setImmediate).toBe(own)
  })

  it('fails with a sentence when the file is over and work is still waiting', () => {
    const { host, own } = standIn()
    const watch = watchReactsWork(host)
    host.setImmediate(ofReact(() => {}))
    host.setImmediate(ofReact(() => {}))

    expect(() => {
      watch.close()
    }).toThrow(leftWaiting(2))
    expect(host.setImmediate).toBe(own)
    expect(leftWaiting(2)).toBe(
      "The test file ends with 2 of React's work still waiting: it would run after the test's document is gone.",
    )
  })
})

/** A stand-in for the test runner: it keeps what it is handed, to be run by the test. */
function runner(): { hooks: Hooks; afterEach: (() => Promise<void>)[]; afterAll: (() => void)[] } {
  const afterEach: (() => Promise<void>)[] = []
  const afterAll: (() => void)[] = []
  return {
    hooks: {
      afterEach: (hook) => {
        afterEach.push(hook)
      },
      afterAll: (hook) => {
        afterAll.push(hook)
      },
    },
    afterEach,
    afterAll,
  }
}

describe('what the tests of a file are held to', () => {
  it('after each test, what the test left is put away and then React is let finish', async () => {
    const { host, own } = standIn()
    const watch = watchReactsWork(host)
    const { hooks, afterEach, afterAll } = runner()
    const happened: string[] = []
    endEveryTestSettled(watch, hooks, () => {
      happened.push(`put away, with ${watch.waiting()} waiting`)
    })
    expect([afterEach.length, afterAll.length]).toEqual([1, 1])

    host.setImmediate(ofReact(() => happened.push('React did its work')))
    expect(happened).toEqual([])
    await afterEach[0]?.()

    expect(happened).toEqual(['put away, with 1 waiting', 'React did its work'])
    expect(watch.waiting()).toBe(0)
    // The watch stays in place for the tests that follow.
    expect(host.setImmediate).not.toBe(own)
  })

  it('after each test, work that does not come to an end fails the test', async () => {
    const { host } = standIn()
    const watch = watchReactsWork(host)
    const { hooks, afterEach } = runner()
    endEveryTestSettled(watch, hooks, () => {})
    let ran = 0
    const piece: Work = ofReact(() => {
      ran += 1
      if (ran < TURNS + 1) {
        host.setImmediate(piece)
      }
    })

    host.setImmediate(piece)

    await expect(afterEach[0]?.()).rejects.toThrow(STILL_WAITING)
  })

  it('when the file is over, the watch is closed', () => {
    const { host, own } = standIn()
    const watch = watchReactsWork(host)
    const { hooks, afterAll } = runner()
    endEveryTestSettled(watch, hooks, () => {})
    expect(host.setImmediate).not.toBe(own)

    afterAll[0]?.()

    expect(host.setImmediate).toBe(own)
  })

  it('when the file is over and work is still waiting, the file fails', () => {
    const { host } = standIn()
    const watch = watchReactsWork(host)
    const { hooks, afterAll } = runner()
    endEveryTestSettled(watch, hooks, () => {})

    host.setImmediate(ofReact(() => {}))

    expect(() => afterAll[0]?.()).toThrow(leftWaiting(1))
  })
})

function emptyRoot(): HTMLElement {
  const root = document.createElement('div')
  document.body.append(root)
  return root
}

describe('the watch of the unit tests, with React itself', () => {
  it('sees the work React asks for when a page is started outside act, and lets it run', async () => {
    const root = emptyRoot()

    // Not inside `act`, as a test that forgets it would start a page.
    createRoot(root).render(<p>shown</p>)
    await Promise.resolve()

    // If this fails after an upgrade of React, React asks the system for
    // its work in another way, and the watch has to follow.
    expect(reactsWork.waiting()).toBe(1)
    expect(root).toBeEmptyDOMElement()

    await reactsWork.settled()

    expect(reactsWork.waiting()).toBe(0)
    expect(root).toHaveTextContent('shown')
    root.remove()
  })

  describe('at the end of a test', () => {
    const root = emptyRoot()

    it('a test may end with a page it started outside act still not shown', async () => {
      createRoot(root).render(<p>shown after the test</p>)
      await Promise.resolve()

      expect(reactsWork.waiting()).toBe(1)
      expect(root).toBeEmptyDOMElement()
    })

    it('and the set-up has let React show it before the next test begins', () => {
      expect(reactsWork.waiting()).toBe(0)
      expect(root).toHaveTextContent('shown after the test')
      root.remove()
    })
  })
})
