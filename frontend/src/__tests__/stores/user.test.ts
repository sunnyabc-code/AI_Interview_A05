import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

describe('UserStore', () => {
  beforeEach(() => {
    // 每个测试前重置 Pinia 和 localStorage
    setActivePinia(createPinia())
    localStorage.clear()
  })

  describe('setUser', () => {
    it('应该正确设置用户信息到 state', () => {
      const store = useUserStore()
      store.setUser({ userId: 42, nickname: '测试用户', token: 'jwt-token-123' })

      expect(store.userInfo.userId).toBe(42)
      expect(store.userInfo.nickname).toBe('测试用户')
      expect(store.userInfo.token).toBe('jwt-token-123')
    })

    it('nickname 为空时应设为空字符串', () => {
      const store = useUserStore()
      store.setUser({ userId: 1, token: 'token' })

      expect(store.userInfo.nickname).toBe('')
    })

    it('应该持久化 token 和 userId 到 localStorage', () => {
      const store = useUserStore()
      store.setUser({ userId: 99, token: 'abc-def-ghi' })

      expect(localStorage.getItem('token')).toBe('abc-def-ghi')
      expect(localStorage.getItem('userId')).toBe('99')
    })
  })

  describe('loadFromStorage', () => {
    it('应该从 localStorage 恢复登录态', () => {
      localStorage.setItem('token', 'saved-token')
      localStorage.setItem('userId', '7')

      const store = useUserStore()
      store.loadFromStorage()

      expect(store.userInfo.token).toBe('saved-token')
      expect(store.userInfo.userId).toBe(7)
    })

    it('localStorage 无数据时保持初始状态', () => {
      const store = useUserStore()
      store.loadFromStorage()

      expect(store.userInfo.userId).toBe(0)
      expect(store.userInfo.token).toBe('')
    })

    it('userId 解析失败时应为 0', () => {
      localStorage.setItem('userId', 'not-a-number')

      const store = useUserStore()
      store.loadFromStorage()

      expect(store.userInfo.userId).toBe(0)
    })

    it('仅恢复 token 而 userId 缺失时正确恢复', () => {
      localStorage.setItem('token', 'only-token')

      const store = useUserStore()
      store.loadFromStorage()

      expect(store.userInfo.token).toBe('only-token')
      expect(store.userInfo.userId).toBe(0)
    })
  })
})
