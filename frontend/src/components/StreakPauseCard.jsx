import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Coffee, Loader2, Play, Pause, AlertCircle, Sparkles } from 'lucide-react'
import './StreakPauseCard.css'

export default function StreakPauseCard({ isGrouped }) {
    const [loading, setLoading] = useState(true)
    const [prefs, setPrefs] = useState(null)
    const [isPausing, setIsPausing] = useState(false)
    const [isCollapsed, setIsCollapsed] = useState(true)

    useEffect(() => {
        loadPreferences()
    }, [])

    async function loadPreferences() {
        try {
            const data = await api.getEmailPreferences()
            setPreferences(data)
        } catch (error) {
            console.error('Failed to load preferences:', error)
        } finally {
            setLoading(false)
        }
    }

    // Small fix for the state name mismatch in loadPreferences
    function setPreferences(data) {
        if (data) setPrefs(data)
    }

    async function handleTogglePause() {
        setIsPausing(true)
        try {
            if (prefs?.is_paused) {
                const data = await api.resumeStreak()
                setPrefs(data)
            } else {
                const data = await api.pauseStreak()
                setPrefs(data)
            }
        } catch (error) {
            alert(error.message)
        } finally {
            setIsPausing(false)
        }
    }

    if (isGrouped) return null

    if (loading) {
        return (
            <div className="streak-pause-card loading">
                <Loader2 className="spinner" size={24} />
            </div>
        )
    }

    const isPaused = prefs?.is_paused || false

    // If active and paused, force expanded (or handle in parent)
    // Actually, distinct UX:
    // If paused -> Show big banner (handled in parent/DashboardPage with different prop/component placement?)
    // But here, if it is placed in "Tucked away" section, it should probably show state.

    // Simplification for compact view:
    return (
        <div className={`streak-pause-card ${isPaused ? 'paused' : ''} ${isCollapsed && !isPaused ? 'collapsed' : ''}`}>
            <div
                className="pause-header"
                onClick={() => !isPaused && setIsCollapsed(!isCollapsed)}
                style={{ cursor: !isPaused ? 'pointer' : 'default', marginBottom: (isCollapsed && !isPaused) ? 0 : 'var(--space-4)' }}
            >
                <div className="pause-icon">
                    <Coffee size={20} />
                </div>
                <div className="pause-title">
                    <h3>Life Happens</h3>
                    <p>{isPaused ? 'Streak currently paused' : (isCollapsed ? 'Pause streaks for a break' : 'Pause streaks for a guilt-free break.')}</p>
                </div>
            </div>

            {(!isCollapsed || isPaused) && (
                <div className="card-content" onClick={e => e.stopPropagation()}>
                    <div className="pause-content">
                        {isPaused ? (
                            <div className="paused-status">
                                <div className="status-badge">
                                    <Sparkles size={14} />
                                    Currently Paused
                                </div>
                                <p className="status-note">
                                    Emails are stopped and your streak is frozen.
                                    Resumes automatically on next check-in.
                                </p>
                            </div>
                        ) : (
                            <p className="pause-description">
                                Traveling or need a mental health break? Pause your streak to prevent it from breaking.
                            </p>
                        )}
                    </div>

                    <button
                        className={`btn w-full ${isPaused ? 'btn-primary' : 'btn-outline'}`}
                        onClick={handleTogglePause}
                        disabled={isPausing}
                    >
                        {isPausing ? (
                            <><Loader2 className="animate-spin" size={16} /> Working...</>
                        ) : isPaused ? (
                            <><Play size={16} /> Resume Now</>
                        ) : (
                            <><Pause size={16} /> Pause Streak</>
                        )}
                    </button>
                </div>
            )}
        </div>
    )
}
