<template>
  <div class="page">
    <van-nav-bar title="选择岗位" fixed placeholder>
      <template #right>
        <van-icon name="manager-o" size="20" color="#1989fa" @click="$router.push('/profile')" />
      </template>
    </van-nav-bar>
    <div class="pad">
      <div v-for="item in scenarios" :key="item.roleId" class="card" @click="open(item)">
        <div class="row">
          <span class="title">{{ item.title }}</span>
          <van-tag type="primary">{{ item.category }}</van-tag>
        </div>
        <p class="desc">{{ item.description }}</p>
      </div>
    </div>
    <van-action-sheet v-model:show="show" title="训练配置">
      <div class="sheet">
        <van-radio-group v-model="difficulty">
          <van-cell title="入门 easy" clickable @click="difficulty = 'L1'"><template #right-icon><van-radio name="L1" /></template></van-cell>
          <van-cell title="进阶 medium" clickable @click="difficulty = 'L2'"><template #right-icon><van-radio name="L2" /></template></van-cell>
          <van-cell title="高压 hard" clickable @click="difficulty = 'L3'"><template #right-icon><van-radio name="L3" /></template></van-cell>
        </van-radio-group>
        <van-button type="primary" block round :loading="creating" class="btn" @click="start">开始模拟面试</van-button>
      </div>
    </van-action-sheet>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import { getScenarios, createSession } from '@/api';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();
const scenarios = ref<any[]>([]);
const show = ref(false);
const current = ref<any>({});
const difficulty = ref('L1');
const creating = ref(false);

onMounted(async () => {
  userStore.loadFromStorage();
  if (!userStore.userInfo.token) {
    router.push('/login');
    return;
  }
  try {
    scenarios.value = (await getScenarios()) as any;
  } catch {
    showToast('加载岗位失败');
  }
});

const open = (item: any) => {
  current.value = item;
  difficulty.value = 'L1';
  show.value = true;
};

const start = async () => {
  creating.value = true;
  try {
    const uid = userStore.userInfo.userId;
    if (!uid) {
      showToast('请先登录');
      router.push('/login');
      return;
    }
    const res: any = await createSession({
      userId: uid,
      roleId: current.value.roleId || current.value.templateId,
      difficulty: difficulty.value,
      mode: 'text',
    });
    show.value = false;
    router.push(`/training/${res.sessionId}`);
  } catch {
    /* toast */
  } finally {
    creating.value = false;
  }
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f8fa;
}
.pad {
  padding: 16px;
}
.card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}
.row {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
}
.desc {
  font-size: 13px;
  color: #666;
  margin-top: 8px;
}
.sheet {
  padding: 16px;
}
.btn {
  margin-top: 16px;
}
</style>
