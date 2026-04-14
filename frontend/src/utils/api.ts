export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001').replace(/\/$/, '')

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: any
  headers?: Record<string, string>
}

export const api = {
  async request(url: string, options: RequestOptions = {}) {
    const token = localStorage.getItem('access_token')
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const config: RequestInit = {
      method: options.method || 'GET',
      headers
    }
    
    if (options.body && options.method !== 'GET') {
      config.body = JSON.stringify(options.body)
    }
    
    const response = await fetch(`${API_BASE_URL}${url}`, config)
    return response.json()
  },
  
  get(url: string) {
    return this.request(url, { method: 'GET' })
  },
  
  post(url: string, body: any) {
    return this.request(url, { method: 'POST', body })
  },
  
  put(url: string, body: any) {
    return this.request(url, { method: 'PUT', body })
  },
  
  patch(url: string, body: any) {
    return this.request(url, { method: 'PATCH', body })
  },
  
  delete(url: string) {
    return this.request(url, { method: 'DELETE' })
  }
}

export default api
