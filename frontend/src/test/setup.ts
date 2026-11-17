import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Unmount everything rendered by a test so the next test starts from an
// empty document.
afterEach(() => {
  cleanup()
})
