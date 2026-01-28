import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../utils/api'
import {
    Brain, LogOut, Plus, Target, Flame, BookOpen,
    ChevronRight, Loader2, X, Dumbbell, Briefcase,
    Palette, GraduationCap, TrendingUp
} from 'lucide-react'
import './DashboardPage.css'
import './CreateModal.css'

const CATEGORY_ICONS = {
    learning: GraduationCap,
    reading: BookOpen,
    skill: Target,
    fitness: Dumbbell,
    professional: Briefcase,
    creative: Palette,
}

const CATEGORY_LABELS = {
    learning: 'Learning & Education',
    reading: 'Reading & Literature',
    skill: 'Skill Acquisition',
    fitness: 'Fitness & Wellness',
    professional: 'Professional Development',
    creative: 'Creative Projects',
}

const CADENCE_LABELS = {
    daily: 'Daily check-ins',
    '3x_week': '3 times per week',
    weekdays: 'Weekdays only',
    weekly: 'Weekly check-ins',
}

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
    const CategoryIcon = CATEGORY_ICONS[resolution.category] || Target

    return (
        <div className="resolution-card" onClick={onClick}>
            <div className="resolution-header">
                <div className="resolution-icon">
                    <CategoryIcon size={24} />
                </div>
                <div className="resolution-meta">
                    <span className={`resolution-status badge badge-${resolution.status === 'active' ? 'success' : 'warning'}`}>
                        {resolution.status}
                    </span>
                    {resolution.skill_level && (
                        <span className="badge badge-primary">{resolution.skill_level}</span>
                    )}
                </div>
            </div>

            <h3 className="resolution-title">{resolution.goal_statement.slice(0, 60)}...</h3>

            <div className="resolution-info">
                <span className="category-label">{CATEGORY_LABELS[resolution.category]}</span>
                <span className="cadence-label">{CADENCE_LABELS[resolution.cadence]}</span>
            </div>

            <div className="resolution-stats">
                {resolution.roadmap_generated ? (
                    <>
                        <div className="stat">
                            <Target size={16} />
                            <span>Milestone {resolution.current_milestone}</span>
                        </div>
                        {resolution.roadmap_needs_refresh && (
                            <span className="badge badge-warning">Needs refresh</span>
                        )}
                    </>
                ) : (
                    <span className="badge badge-warning">Roadmap pending</span>
                )}
            </div>

            <div className="resolution-action">
                <span>Continue</span>
                <ChevronRight size={18} />
            </div>
        </div>
    )
}

