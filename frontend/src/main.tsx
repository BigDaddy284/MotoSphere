import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App.tsx'
import { tellTheEngineWhereItsFilesAre } from './globe/engineAddress.ts'
import './styles/tokens.css'
import './styles/base.css'

// Before anything is shown: the globe may be the first thing to ask.
tellTheEngineWhereItsFilesAre()

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('MotoSphere could not start: the page has no element with id "root".')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

async function spike(): Promise<void> {
  const times: Record<string, number> = { importAsked: performance.now() }
  Object.assign(globalThis, { spikeTimes: times })
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      times['longTasks'] = (times['longTasks'] ?? 0) + 1
      times['longTaskMs'] = (times['longTaskMs'] ?? 0) + entry.duration
      times['longestTask'] = Math.max(times['longestTask'] ?? 0, entry.duration)
    }
  }).observe({ type: 'longtask', buffered: true })
  const { start } = await import('./globe/spike.ts')
  times['imported'] = performance.now()
  const stage = document.querySelector('main')
  if (stage !== null) {
    start(stage, times)
  }
}

if (globalThis.location.search.includes('spike')) {
  void spike()
}
