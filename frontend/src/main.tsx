import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App.tsx'
import './styles/tokens.css'
import './styles/base.css'

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error('MotoSphere could not start: the page has no element with id "root".')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
