// Interview types
export interface Interview {
    id: number
    name: string
    status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
    position_name: string
    difficulty_name?: string
    mode: 'text' | 'voice' | 'mixed'
    total_rounds: number
    created_at: string
    updated_at: string
}

// API Response types
export interface ApiResponse<T = unknown> {
    success: boolean
    data?: T
    message?: string
    errors?: Record<string, string[]>
}

// User types
export interface User {
    id: number
    username: string
    email: string
    [key: string]: unknown
}
