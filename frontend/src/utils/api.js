const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiClient {
    constructor() {
        this.baseUrl = API_BASE_URL
    }

    getToken() {
        return localStorage.getItem('token')
    }

    setToken(token) {
        localStorage.setItem('token', token)
    }

    clearToken() {
        localStorage.removeItem('token')
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`
        const token = this.getToken()

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        }

        if (token) {
            headers['Authorization'] = `Bearer ${token}`
        }

        const response = await fetch(url, {
            ...options,
            headers,
        })

        if (!response.ok) {
            if (response.status === 401) {
                this.clearToken()
                window.location.href = '/login'
            }
            const error = await response.json().catch(() => ({ detail: 'An error occurred' }))
            throw new Error(error.detail || 'Request failed')
        }

        return response.json()
    }

    async register(email, password, fullName) {
        const data = await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, full_name: fullName }),
        })
        this.setToken(data.access_token)
        return data
    }

    async login(email, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        })
        this.setToken(data.access_token)
        return data
    }

    async getMe() {
        return this.request('/auth/me')
    }

    logout() {
        this.clearToken()
    }

    async getResolutions() {
        return this.request('/resolutions')
    }

    async createResolution(data) {
        return this.request('/resolutions', {
            method: 'POST',
            body: JSON.stringify(data),
        })
    }

    async negotiateResolution(data) {
        return this.request('/resolutions/negotiate', {
            method: 'POST',
            body: JSON.stringify(data),
        })
    }

    async getResolution(id) {
        return this.request(`/resolutions/${id}`)
    }

    async generateRoadmap(resolutionId) {
        return this.request(`/resolutions/${resolutionId}/generate-roadmap`, {
            method: 'POST',
        })
    }

    async getRoadmap(resolutionId) {
        return this.request(`/resolutions/${resolutionId}/roadmap`)
    }

    async updateMilestone(milestoneId, data) {
        return this.request(`/resolutions/milestones/${milestoneId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        })
    }

    async completeMilestone(milestoneId) {
        return this.request(`/resolutions/milestones/${milestoneId}/complete`, {
            method: 'POST',
        })
    }

    async logProgress(resolutionId, data) {
        return this.request(`/progress/log/${resolutionId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        })
    }

    async getTodayProgress(resolutionId) {
        return this.request(`/progress/today/${resolutionId}`)
    }

    async generateVerificationQuiz(logId) {
        return this.request(`/progress/log/${logId}/verify`, {
            method: 'POST',
        })
    }

    async submitVerificationQuiz(quizId, answers) {
        return this.request(`/progress/quiz/${quizId}/submit`, {
            method: 'POST',
            body: JSON.stringify({ answers }),
        })
    }

    async getProgressHistory(resolutionId, limit = 30) {
        return this.request(`/progress/history/${resolutionId}?limit=${limit}`)
    }

    async getProgressOverview(resolutionId) {
        return this.request(`/progress/overview/${resolutionId}`)
    }

    async getStreak(resolutionId) {
        return this.request(`/progress/streak/${resolutionId}`)
    }

    async transcribeVoice(audioBase64, durationSeconds = null) {
        return this.request('/progress/transcribe', {
            method: 'POST',
            body: JSON.stringify({
                audio_base64: audioBase64,
                duration_seconds: durationSeconds,
            }),
        })
    }
}

export const api = new ApiClient()
