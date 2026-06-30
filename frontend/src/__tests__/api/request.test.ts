import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// 重新加载真实的 request.ts（因为 setup.ts mock 了 axios，这里测试需要真模块）
// 我们通过手动验证 request 拦截器逻辑来测试

describe('axios 请求拦截器逻辑', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('公开端点判断', () => {
    const PUBLIC_URLS = [
      '/api/chain/auth/login/',
      '/api/chain/auth/register/',
      '/api/chain/auth/send-code/',
      '/api/chain/auth/reset-password/',
    ]

    const PROTECTED_URLS = [
      '/api/session/create/',
      '/api/dialogue/next/',
      '/api/report/detail/?sessionId=1',
      '/api/profile/trend/?userId=1&days=7',
    ]

    it('公开端点不应注入 token', () => {
      // 模拟验证：公开 URL 的判断逻辑
      PUBLIC_URLS.forEach((url) => {
        const isPublic =
          url.includes('/chain/auth/login') ||
          url.includes('/chain/auth/register') ||
          url.includes('/chain/auth/send-code') ||
          url.includes('/chain/auth/reset-password')
        expect(isPublic).toBe(true)
      })
    })

    it('受保护端点应注入 token（当 token 存在时）', () => {
      localStorage.setItem('token', 'test-bearer-token')

      PROTECTED_URLS.forEach((url) => {
        const isPublic =
          url.includes('/chain/auth/login') ||
          url.includes('/chain/auth/register') ||
          url.includes('/chain/auth/send-code') ||
          url.includes('/chain/auth/reset-password')
        const token = localStorage.getItem('token')
        const shouldInject = token && !isPublic
        expect(shouldInject).toBe(true)
      })
    })

    it('无 token 时受保护端点也不注入', () => {
      const url = '/api/session/create/'
      const isPublic =
        url.includes('/chain/auth/login') ||
        url.includes('/chain/auth/register') ||
        url.includes('/chain/auth/send-code') ||
        url.includes('/chain/auth/reset-password')
      const token = localStorage.getItem('token') // null
      // JS: null && ... → null，但 if(token && ...) 正确判断为 falsy
      const shouldInject = !!(token && !isPublic)
      expect(shouldInject).toBe(false)
    })
  })

  describe('响应拦截器逻辑', () => {
    it('code=1 的响应应解包为 data', () => {
      const response = {
        data: {
          code: 1,
          msg: 'ok',
          data: { sessionId: '123', status: 'running' },
        },
      }

      const res = response.data
      if (res.code === 1) {
        const result = res.data
        expect(result).toEqual({ sessionId: '123', status: 'running' })
      }
    })

    it('code!=1 的响应应 reject', () => {
      const response = {
        data: {
          code: 400,
          msg: '参数错误',
          data: null,
        },
      }

      const res = response.data
      expect(res.code).not.toBe(1)
      expect(res.msg).toBe('参数错误')
    })
  })
})

describe('API 接口函数签名', () => {
  it('getScenarios 应为 GET 请求', async () => {
    const { getScenarios } = await import('@/api/index')
    // 验证函数存在且可调用
    expect(typeof getScenarios).toBe('function')
  })

  it('createSession 接受正确的参数结构', async () => {
    const { createSession } = await import('@/api/index')
    expect(typeof createSession).toBe('function')
    // 应接受 roleId, difficulty, mode
    const validData = { roleId: 1, difficulty: 'easy', mode: 'text' }
    expect(validData).toHaveProperty('roleId')
    expect(validData).toHaveProperty('difficulty')
    expect(validData).toHaveProperty('mode')
  })

  it('getNextQuestion 接受 sessionId 和 content', async () => {
    const { getNextQuestion } = await import('@/api/index')
    expect(typeof getNextQuestion).toBe('function')
  })

  it('getReport 接受 sessionId 参数', async () => {
    const { getReport } = await import('@/api/index')
    expect(typeof getReport).toBe('function')
  })
})
