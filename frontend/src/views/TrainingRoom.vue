<template>
  <div class="room">
    <van-nav-bar title="模拟面试" left-text="结束" @click-left="finish" fixed placeholder />
    <div class="chat" ref="chatRef">
      <div
        v-for="(m, i) in messages"
        :key="i"
        :class="['row', m.role === 'USER' ? 'right' : 'left']"
      >
        <div class="av">{{ m.role === 'USER' ? '我' : 'AI' }}</div>
        <div class="bubble">{{ m.content }}</div>
      </div>
      <div v-if="loading" class="row left">
        <div class="av">AI</div>
        <div class="bubble"><van-loading size="16px" /> 思考中…</div>
      </div>
    </div>
    <div class="input">
      <van-icon
        :name="mode === 'TEXT' ? 'volume-o' : 'comment-o'"
        size="26"
        color="#1989fa"
        style="margin-right: 8px"
        @click="mode = mode === 'TEXT' ? 'VOICE' : 'TEXT'"
      />
      <van-field
        v-if="mode === 'TEXT'"
        v-model="text"
        placeholder="输入回答"
        @keydown.enter.prevent="send"
      >
        <template #button>
          <van-button size="small" type="primary" :disabled="loading || !text" @click="send">发送</van-button>
        </template>
      </van-field>
      <div v-else class="voice">
        <van-button block type="primary" @click="showToast('语音请用浏览器录音扩展或先使用文本模式')">
          语音（演示）
        </van-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { showConfirmDialog, showToast } from 'vant';
import { getSessionState, getNextQuestion, submitEvaluation } from '@/api';

const route = useRoute();
const router = useRouter();
const sessionId = route.params.sessionId as string;
const messages = ref<{ role: string; content: string }[]>([]);
const text = ref('');
const loading = ref(false);
const chatRef = ref<HTMLElement | null>(null);
const mode = ref<'TEXT' | 'VOICE'>('TEXT');

const scroll = () =>
  nextTick(() => {
    if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;
  });

onMounted(async () => {
  try {
    const st: any = await getSessionState(sessionId);
    const q = st.openingQuestion || st.currentQuestion;
    if (q) messages.value.push({ role: 'AI', content: q });
  } catch {
    showToast('加载会话失败');
  }
});

const send = async () => {
  const c = text.value.trim();
  if (!c || loading.value) return;
  messages.value.push({ role: 'USER', content: c });
  text.value = '';
  loading.value = true;
  scroll();
  try {
    const res: any = await getNextQuestion({ sessionId, content: c });
    const ai = res.content || res.question || '';
    messages.value.push({ role: 'AI', content: ai });
    if (res.isEnd) {
      showToast('面试结束，正在跳转报告…');
      router.replace(`/report/${sessionId}`);
      return;
    }
  } catch {
    /* */
  } finally {
    loading.value = false;
    scroll();
  }
};

const finish = () => {
  showConfirmDialog({ title: '结束面试', message: '提前结束并生成报告？' })
    .then(async () => {
      await submitEvaluation({ sessionId });
      router.replace(`/report/${sessionId}`);
    })
    .catch(() => {});
};
</script>

<style scoped>
.room {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f7f8fa;
}
.chat {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  margin-top: 46px;
}
.row {
  display: flex;
  margin-bottom: 12px;
}
.left {
  justify-content: flex-start;
}
.right {
  justify-content: flex-end;
}
.av {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #ddd;
  text-align: center;
  line-height: 36px;
  font-size: 12px;
  flex-shrink: 0;
}
.left .av {
  margin-right: 8px;
  background: #1989fa;
  color: #fff;
}
.right .av {
  margin-left: 8px;
  background: #07c160;
  color: #fff;
  order: 2;
}
.bubble {
  max-width: 72%;
  padding: 10px 12px;
  background: #fff;
  border-radius: 8px;
  font-size: 15px;
  word-break: break-all;
}
.right .bubble {
  background: #95ec69;
}
.input {
  display: flex;
  align-items: center;
  padding: 8px;
  background: #fff;
  border-top: 1px solid #eee;
}
.voice {
  flex: 1;
}
</style>
