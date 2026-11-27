// TRIAL ONLY (FND-054). As the browser tests do it: a new browser context,
// one page with a few files, the context closed again, so that the browser
// is the side that closes its connections. In turns with the browser as
// Playwright starts it (A) and with one feature of the browser off (B).
import http from 'node:http'
import { chromium } from '@playwright/test'

const FEATURE = 'TcpPortRandomizationWin'
const ROUNDS = Number(process.env.STRESS_ROUNDS ?? 2)
const CONTEXTS = Number(process.env.STRESS_CONTEXTS ?? 40)
const PER_SECOND = Number(process.env.STRESS_PER_SECOND ?? 10)
const WORKERS = 8

const ports = []
let requests = 0
const server = http.createServer((request, response) => {
  requests += 1
  if (request.url === '/') {
    response.writeHead(200, { 'Content-Type': 'text/html', 'Cache-Control': 'no-store' })
    response.end(
      '<!doctype html><title>stress</title>' +
        [1, 2, 3, 4].map((n) => `<script src="/s${n}.js"></script>`).join(''),
    )
    return
  }
  response.writeHead(200, { 'Content-Type': 'text/javascript', 'Cache-Control': 'no-store' })
  response.end('// nothing\n')
})
server.on('connection', (socket) => ports.push(socket.remotePort))
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
const address = `http://127.0.0.1:${server.address().port}/`

/** The switches Playwright starts the browser with, given these options. */
async function switchesWith(options) {
  const started = await chromium.launchServer(options)
  const switches = started.process().spawnargs.filter((s) => s.startsWith('--disable-features='))
  await started.close()
  return switches
}

const defaults = await switchesWith({})
if (defaults.length !== 1) throw new Error(`expected one --disable-features, got ${defaults.length}`)
const [playwrightsOwn] = defaults
const variants = {
  A: {},
  B: { ignoreDefaultArgs: [playwrightsOwn], args: [`${playwrightsOwn},${FEATURE}`] },
}
for (const [name, options] of Object.entries(variants)) {
  console.log(`${name} starts the browser with: ${JSON.stringify(await switchesWith(options))}`)
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function round(name, number) {
  const browser = await chromium.launch(variants[name])
  if (number === 1) console.log(`browser ${browser.version()} on ${process.platform}`)
  const failures = {}
  const count = (text) => {
    failures[text] = (failures[text] ?? 0) + 1
  }
  let pages = 0
  let next = 0
  ports.length = 0
  requests = 0
  const started = Date.now()
  async function worker() {
    for (;;) {
      const i = next
      next += 1
      if (i >= CONTEXTS) return
      const wait = started + (i * 1000) / PER_SECOND - Date.now()
      if (wait > 0) await sleep(wait)
      const context = await browser.newContext()
      const page = await context.newPage()
      page.on('requestfailed', (request) => count(`file: ${request.failure()?.errorText ?? 'unknown'}`))
      try {
        await page.goto(address)
        pages += 1
      } catch (error) {
        count(`page: ${/net::ERR_[A-Z_]+/.exec(String(error))?.[0] ?? String(error).slice(0, 80)}`)
      }
      await context.close()
    }
  }
  await Promise.all(Array.from({ length: WORKERS }, worker))
  const seconds = ((Date.now() - started) / 1000).toFixed(1)
  await browser.close()
  let beside = 0
  for (let i = 1; i < ports.length; i++) {
    const step = ports[i] - ports[i - 1]
    if (step >= 1 && step <= 4) beside += 1
  }
  console.log(
    `${new Date().toISOString().slice(11, 19)} round ${number} ${name}: contexts=${CONTEXTS} pages-shown=${pages} ` +
      `connections=${ports.length} requests=${requests} failures=${JSON.stringify(failures)} in ${seconds}s ` +
      `ports: distinct=${new Set(ports).size} next-to-the-one-before=${beside}`,
  )
  return { connections: ports.length, pages, failures }
}

const totals = {}
for (const name of ['A', 'B']) totals[name] = { contexts: 0, pages: 0, connections: 0, failures: {} }
for (let number = 1; number <= ROUNDS; number++) {
  for (const name of ['A', 'B']) {
    const result = await round(name, number)
    totals[name].contexts += CONTEXTS
    totals[name].pages += result.pages
    totals[name].connections += result.connections
    for (const [text, n] of Object.entries(result.failures)) {
      totals[name].failures[text] = (totals[name].failures[text] ?? 0) + n
    }
  }
}
server.close()
server.closeAllConnections()
for (const name of ['A', 'B']) console.log(`TOTAL ${name}: ${JSON.stringify(totals[name])}`)
