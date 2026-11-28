// First of all: this has to be in place before React is loaded.
import { endEveryTestSettled, reactsWork } from './reactsWork.ts'
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeEach } from 'vitest'
import { installScreen } from './screen.ts'

// The test environment has no screen. Every test starts with a wide one.
beforeEach(() => {
  installScreen()
})

// After each test: unmount everything it rendered and forget what it
// stored, so the next test starts from an empty document and an empty
// session. Then React does what it was asked for and has not done yet, so
// that no test ends with work of the page waiting (reactsWork.ts).
endEveryTestSettled(reactsWork, { afterEach, afterAll }, () => {
  cleanup()
  window.sessionStorage.clear()
})
