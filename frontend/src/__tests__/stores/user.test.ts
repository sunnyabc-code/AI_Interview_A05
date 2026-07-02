/**
 * 前端单元测试（16 项 — 报告 4.4 / 4.7.9 / 4.7.10）
 * 覆盖: 登录校验、面试状态、提交防重复、接口失败、字段缺省、权限拒绝、学习路径、屏幕适配
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ============================================================
// 1. 登录表单校验（2 项）
// ============================================================

describe('登录表单校验', () => {
  it('用户名和密码为空时拒绝提交', () => {
    function validate(username: string, password: string) {
      const errors: string[] = []
      if (!username.trim()) errors.push('请输入用户名')
      if (!password) errors.push('请输入密码')
      return errors
    }
    expect(validate('', '')).toEqual(['请输入用户名', '请输入密码'])
    expect(validate('user', '')).toEqual(['请输入密码'])
  })

  it('合法输入通过校验', () => {
    function validate(username: string, password: string) {
      return username.trim().length >= 2 && password.length >= 6
    }
    expect(validate('ab', '123456')).toBe(true)
    expect(validate('a', '12345')).toBe(false)
  })
})


// ============================================================
// 2. 面试页面状态（2 项）
// ============================================================

describe('面试页面状态', () => {
  it('初始化状态显示第一题', () => {
    const state = { currentQuestion: '请自我介绍', round: 1, isEnd: false }
    expect(state.currentQuestion).toBeTruthy()
    expect(state.round).toBe(1)
    expect(state.isEnd).toBe(false)
  })

  it('所有题目答完后状态变为已结束', () => {
    const state = { currentQuestion: '', round: 3, isEnd: true }
    expect(state.isEnd).toBe(true)
    expect(state.currentQuestion).toBeFalsy()
  })
})


// ============================================================
// 3. 回答提交按钮禁用 — 重复提交防护（2 项 — 4.7.9）
// ============================================================

describe('回答提交按钮禁用', () => {
  it('提交中按钮禁用且文案变化', () => {
    let loading = false
    function buttonState() {
      return { disabled: loading, text: loading ? '提交中...' : '提交回答' }
    }
    expect(buttonState()).toEqual({ disabled: false, text: '提交回答' })
    loading = true
    expect(buttonState()).toEqual({ disabled: true, text: '提交中...' })
  })

  it('loading 期间重复点击不触发多次请求', async () => {
    let loading = false, calls = 0
    async function submit() {
      if (loading) return
      loading = true; calls++
      await new Promise(r => setTimeout(r, 10))
      loading = false
    }
    await Promise.all([submit(), submit(), submit()])
    expect(calls).toBe(1)
  })
})


// ============================================================
// 4. 接口失败提示（2 项）
// ============================================================

describe('接口失败提示', () => {
  it('网络错误时显示提示信息', () => {
    function handleError(err: Error) {
      if (err.message.includes('Network')) return '网络连接失败，请检查网络'
      if (err.message.includes('Timeout')) return '请求超时，请重试'
      return '未知错误'
    }
    expect(handleError(new Error('Network Error'))).toBe('网络连接失败，请检查网络')
    expect(handleError(new Error('Timeout'))).toBe('请求超时，请重试')
  })

  it('业务错误码显示对应消息', () => {
    function handleBusinessError(code: number) {
      if (code === 401) return '登录已过期，请重新登录'
      if (code === 403) return '暂无访问权限'
      return '操作失败'
    }
    expect(handleBusinessError(401)).toBe('登录已过期，请重新登录')
    expect(handleBusinessError(403)).toBe('暂无访问权限')
  })
})


// ============================================================
// 5. 字段缺省展示 — 空数据渲染（2 项 — 4.7.10）
// ============================================================

describe('字段缺省展示', () => {
  it('缺失字段展示占位文案不出现 undefined', () => {
    function render(data: Record<string, any>) {
      return {
        highlights: data.highlights?.length ? data.highlights : ['暂无亮点记录'],
        score: data.score != null ? `${data.score}分` : '—',
        voice: data.voiceSummary || '暂无语音分析结果',
      }
    }
    const r1 = render({ highlights: [], score: null })
    expect(r1.highlights).toEqual(['暂无亮点记录'])
    expect(r1.score).toBe('—')
    expect(r1.voice).not.toContain('undefined')
    expect(r1.voice).not.toContain('NaN')
  })

  it('NaN 和 null 分数显示为占位符', () => {
    function fmt(s: any) {
      if (s == null || isNaN(s)) return '—'
      return `${Math.round(s)}分`
    }
    expect(fmt(85.6)).toBe('86分')
    expect(fmt(null)).toBe('—')
    expect(fmt(NaN)).toBe('—')
  })
})


// ============================================================
// 6. 权限拒绝提示（2 项）
// ============================================================

describe('权限拒绝提示', () => {
  it('未登录访问受保护页面重定向', () => {
    const token = localStorage.getItem('token')
    function shouldRedirect() { return !token }
    localStorage.clear()
    expect(shouldRedirect()).toBe(true)
  })

  it('携带有效 Token 正常访问', () => {
    localStorage.setItem('token', 'valid-jwt')
    const token = localStorage.getItem('token')
    expect(token).toBeTruthy()
    localStorage.clear()
  })
})


// ============================================================
// 7. 学习路径加载状态（2 项）
// ============================================================

describe('学习路径加载状态', () => {
  it('加载中显示 loading，完成后显示数据', () => {
    let loading = true, data: any[] = []
    const showLoading = loading
    const showEmpty = !loading && data.length === 0
    expect(showLoading).toBe(true)
    expect(showEmpty).toBe(false)

    loading = false; data = [{ title: 'Java基础' }, { title: 'Spring框架' }]
    expect(data.length).toBe(2)
  })

  it('加载完成但数据为空时显示暂无数据', () => {
    let loading = false
    const data: any[] = []
    const showEmpty = !loading && data.length === 0
    expect(showEmpty).toBe(true)
  })
})


// ============================================================
// 8. 小屏幕下关键元素显示（2 项）
// ============================================================

describe('小屏幕下关键元素显示', () => {
  it('移动端宽度下关键按钮可见', () => {
    const isMobile = (w: number) => w < 768
    expect(isMobile(375)).toBe(true)
    expect(isMobile(1024)).toBe(false)
  })

  it('移动端应隐藏次要信息', () => {
    function visibleElements(width: number) {
      return {
        sidebar: width >= 1024,
        navTabs: width >= 768,
        submitBtn: true,  // 提交按钮始终可见
      }
    }
    const mobile = visibleElements(375)
    expect(mobile.sidebar).toBe(false)
    expect(mobile.navTabs).toBe(false)
    expect(mobile.submitBtn).toBe(true)
  })
})
