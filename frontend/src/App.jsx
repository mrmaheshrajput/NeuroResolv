import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ResolutionPage from './pages/ResolutionPage'
import CheckinPage from './pages/CheckinPage'

function ProtectedRoute({ children }) {
    const { user, loading } = useAuth()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="spinner" style={{ width: 48, height: 48 }} />
            </div>
        )
    }

    if (!user) {
        return <Navigate to="/login" replace />
    }

    return children
}

function PublicRoute({ children }) {
    const { user, loading } = useAuth()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="spinner" style={{ width: 48, height: 48 }} />
            </div>
        )
    }

    if (user) {
        return <Navigate to="/dashboard" replace />
    }

    return children
}

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={
                        <PublicRoute>
                            <LoginPage />
                        </PublicRoute>
                    } />
                    <Route path="/register" element={
                        <PublicRoute>
                            <RegisterPage />
                        </PublicRoute>
                    } />
                    <Route path="/dashboard" element={
                        <ProtectedRoute>
                            <DashboardPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/resolution/:id" element={
                        <ProtectedRoute>
                            <ResolutionPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/checkin/:id" element={
                        <ProtectedRoute>
                            <CheckinPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/" element={<Navigate to="/login" replace />} />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    )
}

export default App
