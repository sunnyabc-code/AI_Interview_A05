import request from '@/utils/request';

export const login = (data: { username: string; password: string }) =>
  request({ url: '/api/chain/auth/login/', method: 'post', data });

export const register = (data: { username: string; password: string; email?: string }) =>
  request({ url: '/api/chain/auth/register/', method: 'post', data });

export const sendVerificationCode = (data: {
  target: string;
  send_type: 'email' | 'phone';
  purpose?: 'reset' | 'register';
}) => request({ url: '/api/chain/auth/send-code/', method: 'post', data });

export const resetPassword = (data: {
  identifier: string;
  verification_code: string;
  new_password: string;
  confirm_password: string;
  reset_type: 'email' | 'phone';
}) => request({ url: '/api/chain/auth/reset-password/', method: 'post', data });

export const getScenarios = () => request({ url: '/api/scenario/list/', method: 'get' });

export const createSession = (data: any) =>
  request({ url: '/api/session/create/', method: 'post', data });

export const getSessionState = (sessionId: string) =>
  request({ url: `/api/session/${sessionId}/state/`, method: 'get' });

export const getNextQuestion = (data: { sessionId: string; content?: string; userAnswer?: string }) =>
  request({ url: '/api/dialogue/next/', method: 'post', data });

export const submitEvaluation = (data: { sessionId: string }) =>
  request({ url: '/api/evaluation/submit/', method: 'post', data });

export const getReport = (params: { sessionId: string }) =>
  request({ url: '/api/report/detail/', method: 'get', params });

export const getGrowthTrend = (params: { userId: number; days: number }) =>
  request({ url: '/api/profile/trend/', method: 'get', params });

export const getHistoryList = (params: { userId: number; page?: number; size?: number }) =>
  request({ url: '/api/profile/history/', method: 'get', params });

