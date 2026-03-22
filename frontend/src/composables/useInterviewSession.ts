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
  const isInterviewEnded = ref(false)
  const pollingInterval = ref<number | null>(null)
  const isAutoGenerating = ref(false)

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

  const checkInterviewEnd = async () => {
    if (!interview.value) return false
    
    if (interview.value.status !== 'completed') {
      return false
    }
    
    const rounds = await fetchRounds()
    if (!rounds || rounds.length === 0) {
      return false
    }
    
    const maxRoundNumber = Math.max(...rounds.map((r: any) => r.round_number))
    const lastRound = rounds.find((r: any) => r.round_number === maxRoundNumber)
    
    if (!lastRound) {
      return false
    }
    
    if (lastRound.user_answer === '1') {
      return false
    }
    
    return maxRoundNumber === interview.value.total_rounds
  }

  const getNextQuestion = async () => {
    isWaitingForQuestion.value = true
    
    try {
      const rounds = await fetchRounds()
      
      if (!rounds || rounds.length === 0) {
        // 没有轮次，启动问题生成
        await startQuestionGeneration()
        return
      }
      
      const unansweredRound = rounds.find((r: any) => {
        // 查找未回答的问题：
        // 1. user_answer 是 '1'（占位符）
        // 2. user_answer 是空字符串或 null（问题已生成但未回答）
        return r.user_answer === '1' || !r.user_answer || r.user_answer === ''
      })
      
      if (unansweredRound) {
        currentRound.value = unansweredRound
        addQuestionMessage(unansweredRound)
        isWaitingForQuestion.value = false
        stopPolling()
        return
      }
      
      const interviewEnded = await checkInterviewEnd()
      if (interviewEnded) {
        isInterviewEnded.value = true
        addSystemMessage('面试已结束！感谢您的参与。')
        isWaitingForQuestion.value = false
        stopPolling()
        return
      }
      
      // 没有未回答的问题，但面试未结束，等待后端生成
      if (messages.value[messages.value.length - 1]?.content !== '⏳ 问题还在生成中，请稍候...') {
        addSystemMessage('⏳ 问题还在生成中，请稍候...')
      }
      startPolling()
      
    } catch (err) {
      console.error('获取下一题失败:', err)
      addSystemMessage('获取题目失败，请稍后重试')
      isWaitingForQuestion.value = false
    }
  }

  const startQuestionGeneration = async (): Promise<boolean> => {
    if (isAutoGenerating.value) {
      console.log('Already auto generating, returning')
      return false
    }
    isAutoGenerating.value = true
    
    addSystemMessage('正在启动问题生成...')
    
    try {
      const interviewId = route.params.id as string
      console.log('Calling next-question API for interview:', interviewId)
      const response = await fetch(`${API_BASE_URL}/api/v1/interviews/${interviewId}/next-question/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({})
      })
      
      console.log('next-question response status:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('next-question response data:', data)
        if (data.code === 201) {
          // 问题生成成功，自动提交回答 "1"
          const roundId = data.data.round_id
          console.log('Question generated, roundId:', roundId, 'calling submitAutoAnswer')
          await submitAutoAnswer(roundId)
          return true
        } else if (data.code === 200) {
          // ，没有下一题了
          isWaitingForQuestion.value = false
          isAutoGenerating.value = false
          return false
        } else {
          addSystemMessage(data.message || '启动问题生成失败')
          isWaitingForQuestion.value = false
          isAutoGenerating.value = false
          return false
        }
      } else {
        // 读取错误响应
        const errorData = await response.json().catch(() => ({ message: '未知错误' }))
        console.error('next-question error:', errorData)
        addSystemMessage(errorData.message || '启动问题生成失败，请稍后重试')
        isWaitingForQuestion.value = false
        isAutoGenerating.value = false
        return false
      }
    } catch (err) {
      console.error('启动问题生成失败:', err)
      addSystemMessage('启动问题生成失败，请稍后重试')
      isWaitingForQuestion.value = false
      isAutoGenerating.value = false
      return false
    }
  }

  const submitAutoAnswer = async (roundId: number) => {
    console.log('submitAutoAnswer called, roundId:', roundId, 'interview.value:', interview.value)
    if (!interview.value) {
      console.log('interview.value is null, returning')
      return
    }
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/interviews/${interview.value.id}/rounds/${roundId}/answer/`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ user_answer: '1' })
        }
      )
      
      console.log('submitAutoAnswer response status:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('submitAutoAnswer response data:', data)
        if (data.code === 200) {
          console.log('自动回答提交成功，准备调用 startQuestionGeneration')
          // 自动回答提交成功，继续生成下一个问题
          // 先重置状态，然后调用 startQuestionGeneration
          isAutoGenerating.value = false
          const hasNext = await startQuestionGeneration()
          if (!hasNext) {
            // 没有下一题了，停止自动生成
            console.log('No more questions, stopping auto generation')
            addSystemMessage('所有问题已生成完毕，请开始作答')
          }
        } else {
          console.error('自动提交回答失败:', data.message)
          isAutoGenerating.value = false
          addSystemMessage('问题生成中断，请刷新页面重试')
        }
      } else {
        // 读取错误响应
        const errorData = await response.json().catch(() => ({ message: '未知错误' }))
        console.error('submitAutoAnswer error:', errorData)
        isAutoGenerating.value = false
        addSystemMessage(errorData.message || '问题生成中断，请刷新页面重试')
      }
    } catch (err) {
      console.error('自动提交回答失败:', err)
      isAutoGenerating.value = false
      addSystemMessage('问题生成中断，请刷新页面重试')
    }
  }

  const submitAnswer = async (answer: string) => {
    if (!answer.trim() || isSubmitting.value || !currentRound.value) return false
    
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
          
          // 检查是否是最后一轮
          const rounds = await fetchRounds()
          if (rounds && rounds.length > 0) {
            const maxRoundNumber = Math.max(...rounds.map((r: any) => r.round_number))
            const currentRoundNumber = data.data.round_number
            
            if (currentRoundNumber === maxRoundNumber) {
              // 是最后一轮，调用 PATCH 接口设置面试状态为 completed
              const patchResponse = await fetch(
                `${API_BASE_URL}/api/v1/interviews/${interview.value.id}/`,
                {
                  method: 'PATCH',
                  headers: getAuthHeaders(),
                  body: JSON.stringify({ status: 'completed' })
                }
              )
              
              if (patchResponse.ok) {
                const patchData = await patchResponse.json()
                if (patchData.code === 200) {
                  interview.value = patchData.data
                  isInterviewEnded.value = true
                  addSystemMessage('面试已结束！感谢您的参与。')
                  stopPolling()
                  return true
                }
              }
            }
          }
          
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
        addSystemMessage('网络错误，请稍后重试')
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
    messages.value.push({
      type: 'user',
      content,
      time: new Date().toLocaleTimeString()
    })
    scrollToBottom()
  }

  const addWaitingMessage = () => {
    messages.value.push({
      type: 'system',
      content: '⏳ 生成中，请稍候...'
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

    // 过滤出已回答的轮次（user_answer 不是 '1'）并按轮次号排序
    const answeredRounds = rounds
      .filter((r: any) => r.user_answer && r.user_answer !== '1')
      .sort((a: any, b: any) => a.round_number - b.round_number)

    for (const round of answeredRounds) {
      // 添加问题消息
      addQuestionMessage(round)
      
      // 添加用户回答消息
      if (round.user_answer && round.user_answer !== '1') {
        messages.value.push({
          type: 'user',
          content: round.user_answer,
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
    isInterviewEnded,
    isAutoGenerating,
    
    fetchInterviewDetail,
    getNextQuestion,
    submitAnswer,
    startPolling,
    stopPolling,
    addWelcomeMessage,
    loadHistoryMessages,
    statusText
  }
}
