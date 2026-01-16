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

    async getResolution(id) {
        return this.request(`/resolutions/${id}`)
    }

    async uploadContent(resolutionId, file) {
        const formData = new FormData()
        formData.append('file', file)

        const token = this.getToken()
        const response = await fetch(`${this.baseUrl}/resolutions/${resolutionId}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
            body: formData,
        })

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
            throw new Error(error.detail)
        }

        return response.json()
    }

    async generateSyllabus(resolutionId) {
        return this.request(`/resolutions/${resolutionId}/generate-syllabus`, {
            method: 'POST',
        })
    }

    async getSyllabus(resolutionId) {
        return this.request(`/resolutions/${resolutionId}/syllabus`)
    }

    async getTodaySession(resolutionId) {
        return this.request(`/sessions/today?resolution_id=${resolutionId}`)
    }

    async getSession(sessionId) {
        return this.request(`/sessions/${sessionId}`)
    }

    async completeSession(sessionId) {
        return this.request(`/sessions/${sessionId}/complete`, {
            method: 'POST',
        })
    }

    async getQuiz(sessionId) {
        return this.request(`/sessions/${sessionId}/quiz`)
    }

    async submitQuiz(sessionId, answers) {
        return this.request(`/sessions/${sessionId}/quiz/submit`, {
            method: 'POST',
            body: JSON.stringify({ answers }),
        })
    }

    async getSessionHistory(resolutionId) {
        return this.request(`/sessions/history/${resolutionId}`)
    }

    async getProgressOverview(resolutionId) {
        return this.request(`/progress/overview/${resolutionId}`)
    }

    async getWeakAreas(resolutionId) {
        return this.request(`/progress/weak-areas/${resolutionId}`)
    }

    async getStreakInfo(resolutionId) {
        return this.request(`/progress/streaks/${resolutionId}`)
    }

    async getProgressSummary() {
        return this.request('/progress/summary')
    }
}

export const api = new ApiClient()
