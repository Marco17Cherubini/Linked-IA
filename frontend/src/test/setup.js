import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Senza `globals` di Vitest, Testing Library non smonta da sola i componenti tra i test.
afterEach(() => cleanup())

// jsdom non implementa ResizeObserver, usato dai contenitori responsive dei grafici.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver || ResizeObserverStub