function CreateResolutionModal({ onClose, onCreated }) {
    const [step, setStep] = useState(1)
    const [goalStatement, setGoalStatement] = useState('')
    const [category, setCategory] = useState('learning')
    const [skillLevel, setSkillLevel] = useState('')
    const [cadence, setCadence] = useState('daily')
    const [loading, setLoading] = useState(false)
    const [negotiating, setNegotiating] = useState(false)
    const [negotiationResult, setNegotiationResult] = useState(null)
    const [error, setError] = useState('')

    async function handleNext() {
        if (step === 1) {
            setStep(2)
            return
        }

        if (step === 2) {
            setNegotiating(true)
            setError('')
            try {
                const result = await api.negotiateResolution({
                    goal_statement: goalStatement,
                    category,
                    skill_level: skillLevel || null,
                    cadence,
                })
                setNegotiationResult(result)
                if (!result.is_feasible) {
                    // Stay on step 2 but show negotiation
                } else {
                    handleSubmit()
                }
            } catch (err) {
                setError(err.message)
            } finally {
                setNegotiating(false)
            }
        }
    }

    async function applySuggestion() {
        if (negotiationResult?.suggestion) {
            setCadence(negotiationResult.suggestion.cadence)
            setNegotiationResult(null)
            // Re-negotiate or just submit? Let's just submit with the new cadence to be fast
            setLoading(true)
            try {
                const resolution = await api.createResolution({
                    goal_statement: goalStatement,
                    category,
                    skill_level: skillLevel || null,
                    cadence: negotiationResult.suggestion.cadence,
                })
                onCreated(resolution)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }
    }

    async function handleSubmit() {
        if (goalStatement.length < 10) {
            setError('Please describe your goal in more detail')
            return
        }

        setError('')
        setLoading(true)

        try {
            const resolution = await api.createResolution({
                goal_statement: goalStatement,
                category,
                skill_level: skillLevel || null,
                cadence,
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
            <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Create New Resolution</h2>
                    <button onClick={onClose} className="modal-close">
                        <X size={24} />
                    </button>
                </div>

                {error && <div className="error-message">{error}</div>}

                <div className="modal-steps">
                    <div className={`step ${step >= 1 ? 'active' : ''}`}>1. Goal</div>
                    <div className={`step ${step >= 2 ? 'active' : ''}`}>2. Details</div>
                </div>

                <div className="modal-form">
                    {step === 1 && (
                        <div className="step-content">
                            <div className="input-group">
                                <label className="input-label">What's your goal?</label>
                                <textarea
                                    className="input textarea"
                                    placeholder="e.g., Read 12 books on behavioral psychology this year, or Learn Spanish to conversational fluency"
                                    value={goalStatement}
                                    onChange={(e) => setGoalStatement(e.target.value)}
                                    rows={4}
                                />
                                <p className="input-hint">Be specific about what you want to achieve</p>
                            </div>

                            <div className="input-group">
                                <label className="input-label">Category</label>
                                <div className="category-grid">
                                    {Object.entries(CATEGORY_LABELS).map(([key, label]) => {
                                        const Icon = CATEGORY_ICONS[key]
                                        return (
                                            <button
                                                key={key}
                                                type="button"
                                                className={`category-btn ${category === key ? 'selected' : ''}`}
                                                onClick={() => setCategory(key)}
                                            >
                                                <Icon size={20} />
                                                <span>{label}</span>
                                            </button>
                                        )
                                    })}
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="step-content">
                            <div className="input-group">
                                <label className="input-label">Current Skill Level (Optional)</label>
                                <p className="input-hint">The AI will assess this if you skip</p>
                                <div className="skill-options">
                                    {[
                                        { value: '', label: 'Let AI assess' },
                                        { value: 'beginner', label: 'Beginner' },
                                        { value: 'intermediate', label: 'Intermediate' },
                                        { value: 'advanced', label: 'Advanced' },
                                    ].map((option) => (
                                        <button
                                            key={option.value}
                                            type="button"
                                            className={`skill-btn ${skillLevel === option.value ? 'selected' : ''}`}
                                            onClick={() => setSkillLevel(option.value)}
                                        >
                                            {option.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="input-group">
                                <label className="input-label">How often will you work on this?</label>
                                <div className="cadence-options">
                                    {[
                                        { value: 'daily', label: 'Daily', desc: '7 days/week' },
                                        { value: '3x_week', label: '3x per week', desc: 'Flexible days' },
                                        { value: 'weekdays', label: 'Weekdays only', desc: 'Mon-Fri' },
                                        { value: 'weekly', label: 'Weekly', desc: 'Once per week' },
                                    ].map((option) => (
                                        <button
                                            key={option.value}
                                            type="button"
                                            className={`cadence-btn ${cadence === option.value ? 'selected' : ''}`}
                                            onClick={() => {
                                                setCadence(option.value)
                                                setNegotiationResult(null)
                                            }}
                                        >
                                            <span className="cadence-label">{option.label}</span>
                                            <span className="cadence-desc">{option.desc}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {negotiationResult && !negotiationResult.is_feasible && (
                                <div className="negotiation-card">
                                    <div className="negotiation-header">
                                        <Brain size={20} className="negotiation-icon" />
                                        <h3>Reality Check</h3>
                                    </div>
                                    <p className="negotiation-feedback">{negotiationResult.feedback}</p>
                                    {negotiationResult.suggestion && (
                                        <div className="negotiation-suggestion">
                                            <p><strong>AI Suggestion:</strong> {negotiationResult.suggestion.reason}</p>
                                            <div className="negotiation-actions">
                                                <button
                                                    type="button"
                                                    className="btn btn-secondary btn-sm"
                                                    onClick={applySuggestion}
                                                >
                                                    Apply {CADENCE_LABELS[negotiationResult.suggestion.cadence]}
                                                </button>
                                                <button
                                                    type="button"
                                                    className="btn btn-ghost btn-sm"
                                                    onClick={handleSubmit}
                                                >
                                                    Keep My Plan
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                </div>

                <div className="modal-actions">
                    {step > 1 && (
                        <button
                            type="button"
                            onClick={() => {
                                setStep(step - 1)
                                setNegotiationResult(null)
                            }}
                            className="btn btn-secondary"
                            disabled={loading || negotiating}
                        >
                            Back
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={handleNext}
                        className="btn btn-primary"
                        disabled={loading || negotiating || (step === 1 && goalStatement.length < 10)}
                    >
                        {loading || negotiating ? (
                            <>
                                <Loader2 className="animate-spin" size={18} />
                                {negotiating ? 'Checking...' : 'Creating...'}
                            </>
                        ) : (
                            <>
                                {step === 2 ? 'Finish' : 'Continue'}
                                <ChevronRight size={18} />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
