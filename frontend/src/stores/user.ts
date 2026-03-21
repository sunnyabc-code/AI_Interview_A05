import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useUserStore = defineStore('user', () => {
  const userInfo = ref({
    userId: 0 as number,
    nickname: '',
    token: '',
  });

  function setUser(payload: { userId: number; nickname?: string; token: string }) {
    userInfo.value.userId = payload.userId;
    userInfo.value.nickname = payload.nickname || '';
    userInfo.value.token = payload.token;
    localStorage.setItem('token', payload.token);
    localStorage.setItem('userId', String(payload.userId));
  }

  function loadFromStorage() {
    const t = localStorage.getItem('token');
    const uid = localStorage.getItem('userId');
    if (t) userInfo.value.token = t;
    if (uid) userInfo.value.userId = parseInt(uid, 10) || 0;
  }

  return { userInfo, setUser, loadFromStorage };
});
