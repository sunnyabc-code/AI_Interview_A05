<template>
  <div class="page">
    <van-nav-bar title="我的" left-arrow @click-left="$router.back()" fixed placeholder />
    <van-cell-group inset title="能力趋势（近次）">
      <div v-if="trend.labels?.length" class="trend">
        <span v-for="(lb, i) in trend.labels" :key="i" class="trend-item">{{ lb }}: {{ trend.scores[i] }} 分</span>
      </div>
      <van-empty v-else description="完成模拟面试后展示" />
    </van-cell-group>
    <van-cell-group inset>
      <van-cell title="刷新历史" is-link @click="load" />
    </van-cell-group>
    <van-cell-group inset v-if="list.length" title="记录">
      <van-cell
        v-for="item in list"
        :key="item.sessionId"
        :title="item.scenario"
        :value="item.score + ' 分'"
        :label="item.completedAt"
        is-link
        @click="$router.push(`/report/${item.sessionId}`)"
      />
    </van-cell-group>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { getHistoryList, getGrowthTrend } from '@/api';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();
const list = ref<any[]>([]);
const trend = ref<{ labels: string[]; scores: number[] }>({ labels: [], scores: [] });

const load = async () => {
  const uid = userStore.userInfo.userId;
  if (!uid) {
    showToast('请先登录');
    router.push('/login');
    return;
  }
  try {
    const res: any = await getHistoryList({ userId: uid, page: 1, size: 20 });
    list.value = res.records || [];
    const tr: any = await getGrowthTrend({ userId: uid, days: 14 });
    trend.value = { labels: tr.labels || [], scores: tr.scores || [] };
  } catch {
    /* toast in interceptor */
  }
};

onMounted(() => {
  userStore.loadFromStorage();
  load();
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
  padding-top: 8px;
}
.trend {
  padding: 12px 16px;
  font-size: 13px;
  color: #323233;
  line-height: 1.8;
}
.trend-item {
  display: block;
}
</style>
