import { ref, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const API_BASE_URL = 'http://localhost:8000'

export function useInterviewSession() {
  const route = useRoute()
  const router = useRouter()

  const interview = ref<any>(null)
  const messages = ref<any[]>([])
  const currentRound = ref<any>(null)
  const isSubmitting = ref(false)
  const isWaitingForQuestion = ref(false)
  /** 正在结束面试（拉取最后一题结果或调用结束接口），用于全屏加载层 */
  const isClosingInterview = ref(false)
  const isInterviewEnded = ref(false)
  const isPaused = ref(false)
  const pollingInterval = ref<number | null>(null)
  const countdownSeconds = ref(5)
  const showCountdown = ref(false)
  const countdownInterval = ref<number | null>(null)
  const VOICE_PLACEHOLDER_ANSWER = '1'

  /** 获取下一题时：仅空回答视为未作答；语音占位「1」允许继续推进 */
  const isEffectiveUserAnswer = (userAnswer: unknown) => {
    const s = String(userAnswer ?? '').trim()
    if (!s) return false
    return true
  }

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token')
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  }

  const fetchInterviewDetail = async () => {
    const interviewId = route.params.id as string
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/`, {
        headers: getAuthHeaders()
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 200) {
          interview.value = data.data
          isPaused.value = data.data.status === 'paused'
          isInterviewEnded.value = data.data.status === 'completed'
          return data.data
        } else {
          throw new Error(data.message || '获取面试详情失败')
        }
      } else if (response.status === 401) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        router.push('/auth')
        throw new Error('未授权')
      } else {
        throw new Error('网络错误，请稍后重试')
      }
    } catch (err) {
      throw err
    }
  }

  const fetchRounds = async () => {
    const interviewId = route.params.id as string
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/rounds/`, {
        headers: getAuthHeaders()
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 200) {
          return data.data || []
        }
      }
    } catch (err) {
      console.error('获取轮次列表失败:', err)
    }
    
    return []
  }

  const startInterview = async () => {
    const interviewId = route.params.id as string
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/start/`, {
        method: 'POST',
        headers: getAuthHeaders()
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 200) {
          interview.value = { ...interview.value, ...data.data }
          addWelcomeMessage()
          await getNextQuestion()
          return true
        } else {
          addSystemMessage(data.message || '开始面试失败')
          return false
        }
      } else {
        const errorData = await response.json().catch(() => ({ message: '未知错误' }))
        addSystemMessage(errorData.message || '开始面试失败')
        return false
      }
    } catch (err) {
      console.error('开始面试失败:', err)
      addSystemMessage('开始面试失败，请稍后重试')
      return false
    }
  }

  const pauseInterview = async () => {
    const interviewId = route.params.id as string
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/pause/`, {
        method: 'POST',
        headers: getAuthHeaders()
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 200) {
          interview.value = { ...interview.value, ...data.data }
          isPaused.value = true
          addSystemMessage('面试已暂停')
          return true
        } else {
          addSystemMessage(data.message || '暂停面试失败')
          return false
        }
      } else {
        const errorData = await response.json().catch(() => ({ message: '未知错误' }))
        addSystemMessage(errorData.message || '暂停面试失败')
        return false
      }
    } catch (err) {
      console.error('暂停面试失败:', err)
      addSystemMessage('暂停面试失败，请稍后重试')
      return false
    }
  }

  const resumeInterview = async () => {
    const interviewId = route.params.id as string
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/resume/`, {
        method: 'POST',
        headers: getAuthHeaders()
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 200) {
          interview.value = { ...interview.value, ...data.data }
          isPaused.value = false
          addSystemMessage('面试已恢复')
          getNextQuestion()
          return true
        } else {
          addSystemMessage(data.message || '恢复面试失败')
          return false
        }
      } else {
        const errorData = await response.json().catch(() => ({ message: '未知错误' }))
        addSystemMessage(errorData.message || '恢复面试失败')
        return false
      }
    } catch (err) {
      console.error('恢复面试失败:', err)
      addSystemMessage('恢复面试失败，请稍后重试')
      return false
    }
  }

  const endInterview = async () => {
    const interviewId = route.params.id as string
    isClosingInterview.value = true
    isWaitingForQuestion.value = true

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/end/`, {
        method: 'POST',
        headers: getAuthHeaders()
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 200) {
          interview.value = { ...interview.value, ...data.data }
          isInterviewEnded.value = true
          stopPolling()
          router.push(`/interview/${interviewId}/evaluation`)
          return true
        } else {
          addSystemMessage(data.message || '结束面试失败')
          return false
        }
      } else {
        const errorData = await response.json().catch(() => ({ message: '未知错误' }))
        addSystemMessage(errorData.message || '结束面试失败')
        return false
      }
    } catch (err) {
      console.error('结束面试失败:', err)
      addSystemMessage('结束面试失败，请稍后重试')
      return false
    } finally {
      isClosingInterview.value = false
      isWaitingForQuestion.value = false
    }
  }

  const getNextQuestion = async () => {
    if (isPaused.value || isInterviewEnded.value || isWaitingForQuestion.value) return
    
    isWaitingForQuestion.value = true
    
    try {
      const rounds = await fetchRounds()
      
      if (!rounds || rounds.length === 0) {
        // 没有轮次，生成第一个问题
        await generateNextQuestion()
        return
      }
      
      const unansweredRound = rounds.find(
        (r: any) => !isEffectiveUserAnswer(r.user_answer)
      )
      
      if (unansweredRound) {
        currentRound.value = unansweredRound
        addQuestionMessage(unansweredRound)
        isWaitingForQuestion.value = false
        stopPolling()
        return
      }

      // 当前已产生的轮次均已有效作答：由后端 next-question 判断是否还有下一题或结束面试（勿设 isClosingInterview，避免与追问链切换时误显示「结束面试」全屏层）
      await generateNextQuestion()
      
    } catch (err) {
      console.error('获取下一题失败:', err)
      addSystemMessage('获取题目失败，请稍后重试')
      isWaitingForQuestion.value = false
    }
  }

  const generateNextQuestion = async () => {
    isWaitingForQuestion.value = true
    addSystemMessage('⏳ 正在生成问题，请稍候...')
    
    try {
      const interviewId = route.params.id as string
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/next-question/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({})
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 201) {
          isClosingInterview.value = false
          const newRound = data.data
          currentRound.value = newRound
          addQuestionMessage(newRound)
          isWaitingForQuestion.value = false
        } else if (data.code === 200) {
          // 后端已在 next-question 内标记完成并打分，直接进评估页（勿再调 end 以免二次等待）
          currentRound.value = null
          interview.value = {
            ...interview.value,
            ...data.data,
            status: 'completed',
          }
          isInterviewEnded.value = true
          stopPolling()
          isWaitingForQuestion.value = false
          isClosingInterview.value = false
          router.push(`/interview/${interviewId}/evaluation`)
        } else {
          addSystemMessage(`生成问题失败: ${data.message || '未知错误'}`)
          currentRound.value = null
          isWaitingForQuestion.value = false
          isClosingInterview.value = false
        }
      } else {
        const errorData = await response.json().catch(() => ({ message: '服务器错误' }))
        addSystemMessage(`生成问题失败: ${errorData.message || '服务器错误'}`)
        currentRound.value = null
        isWaitingForQuestion.value = false
        isClosingInterview.value = false
      }
    } catch (err) {
      console.error('生成问题失败:', err)
      addSystemMessage('生成问题失败，请点击重试按钮')
      currentRound.value = null
      isWaitingForQuestion.value = false
      isClosingInterview.value = false
    }
  }

  const retryGenerateQuestion = async () => {
    if (
      !isInterviewEnded.value &&
      !isPaused.value &&
      !isWaitingForQuestion.value &&
      !isClosingInterview.value
    ) {
      await generateNextQuestion()
    }
  }

  const submitAnswer = async (answer: string) => {
    if (!answer.trim() || isSubmitting.value || !currentRound.value || isPaused.value) return false
    
    addUserMessage(answer)
    
    isSubmitting.value = true
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/interviews/${interview.value.id}/rounds/${currentRound.value.round_id}/answer/`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ user_answer: answer })
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        if (data.code === 200) {
          addSystemMessage('回答已提交')
          currentRound.value = null
          // 避免上一轮「等题目」状态阻塞后续拉题/结束流程
          isWaitingForQuestion.value = false

          // 获取下一个问题（由后端决定：新题或结束面试）
          await getNextQuestion()
          return true
        } else {
          addSystemMessage(data.message || '提交回答失败')
          return false
        }
      } else if (response.status === 401) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        router.push('/auth')
        return false
      } else {
        const errorData = await response.json().catch(() => ({ message: '未知错误' }))
        addSystemMessage(errorData.message || '网络错误，请稍后重试')
        return false
      }
    } catch (err) {
      console.error('提交回答失败:', err)
      addSystemMessage('网络错误，请稍后重试')
      return false
    } finally {
      isSubmitting.value = false
    }
  }

  const startCountdown = () => {
    showCountdown.value = true
    countdownSeconds.value = 5
    
    countdownInterval.value = window.setInterval(() => {
      countdownSeconds.value--
      if (countdownSeconds.value <= 0) {
        stopCountdown()
        addWelcomeMessage()
        getNextQuestion()
      }
    }, 1000)
  }

  const stopCountdown = () => {
    if (countdownInterval.value) {
      clearInterval(countdownInterval.value)
      countdownInterval.value = null
      showCountdown.value = false
    }
  }

  const startPolling = () => {
    if (pollingInterval.value) return
    
    pollingInterval.value = window.setInterval(async () => {
      await getNextQuestion()
    }, 3000)
  }

  const stopPolling = () => {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
  }

  const addSystemMessage = (content: string) => {
    messages.value.push({
      type: 'system',
      content
    })
    scrollToBottom()
  }

  const addQuestionMessage = (round: any) => {
    const categoryNames: Record<string, string> = {
      'technical': '技术知识题',
      'project': '项目经历题',
      'scenario': '场景题'
    }
    
    const categoryName = categoryNames[round.category] || round.category_name || '面试题'
    const questionLabel = round.followup_depth === 0 ? '主问题' : `第${round.followup_depth}次追问`
    
    messages.value.push({
      type: 'ai',
      content: `【${categoryName} - ${questionLabel}】\n\n${round.question_content}`,
      time: new Date().toLocaleTimeString()
    })
    scrollToBottom()
  }

  const addUserMessage = (content: string) => {
    const displayContent = content === VOICE_PLACEHOLDER_ANSWER ? '【语音回答】' : content
    messages.value.push({
      type: 'user',
      content: displayContent,
      time: new Date().toLocaleTimeString()
    })
    scrollToBottom()
  }

  const addWelcomeMessage = () => {
    messages.value.push({
      type: 'system',
      content: `面试开始！您正在参加 ${interview.value?.position_name} 岗位的${interview.value?.difficulty_name || ''}难度面试。`
    })
  }

  const loadHistoryMessages = async () => {
    const rounds = await fetchRounds()
    if (!rounds || rounds.length === 0) return

    // 过滤出已回答的轮次并按轮次号排序
    const answeredRounds = rounds
      .filter((r: any) => r.user_answer && r.user_answer !== '')
      .sort((a: any, b: any) => a.round_number - b.round_number)

    for (const round of answeredRounds) {
      // 添加问题消息
      addQuestionMessage(round)
      
      // 添加用户回答消息
      if (round.user_answer && round.user_answer !== '') {
        const displayContent = round.user_answer === VOICE_PLACEHOLDER_ANSWER
          ? '【语音回答】'
          : round.user_answer
        messages.value.push({
          type: 'user',
          content: displayContent,
          time: round.end_time ? new Date(round.end_time).toLocaleTimeString() : new Date().toLocaleTimeString()
        })
      }
    }
  }

  const scrollToBottom = async () => {
    await nextTick()
    const chatContainer = document.querySelector('.chat-messages')
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight
    }
  }

  const statusText = (status: string) => {
    const statusMap: Record<string, string> = {
      pending: '待开始',
      in_progress: '进行中',
      paused: '已暂停',
      completed: '已完成',
      cancelled: '已取消'
    }
    return statusMap[status] || status
  }

  return {
    interview,
    messages,
    currentRound,
    isSubmitting,
    isWaitingForQuestion,
    isClosingInterview,
    isInterviewEnded,
    isPaused,
    countdownSeconds,
    showCountdown,
    
    fetchInterviewDetail,
    startInterview,
    pauseInterview,
    resumeInterview,
    endInterview,
    getNextQuestion,
    generateNextQuestion,
    retryGenerateQuestion,
    submitAnswer,
    startPolling,
    stopPolling,
    addWelcomeMessage,
    loadHistoryMessages,
    statusText
  }
}
