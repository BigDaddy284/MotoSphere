import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App.tsx'
import { tellTheEngineWhereItsFilesAre } from './globe/engineAddress.ts'
import type { Load } from './globe/Globe.tsx'
import './styles/tokens.css'
import './styles/base.css'

// Before anything is shown: the globe may be the first thing to ask.
tellTheEngineWhereItsFilesAre()

// The engine is large. It is fetched when the globe is shown and not with
// the page, so the top bar and the panels are there at once.
const loadTheEngine: Load = async () => {
  const { start } = await import('./globe/earth.ts')
  return start
}

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('MotoSphere could not start: the page has no element with id "root".')
}

createRoot(rootElement).render(
  <StrictMode>
    <App loadTheEngine={loadTheEngine} />
  </StrictMode>,
)
