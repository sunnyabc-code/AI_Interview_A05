<template>
  <div class="page">
    <van-nav-bar title="评估报告" left-arrow @click-left="$router.push('/scenarios')" fixed placeholder />
    <div v-if="loading" class="loading"><van-loading vertical>加载中…</van-loading></div>
    <div v-else-if="report" class="body">
      <div class="score">{{ report.totalScore }}</div>
      <p class="sub">综合得分（规则聚合）</p>
      <van-cell-group inset>
        <van-cell title="技术" :value="String(report.technicalScore ?? '-')" />
        <van-cell title="项目" :value="String(report.projectScore ?? '-')" />
        <van-cell title="场景" :value="String(report.scenarioScore ?? '-')" />
      </van-cell-group>
      <van-collapse v-model="active">
        <van-collapse-item title="亮点" name="1">
          <van-tag v-for="(t, i) in report.strengths || []" :key="i" type="success" style="margin: 4px">{{ t }}</van-tag>
        </van-collapse-item>
        <van-collapse-item title="改进建议" name="2">
          <div v-for="(s, i) in report.suggestions || []" :key="i" class="sug">{{ s.action }}</div>
        </van-collapse-item>
      </van-collapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { getReport } from '@/api';

const route = useRoute();
const sessionId = route.params.sessionId as string;
const loading = ref(true);
const report = ref<any>(null);
const active = ref(['1', '2']);

onMounted(async () => {
  try {
    report.value = await getReport({ sessionId });
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
}
.loading {
  padding-top: 80px;
  text-align: center;
}
.body {
  padding: 16px;
}
.score {
  text-align: center;
  font-size: 44px;
  font-weight: bold;
  color: #1989fa;
}
.sub {
  text-align: center;
  color: #666;
  margin-bottom: 16px;
}
.sug {
  margin-bottom: 8px;
  font-size: 14px;
}
</style>
