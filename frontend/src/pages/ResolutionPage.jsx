import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../utils/api'
import {
    ArrowLeft, Sparkles, Target, Calendar, Clock,
    CheckCircle, Edit2, ChevronRight, Loader2, Flame,
    BookOpen, AlertTriangle, RefreshCw
} from 'lucide-react'
import './ResolutionPage.css'

const CADENCE_LABELS = {
    daily: 'Daily',
    '3x_week': '3x/week',
    weekdays: 'Weekdays',
    weekly: 'Weekly',
}

export default function ResolutionPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [resolution, setResolution] = useState(null)
    const [roadmap, setRoadmap] = useState(null)
    const [streak, setStreak] = useState(null)
    const [todayProgress, setTodayProgress] = useState(null)
    const [loading, setLoading] = useState(true)
    const [generating, setGenerating] = useState(false)

    useEffect(() => {
        loadData()
    }, [id])

    async function loadData() {
        try {
            const resData = await api.getResolution(id)
            setResolution(resData)

            if (resData.roadmap_generated) {
                const [roadmapData, streakData, todayData] = await Promise.all([
                    api.getRoadmap(id).catch(() => null),
                    api.getStreak(id).catch(() => null),
                    api.getTodayProgress(id).catch(() => null),
                ])
                setRoadmap(roadmapData)
                setStreak(streakData)
                setTodayProgress(todayData)
            }
        } catch (error) {
            console.error('Failed to load resolution:', error)
        } finally {
            setLoading(false)
        }
    }

    async function handleGenerateRoadmap() {
        setGenerating(true)
        try {
            const roadmapData = await api.generateRoadmap(id)
            setRoadmap(roadmapData)
            setResolution(prev => ({ ...prev, roadmap_generated: true }))
        } catch (error) {
            alert('Failed to generate roadmap: ' + error.message)
        } finally {
            setGenerating(false)
        }
    }

    if (loading) {
        return (
            <div className="resolution-page">
                <div className="loading-container">
                    <Loader2 className="spinner" size={48} />
                    <p>Loading resolution...</p>
                </div>
            </div>
        )
    }

    if (!resolution) {
        return (
            <div className="resolution-page">
                <div className="error-container">
                    <h2>Resolution not found</h2>
                    <Link to="/dashboard" className="btn btn-primary">
                        Back to Dashboard
                    </Link>
                </div>
            </div>
        )
    }

    const currentMilestone = roadmap?.milestones?.find(m => m.status === 'in_progress')
    const completedMilestones = roadmap?.milestones?.filter(m => m.status === 'completed').length || 0
    const totalMilestones = roadmap?.milestones?.length || 0

    return (
        <div className="resolution-page">
            <header className="page-header">
                <div className="container">
                    <Link to="/dashboard" className="back-link">
                        <ArrowLeft size={18} />
                        Back to Dashboard
                    </Link>
                </div>
            </header>

            <main className="page-main">
                <div className="container">
                    <div className="resolution-hero">
                        <div className="hero-content">
                            <div className="goal-category">
                                <span className="category-badge">{resolution.category}</span>
                                <span className="cadence-badge">{CADENCE_LABELS[resolution.cadence]}</span>
                                {resolution.skill_level && (
                                    <span className="skill-badge">{resolution.skill_level}</span>
                                )}
                            </div>
                            <h1>{resolution.goal_statement}</h1>
                        </div>

                        {streak && (
                            <div className="streak-card">
                                <Flame className="streak-icon" />
                                <div className="streak-info">
                                    <span className="streak-number">{streak.current_streak}</span>
                                    <span className="streak-label">day streak</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {!resolution.roadmap_generated ? (
                        <div className="generate-section">
                            <div className="generate-card">
                                <div className="generate-icon">
                                    <Sparkles size={48} />
                                </div>
                                <h2>Generate Your Learning Roadmap</h2>
                                <p>
                                    Our AI will create a personalized milestone-based roadmap
                                    tailored to your goal and learning style.
                                </p>
                                <button
                                    onClick={handleGenerateRoadmap}
                                    className="btn btn-primary btn-lg"
                                    disabled={generating}
                                >
                                    {generating ? (
                                        <>
                                            <Loader2 className="animate-spin" size={20} />
                                            Generating Roadmap...
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles size={20} />
                                            Generate AI Roadmap
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="stats-row">
                                <div className="stat-card">
                                    <Target className="stat-icon" />
                                    <div className="stat-info">
                                        <span className="stat-value">{completedMilestones}/{totalMilestones}</span>
                                        <span className="stat-label">Milestones</span>
                                    </div>
                                </div>
                                <div className="stat-card">
                                    <Flame className="stat-icon" />
                                    <div className="stat-info">
                                        <span className="stat-value">{streak?.current_streak || 0}</span>
                                        <span className="stat-label">Current Streak</span>
                                    </div>
                                </div>
                                <div className="stat-card">
                                    <CheckCircle className="stat-icon" />
                                    <div className="stat-info">
                                        <span className="stat-value">{streak?.total_verified_days || 0}</span>
                                        <span className="stat-label">Verified Days</span>
                                    </div>
                                </div>
                            </div>

                            <div className="daily-action-section">
                                {todayProgress ? (
                                    <div className="today-logged-card">
                                        <CheckCircle size={24} className="logged-icon" />
                                        <div className="logged-content">
                                            <h3>Today's Progress Logged</h3>
                                            <p>{todayProgress.content.slice(0, 100)}...</p>
                                            {!todayProgress.verified && (
                                                <Link
                                                    to={`/checkin/${id}?verify=${todayProgress.id}`}
                                                    className="btn btn-primary btn-sm"
                                                >
                                                    Take Verification Quiz
                                                </Link>
                                            )}
                                        </div>
                                    </div>
                                ) : (
                                    <Link to={`/checkin/${id}`} className="daily-checkin-btn">
                                        <div className="checkin-content">
                                            <BookOpen size={28} />
                                            <div className="checkin-text">
                                                <h3>Log Today's Progress</h3>
                                                <p>What did you work on today?</p>
                                            </div>
                                        </div>
                                        <ChevronRight size={24} />
                                    </Link>
                                )}
                            </div>

                            {roadmap?.needs_refresh && (
                                <div className="refresh-notice">
                                    <AlertTriangle size={20} />
                                    <span>You've made edits. The roadmap may need refreshing.</span>
                                    <button className="btn btn-sm btn-secondary">
                                        <RefreshCw size={14} />
                                        Refresh
                                    </button>
                                </div>
                            )}

                            <div className="roadmap-section">
                                <div className="section-header">
                                    <h2>Your Learning Roadmap</h2>
                                    <button className="btn btn-ghost btn-sm">
                                        <Edit2 size={16} />
                                        Edit
                                    </button>
                                </div>

                                <div className="milestones-list">
                                    {roadmap?.milestones?.map((milestone, i) => (
                                        <div
                                            key={milestone.id}
                                            className={`milestone-card ${milestone.status}`}
                                        >
                                            <div className="milestone-number">
                                                {milestone.status === 'completed' ? (
                                                    <CheckCircle size={24} />
                                                ) : (
                                                    <span>{i + 1}</span>
                                                )}
                                            </div>
                                            <div className="milestone-content">
                                                <h3>{milestone.title}</h3>
                                                <p>{milestone.description}</p>
                                                <div className="milestone-meta">
                                                    <span className="verification-label">
                                                        <Target size={14} />
                                                        {milestone.verification_criteria}
                                                    </span>
                                                    {milestone.target_date && (
                                                        <span className="target-date">
                                                            <Calendar size={14} />
                                                            Target: {new Date(milestone.target_date).toLocaleDateString()}
                                                        </span>
                                                    )}
                                                </div>
                                                {milestone.is_edited && (
                                                    <span className="edited-badge">Edited</span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </main>
        </div>
    )
}
