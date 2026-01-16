import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        checkAuth()
    }, [])

    async function checkAuth() {
        const token = localStorage.getItem('token')
        if (!token) {
            setLoading(false)
            return
        }

        try {
            const userData = await api.getMe()
            setUser(userData)
        } catch (error) {
            api.clearToken()
        } finally {
            setLoading(false)
        }
    }

    async function login(email, password) {
        const data = await api.login(email, password)
        setUser(data.user)
        return data
    }

    async function register(email, password, fullName) {
        const data = await api.register(email, password, fullName)
        setUser(data.user)
        return data
    }

    function logout() {
        api.logout()
        setUser(null)
    }

    const value = {
        user,
        loading,
        login,
        register,
        logout,
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
