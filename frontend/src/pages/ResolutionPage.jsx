import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../utils/api'
import {
    Brain, ArrowLeft, Upload, Sparkles, BookOpen, Target,
    Calendar, Clock, Trophy, AlertTriangle, CheckCircle,
    ChevronRight, Loader2, FileText, Play
} from 'lucide-react'
import './ResolutionPage.css'

export default function ResolutionPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [resolution, setResolution] = useState(null)
    const [syllabus, setSyllabus] = useState(null)
    const [sessions, setSessions] = useState([])
    const [progress, setProgress] = useState(null)
    const [weakAreas, setWeakAreas] = useState(null)
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [generating, setGenerating] = useState(false)

    useEffect(() => {
        loadData()
    }, [id])

    async function loadData() {
        try {
            const [resData, sessionsData] = await Promise.all([
                api.getResolution(id),
                api.getSessionHistory(id).catch(() => []),
            ])
            setResolution(resData)
            setSessions(sessionsData)

            try {
                const syllabusData = await api.getSyllabus(id)
                setSyllabus(syllabusData)
            } catch (e) {
                // No syllabus yet
            }

            try {
                const progressData = await api.getProgressOverview(id)
                setProgress(progressData)
            } catch (e) { }

            try {
                const weakData = await api.getWeakAreas(id)
                setWeakAreas(weakData)
            } catch (e) { }
        } catch (error) {
            console.error('Failed to load resolution:', error)
        } finally {
            setLoading(false)
        }
    }

    async function handleFileUpload(e) {
        const file = e.target.files?.[0]
        if (!file) return

        setUploading(true)
        try {
            await api.uploadContent(id, file)
            loadData()
        } catch (error) {
            alert('Upload failed: ' + error.message)
        } finally {
            setUploading(false)
        }
    }

    async function handleGenerateSyllabus() {
        setGenerating(true)
        try {
            const syllabusData = await api.generateSyllabus(id)
            setSyllabus(syllabusData)
            loadData()
        } catch (error) {
            alert('Failed to generate syllabus: ' + error.message)
        } finally {
            setGenerating(false)
        }
    }

    async function handleStartSession() {
        try {
            const todaySession = await api.getTodaySession(id)
            if (todaySession) {
                navigate(`/session/${id}/${todaySession.id}`)
            } else {
                alert('No session available for today!')
            }
        } catch (error) {
            alert('Failed to load session: ' + error.message)
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

    const progressPercent = resolution.duration_days > 0
        ? (resolution.current_day / resolution.duration_days) * 100
        : 0

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
                        <div className="hero-icon">
                            <Target size={32} />
                        </div>
                        <div className="hero-content">
                            <h1>{resolution.title}</h1>
                            <p>{resolution.description}</p>
                        </div>
                    </div>

                    <div className="stats-grid">
                        <div className="stat-card">
                            <Calendar className="stat-icon" />
                            <div className="stat-content">
                                <span className="stat-value">Day {resolution.current_day}</span>
                                <span className="stat-label">of {resolution.duration_days} days</span>
                            </div>
                        </div>

                        <div className="stat-card">
                            <Clock className="stat-icon" />
                            <div className="stat-content">
                                <span className="stat-value">{resolution.daily_time_minutes} min</span>
                                <span className="stat-label">daily commitment</span>
                            </div>
                        </div>

                        <div className="stat-card">
                            <Trophy className="stat-icon" />
                            <div className="stat-content">
                                <span className="stat-value">{Math.round(progressPercent)}%</span>
                                <span className="stat-label">complete</span>
                            </div>
                        </div>

                        {progress && (
                            <div className="stat-card">
                                <CheckCircle className="stat-icon" />
                                <div className="stat-content">
                                    <span className="stat-value">{progress.quizzes_passed}</span>
                                    <span className="stat-label">quizzes passed</span>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="main-progress">
                        <div className="progress-header">
                            <span>Overall Progress</span>
                            <span>{Math.round(progressPercent)}%</span>
                        </div>
                        <div className="progress-bar large">
                            <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
                        </div>
                    </div>

                    {!syllabus ? (
                        <div className="setup-section">
                            <div className="setup-card">
                                <div className="setup-icon">
                                    <Upload size={32} />
                                </div>
                                <h3>Step 1: Upload Learning Materials</h3>
                                <p>Upload PDF, EPUB, or text files that you want to learn from.</p>
                                <label className="btn btn-secondary">
                                    <input
                                        type="file"
                                        accept=".pdf,.epub,.txt,.md"
                                        onChange={handleFileUpload}
                                        style={{ display: 'none' }}
                                    />
                                    {uploading ? (
                                        <>
                                            <Loader2 className="animate-spin" size={18} />
                                            Uploading...
                                        </>
                                    ) : (
                                        <>
                                            <FileText size={18} />
                                            Choose File
                                        </>
                                    )}
                                </label>
                            </div>

                            <div className="setup-card">
                                <div className="setup-icon">
                                    <Sparkles size={32} />
                                </div>
                                <h3>Step 2: Generate AI Syllabus</h3>
                                <p>Our AI will create a personalized curriculum based on your goal and materials.</p>
                                <button
                                    onClick={handleGenerateSyllabus}
                                    className="btn btn-primary"
                                    disabled={generating}
                                >
                                    {generating ? (
                                        <>
                                            <Loader2 className="animate-spin" size={18} />
                                            Generating...
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles size={18} />
                                            Generate Syllabus
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="action-section">
                                <button onClick={handleStartSession} className="btn btn-primary btn-lg start-btn">
                                    <Play size={24} />
                                    Start Today's Session
                                    <ChevronRight size={20} />
                                </button>
                            </div>

                            {weakAreas && weakAreas.weak_concepts.length > 0 && (
                                <div className="weak-areas-section">
                                    <h2>
                                        <AlertTriangle size={24} />
                                        Areas Needing Reinforcement
                                    </h2>
                                    <div className="weak-concepts">
                                        {weakAreas.weak_concepts.map((concept, i) => (
                                            <div key={i} className="concept-chip">
                                                <span className="concept-name">{concept.concept}</span>
                                                <span className="concept-score">{Math.round(concept.mastery_score * 100)}%</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="syllabus-section">
                                <h2>
                                    <BookOpen size={24} />
                                    Your Learning Syllabus
                                </h2>
                                <div className="syllabus-days">
                                    {syllabus.days.map((day, i) => {
                                        const session = sessions.find(s => s.day_number === day.day)
                                        const isCompleted = session?.is_completed
                                        const isCurrent = day.day === resolution.current_day + 1

                                        return (
                                            <div
                                                key={i}
                                                className={`syllabus-day ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}`}
                                            >
                                                <div className="day-number">
                                                    {isCompleted ? <CheckCircle size={18} /> : <span>Day {day.day}</span>}
                                                </div>
                                                <div className="day-content">
                                                    <h4>{day.title}</h4>
                                                    <p>{day.description}</p>
                                                    <div className="day-concepts">
                                                        {day.concepts.slice(0, 3).map((c, j) => (
                                                            <span key={j} className="concept-tag">{c}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                                <div className="day-time">
                                                    <Clock size={14} />
                                                    {day.estimated_minutes} min
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </main>
        </div>
    )
}
