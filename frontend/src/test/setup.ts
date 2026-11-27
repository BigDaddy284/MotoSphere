import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'
import { installScreen } from './screen.ts'

// The test environment has no screen. Every test starts with a wide one.
beforeEach(() => {
  installScreen()
})

// Unmount everything rendered by a test and forget what it stored, so the
// next test starts from an empty document and an empty session.
afterEach(() => {
  cleanup()
  window.sessionStorage.clear()
})
