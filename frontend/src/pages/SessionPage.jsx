import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../utils/api'
import {
    ArrowLeft, Clock, BookOpen, CheckCircle, ChevronRight,
    Loader2, Brain
} from 'lucide-react'
import './SessionPage.css'

export default function SessionPage() {
    const { resolutionId, sessionId } = useParams()
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [loading, setLoading] = useState(true)
    const [completing, setCompleting] = useState(false)
    const [readingProgress, setReadingProgress] = useState(0)

    useEffect(() => {
        loadSession()
    }, [sessionId])

    useEffect(() => {
        function handleScroll() {
            const element = document.querySelector('.content-reader')
            if (!element) return

            const scrolled = element.scrollTop
            const total = element.scrollHeight - element.clientHeight
            const progress = total > 0 ? (scrolled / total) * 100 : 100
            setReadingProgress(Math.min(100, Math.max(0, progress)))
        }

        const reader = document.querySelector('.content-reader')
        if (reader) {
            reader.addEventListener('scroll', handleScroll)
            return () => reader.removeEventListener('scroll', handleScroll)
        }
    }, [session])

    async function loadSession() {
        try {
            const data = await api.getSession(sessionId)
            setSession(data)
        } catch (error) {
            console.error('Failed to load session:', error)
        } finally {
            setLoading(false)
        }
    }

    async function handleComplete() {
        setCompleting(true)
        try {
            await api.completeSession(sessionId)
            navigate(`/quiz/${sessionId}`)
        } catch (error) {
            alert('Failed to complete session: ' + error.message)
        } finally {
            setCompleting(false)
        }
    }

    if (loading) {
        return (
            <div className="session-page">
                <div className="loading-container">
                    <Loader2 className="spinner" size={48} />
                    <p>Loading today's session...</p>
                </div>
            </div>
        )
    }

    if (!session) {
        return (
            <div className="session-page">
                <div className="error-container">
                    <h2>Session not found</h2>
                    <Link to={`/resolution/${resolutionId}`} className="btn btn-primary">
                        Back to Resolution
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="session-page">
            <header className="session-header">
                <div className="container">
                    <Link to={`/resolution/${resolutionId}`} className="back-link">
                        <ArrowLeft size={18} />
                        Back to Resolution
                    </Link>
                    <div className="session-meta">
                        <span className="day-badge">Day {session.day_number}</span>
                        {session.is_reinforcement && (
                            <span className="reinforcement-badge">
                                <Brain size={14} />
                                Reinforcement
                            </span>
                        )}
                    </div>
                </div>
            </header>

            <div className="reading-progress-bar">
                <div className="reading-progress-fill" style={{ width: `${readingProgress}%` }} />
            </div>

            <main className="session-main">
                <div className="container">
                    <div className="session-intro">
                        <h1>{session.title}</h1>
                        {session.summary && <p className="session-summary">{session.summary}</p>}

                        {session.concepts && session.concepts.length > 0 && (
                            <div className="session-concepts">
                                <span className="concepts-label">Today's Concepts:</span>
                                <div className="concepts-list">
                                    {session.concepts.map((concept, i) => (
                                        <span key={i} className="concept-tag">{concept}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="content-reader">
                        <div className="content-body">
                            {session.content ? (
                                session.content.split('\n').map((paragraph, i) => (
                                    paragraph.trim() && (
                                        <p key={i} className="content-paragraph">{paragraph}</p>
                                    )
                                ))
                            ) : (
                                <div className="no-content">
                                    <BookOpen size={48} />
                                    <h3>Content is being prepared</h3>
                                    <p>The AI is generating your learning content. Please check back in a moment.</p>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="session-footer">
                        <div className="footer-progress">
                            <div className="progress-info">
                                <Clock size={18} />
                                <span>Estimated: 30 minutes</span>
                            </div>
                            <div className="progress-indicator">
                                <span>Reading Progress: {Math.round(readingProgress)}%</span>
                            </div>
                        </div>

                        <button
                            onClick={handleComplete}
                            className="btn btn-primary btn-lg complete-btn"
                            disabled={completing}
                        >
                            {completing ? (
                                <>
                                    <Loader2 className="animate-spin" size={20} />
                                    Completing...
                                </>
                            ) : (
                                <>
                                    <CheckCircle size={20} />
                                    I've Finished Reading - Take Quiz
                                    <ChevronRight size={20} />
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </main>
        </div>
    )
}
