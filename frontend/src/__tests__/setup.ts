import '@testing-library/jest-dom'
import { vi } from 'vitest'

// ============================================================
// Mock localStorage（jsdom 环境使用原生实现）
// ============================================================
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
})

// ============================================================
// Mock Vant UI（避免组件注册警告）
// ============================================================
vi.mock('vant', () => ({
  showToast: vi.fn(),
  showNotify: vi.fn(),
  showDialog: vi.fn(),
  showLoadingToast: vi.fn(),
  closeToast: vi.fn(),
}))

// ============================================================
// Mock axios（在需要真实请求的测试中可 unmock）
// ============================================================
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))
