import axios from 'axios';
import { showToast } from 'vant';

const service = axios.create({
  baseURL: '',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

service.interceptors.request.use((config) => {
  const url = `${config.baseURL || ''}${config.url || ''}`;
  const isPublicAuth =
    url.includes('/chain/auth/login') ||
    url.includes('/chain/auth/register') ||
    url.includes('/chain/auth/send-code') ||
    url.includes('/chain/auth/reset-password');
  const token = localStorage.getItem('token');
  if (token && !isPublicAuth) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

service.interceptors.response.use(
  (response) => {
    const res = response.data;
    if (res.code !== 1) {
      showToast(res.msg || '请求失败');
      return Promise.reject(new Error(res.msg || 'Error'));
    }
    return res.data;
  },
  (error) => {
    showToast(error.message || '网络异常');
    return Promise.reject(error);
  }
);

export default service;
