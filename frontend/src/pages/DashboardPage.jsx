import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../utils/api'
import {
    Brain, LogOut, Plus, Target, Flame, Trophy,
    BookOpen, ChevronRight, Calendar, TrendingUp,
    Loader2, X
} from 'lucide-react'
import './DashboardPage.css'

export default function DashboardPage() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()
    const [resolutions, setResolutions] = useState([])
    const [loading, setLoading] = useState(true)
    const [showCreateModal, setShowCreateModal] = useState(false)

    useEffect(() => {
        loadResolutions()
    }, [])

    async function loadResolutions() {
        try {
            const data = await api.getResolutions()
            setResolutions(data)
        } catch (error) {
            console.error('Failed to load resolutions:', error)
        } finally {
            setLoading(false)
        }
    }

    function handleLogout() {
        logout()
        navigate('/login')
    }

    return (
        <div className="dashboard-page">
            <header className="dashboard-header">
                <div className="container">
                    <div className="header-content">
                        <Link to="/dashboard" className="logo">
                            <Brain className="logo-icon" />
                            <span className="logo-text">NeuroResolv</span>
                        </Link>

                        <div className="header-actions">
                            <div className="user-info">
                                <span className="user-name">{user?.full_name}</span>
                                <span className="user-email">{user?.email}</span>
                            </div>
                            <button onClick={handleLogout} className="btn btn-ghost">
                                <LogOut size={18} />
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <main className="dashboard-main">
                <div className="container">
                    <div className="dashboard-welcome">
                        <div className="welcome-text">
                            <h1>Welcome back, {user?.full_name?.split(' ')[0]}! 👋</h1>
                            <p>Ready to continue your learning journey?</p>
                        </div>
                        <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
                            <Plus size={20} />
                            New Resolution
                        </button>
                    </div>

                    {loading ? (
                        <div className="loading-state">
                            <Loader2 className="spinner" size={48} />
                            <p>Loading your resolutions...</p>
                        </div>
                    ) : resolutions.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-icon">
                                <Target size={64} />
                            </div>
                            <h2>No resolutions yet</h2>
                            <p>Create your first resolution and start your learning journey!</p>
                            <button onClick={() => setShowCreateModal(true)} className="btn btn-primary btn-lg">
                                <Plus size={20} />
                                Create Your First Resolution
                            </button>
                        </div>
                    ) : (
                        <div className="resolutions-grid">
                            {resolutions.map((resolution) => (
                                <ResolutionCard
                                    key={resolution.id}
                                    resolution={resolution}
                                    onClick={() => navigate(`/resolution/${resolution.id}`)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </main>

            {showCreateModal && (
                <CreateResolutionModal
                    onClose={() => setShowCreateModal(false)}
                    onCreated={(newResolution) => {
                        setResolutions([newResolution, ...resolutions])
                        setShowCreateModal(false)
                        navigate(`/resolution/${newResolution.id}`)
                    }}
                />
            )}
        </div>
    )
}

function ResolutionCard({ resolution, onClick }) {
    const progressPercent = resolution.duration_days > 0
        ? (resolution.current_day / resolution.duration_days) * 100
        : 0

    return (
        <div className="resolution-card" onClick={onClick}>
            <div className="resolution-header">
                <div className="resolution-icon">
                    <BookOpen size={24} />
                </div>
                <span className={`resolution-status badge badge-${resolution.status === 'active' ? 'success' : 'warning'}`}>
                    {resolution.status}
                </span>
            </div>

            <h3 className="resolution-title">{resolution.title}</h3>
            <p className="resolution-description">{resolution.description}</p>

            <div className="resolution-stats">
                <div className="stat">
                    <Calendar size={16} />
                    <span>Day {resolution.current_day} of {resolution.duration_days}</span>
                </div>
                <div className="stat">
                    <TrendingUp size={16} />
                    <span>{resolution.daily_time_minutes} min/day</span>
                </div>
            </div>

            <div className="resolution-progress">
                <div className="progress-header">
                    <span>Progress</span>
                    <span>{Math.round(progressPercent)}%</span>
                </div>
                <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
                </div>
            </div>

            <div className="resolution-action">
                <span>Continue Learning</span>
                <ChevronRight size={18} />
            </div>
        </div>
    )
}

function CreateResolutionModal({ onClose, onCreated }) {
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [goalStatement, setGoalStatement] = useState('')
    const [dailyMinutes, setDailyMinutes] = useState(30)
    const [durationDays, setDurationDays] = useState(30)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    async function handleSubmit(e) {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const resolution = await api.createResolution({
                title,
                description,
                goal_statement: goalStatement,
                daily_time_minutes: dailyMinutes,
                duration_days: durationDays,
            })
            onCreated(resolution)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Create New Resolution</h2>
                    <button onClick={onClose} className="modal-close">
                        <X size={24} />
                    </button>
                </div>

                {error && <div className="error-message">{error}</div>}

                <form onSubmit={handleSubmit} className="modal-form">
                    <div className="input-group">
                        <label htmlFor="title" className="input-label">Resolution Title</label>
                        <input
                            id="title"
                            type="text"
                            className="input"
                            placeholder="e.g., Master LLM Operations"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label htmlFor="description" className="input-label">Description</label>
                        <textarea
                            id="description"
                            className="input textarea"
                            placeholder="What do you want to achieve?"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label htmlFor="goal" className="input-label">Learning Goal Statement</label>
                        <textarea
                            id="goal"
                            className="input textarea"
                            placeholder="e.g., I want to master LLM Ops by reading documentation and papers, 30 minutes a day."
                            value={goalStatement}
                            onChange={(e) => setGoalStatement(e.target.value)}
                            required
                        />
                    </div>

                    <div className="input-row">
                        <div className="input-group">
                            <label htmlFor="dailyMinutes" className="input-label">Daily Minutes</label>
                            <input
                                id="dailyMinutes"
                                type="number"
                                className="input"
                                min={10}
                                max={120}
                                value={dailyMinutes}
                                onChange={(e) => setDailyMinutes(parseInt(e.target.value))}
                                required
                            />
                        </div>

                        <div className="input-group">
                            <label htmlFor="duration" className="input-label">Duration (Days)</label>
                            <input
                                id="duration"
                                type="number"
                                className="input"
                                min={7}
                                max={90}
                                value={durationDays}
                                onChange={(e) => setDurationDays(parseInt(e.target.value))}
                                required
                            />
                        </div>
                    </div>

                    <div className="modal-actions">
                        <button type="button" onClick={onClose} className="btn btn-secondary">
                            Cancel
                        </button>
                        <button type="submit" className="btn btn-primary" disabled={loading}>
                            {loading ? (
                                <>
                                    <Loader2 className="animate-spin" size={18} />
                                    Creating...
                                </>
                            ) : (
                                <>
                                    <Plus size={18} />
                                    Create Resolution
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
