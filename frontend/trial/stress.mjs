// TRIAL ONLY (FND-054). Opens many connections from the browser of the
// browser tests to a server on this computer, in turns with the browser as
// Playwright starts it (A) and with one feature of the browser turned off
// (B), and counts the requests that fail and with what.
import http from 'node:http'
import { chromium } from '@playwright/test'

const FEATURE = 'TcpPortRandomizationWin'
const ROUNDS = Number(process.env.STRESS_ROUNDS ?? 2)
const PER_ROUND = Number(process.env.STRESS_PER_ROUND ?? 300)
const PER_SECOND = Number(process.env.STRESS_PER_SECOND ?? 50)

const ports = []
const server = http.createServer((request, response) => {
  if (request.url === '/') {
    response.writeHead(200, { 'Content-Type': 'text/html', Connection: 'close' })
    response.end('<!doctype html><title>stress</title>')
    return
  }
  ports.push(request.socket.remotePort)
  response.writeHead(200, {
    'Content-Type': 'text/plain',
    'Cache-Control': 'no-store',
    Connection: 'close',
  })
  response.end('ok')
})
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
const address = `http://127.0.0.1:${server.address().port}/`

/** The switches Playwright starts the browser with, given these options. */
async function switchesWith(options) {
  const started = await chromium.launchServer(options)
  const switches = started.process().spawnargs.filter((s) => s.startsWith('--disable-features='))
  await started.close()
  return switches
}

// What Playwright turns off by itself, read from a browser it started.
const defaults = await switchesWith({})
if (defaults.length !== 1) throw new Error(`expected one --disable-features, got ${defaults.length}`)
const [playwrightsOwn] = defaults
console.log(`Playwright's own switch: ${playwrightsOwn}`)

const variants = {
  A: {},
  B: { ignoreDefaultArgs: [playwrightsOwn], args: [`${playwrightsOwn},${FEATURE}`] },
}

for (const [name, options] of Object.entries(variants)) {
  console.log(`${name} starts the browser with: ${JSON.stringify(await switchesWith(options))}`)
}

async function round(name, number) {
  const browser = await chromium.launch(variants[name])
  if (number === 1) console.log(`browser ${browser.version()} on ${process.platform}`)
  const page = await browser.newPage()
  const failures = {}
  page.on('requestfailed', (request) => {
    const text = request.failure()?.errorText ?? 'unknown'
    failures[text] = (failures[text] ?? 0) + 1
  })
  await page.goto(address)
  ports.length = 0
  const started = Date.now()
  const failed = await page.evaluate(
    async ([count, perSecond]) => {
      let failed = 0
      const gap = 1000 / perSecond
      const start = performance.now()
      const jobs = []
      for (let i = 0; i < count; i++) {
        const wait = start + i * gap - performance.now()
        if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait))
        jobs.push(
          fetch(`/x?${i}`, { cache: 'no-store' })
            .then((response) => response.text())
            .catch(() => {
              failed += 1
            }),
        )
      }
      await Promise.all(jobs)
      return failed
    },
    [PER_ROUND, PER_SECOND],
  )
  const seconds = ((Date.now() - started) / 1000).toFixed(1)
  await browser.close()
  // How the browser's ports follow one another: next to the one before, or not.
  let next = 0
  for (let i = 1; i < ports.length; i++) {
    const step = ports[i] - ports[i - 1]
    if (step >= 1 && step <= 4) next += 1
  }
  const distinct = new Set(ports).size
  console.log(
    `${new Date().toISOString().slice(11, 19)} round ${number} ${name}: asked=${PER_ROUND} arrived=${ports.length} ` +
      `failed=${failed} ${JSON.stringify(failures)} in ${seconds}s ` +
      `ports: distinct=${distinct} next-to-the-one-before=${next} ` +
      `lowest=${Math.min(...ports)} highest=${Math.max(...ports)}`,
  )
  return { failed, failures, arrived: ports.length }
}

const totals = { A: { asked: 0, failed: 0, failures: {} }, B: { asked: 0, failed: 0, failures: {} } }
for (let number = 1; number <= ROUNDS; number++) {
  for (const name of ['A', 'B']) {
    const result = await round(name, number)
    totals[name].asked += PER_ROUND
    totals[name].failed += result.failed
    for (const [text, count] of Object.entries(result.failures)) {
      totals[name].failures[text] = (totals[name].failures[text] ?? 0) + count
    }
  }
}
server.close()
for (const name of ['A', 'B']) {
  console.log(`TOTAL ${name}: asked=${totals[name].asked} failed=${totals[name].failed} ${JSON.stringify(totals[name].failures)}`)
}
