import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Sparkles, X, ChevronDown, ChevronUp, Target, Loader2 } from 'lucide-react'
import './WeeklyGoalBanner.css'

/**
 * WeeklyGoalBanner - Displays a single, aggregated weekly focus for all resolutions
 */
export default function WeeklyGoalBanner({ resolutions }) {
    const [aggregatedFocus, setAggregatedFocus] = useState(null)
    const [loading, setLoading] = useState(true)
    const [expanded, setExpanded] = useState(true)
    const [isDismissed, setIsDismissed] = useState(false)

    useEffect(() => {
        loadFocus()
    }, [resolutions])

    async function loadFocus() {
        setLoading(true)
        try {
            const data = await api.getAggregatedWeeklyFocus()
            setAggregatedFocus(data)
            setIsDismissed(data.is_dismissed)
            // If it's already dismissed in DB, collapse it by default
            if (data.is_dismissed) {
                setExpanded(false)
            }
        } catch (error) {
            console.error('Failed to load aggregated weekly focus:', error)
        } finally {
            setLoading(false)
        }
    }

    async function handleDismiss(e) {
        if (e) e.stopPropagation()
        if (!aggregatedFocus || aggregatedFocus.id === 0) {
            setExpanded(false)
            return
        }

        try {
            await api.dismissAggregatedFocus(aggregatedFocus.id)
            setIsDismissed(true)
            setExpanded(false)
        } catch (error) {
            console.error('Failed to dismiss focus:', error)
        }
    }

    if (loading) {
        return (
            <div className="weekly-goal-banner loading">
                <Loader2 className="animate-spin" size={20} />
                <span>Syncing your weekly focus...</span>
            </div>
        )
    }

    if (!aggregatedFocus) return null

    return (
        <div className={`weekly-goal-banner ${expanded ? 'expanded' : 'collapsed'}`}>
            <div className="banner-header" onClick={() => setExpanded(!expanded)}>
                <div className="banner-title">
                    <Sparkles className="banner-icon" size={20} />
                    <div className="title-text-wrap">
                        <h3>Your Weekly Focus</h3>
                        {isDismissed && <span className="dismissed-tag">Hidden</span>}
                    </div>
                </div>
                <div className="banner-actions">
                    {!expanded && (
                        <span className="collapsed-preview">
                            {aggregatedFocus.focus_text.slice(0, 60)}...
                        </span>
                    )}
                    <button className="toggle-btn">
                        {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </button>
                </div>
            </div>

            {expanded && (
                <div className="banner-content">
                    <div className="goal-card actual">
                        <div className="goal-header">
                            <Target className="goal-icon" size={16} />
                            <span className="focus-label">Integrated Strategy</span>
                            <button
                                className="dismiss-btn"
                                onClick={handleDismiss}
                                title="Hide this focus"
                            >
                                <X size={14} />
                            </button>
                        </div>

                        <p className="goal-text">{aggregatedFocus.focus_text}</p>

                        {aggregatedFocus.micro_actions && aggregatedFocus.micro_actions.length > 0 && (
                            <div className="micro-actions-section">
                                <h4>Key Micro-actions:</h4>
                                <ul className="micro-actions">
                                    {aggregatedFocus.micro_actions.map((action, i) => (
                                        <li key={i}>{action}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {aggregatedFocus.motivation_note && (
                            <p className="motivation-note">
                                <strong>Pro Tip:</strong> {aggregatedFocus.motivation_note}
                            </p>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
