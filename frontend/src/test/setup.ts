import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Unmount everything rendered by a test and forget what it stored, so the
// next test starts from an empty document and an empty session.
afterEach(() => {
  cleanup()
  window.sessionStorage.clear()
})
