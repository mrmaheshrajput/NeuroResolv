import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../utils/api'
import {
    ArrowLeft, Sparkles, Target, Calendar, Clock,
    CheckCircle, Edit2, ChevronRight, Loader2, Flame,
    BookOpen, AlertTriangle, RefreshCw, Trophy, LineChart,
    Plus, X
} from 'lucide-react'
import WeeklyGoalBanner from './WeeklyGoalBanner'
import AIFeedback from '../components/AIFeedback'
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
    const [northStar, setNorthStar] = useState(null)
    const [loading, setLoading] = useState(true)
    const [generating, setGenerating] = useState(false)
    const [livingRoadmapData, setLivingRoadmapData] = useState(null)
    const [isEditingRoadmap, setIsEditingRoadmap] = useState(false)
    const [editableMilestones, setEditableMilestones] = useState([])
    const [savingRoadmap, setSavingRoadmap] = useState(false)
    const [isEditingNorthStar, setIsEditingNorthStar] = useState(false)
    const [editableNorthStar, setEditableNorthStar] = useState('')

    async function saveNorthStar() {
        try {
            const updated = await api.updateNorthStar(id, { goal_statement: editableNorthStar })
            setNorthStar(updated)
            setIsEditingNorthStar(false)
        } catch (error) {
            alert('Failed to save North Star: ' + error.message)
        }
    }

    useEffect(() => {
        loadData()
    }, [id])

    async function loadData() {
        try {
            const resData = await api.getResolution(id)
            setResolution(resData)

            if (resData.roadmap_generated) {
                const [roadmapData, streakData, todayData, northStarData, livingData] = await Promise.all([
                    api.getRoadmap(id).catch(() => null),
                    api.getStreak(id).catch(() => null),
                    api.getTodayProgress(id).catch(() => null),
                    api.getNorthStar(id).catch(() => null),
                    api.getLivingRoadmap(id).catch(() => null),
                ])
                setRoadmap(roadmapData)
                setStreak(streakData)
                setTodayProgress(todayData)
                setNorthStar(northStarData)
                setLivingRoadmapData(livingData)
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

            // Also generate initial North Star
            try {
                const nsData = await api.generateNorthStar(id)
                setNorthStar(nsData)
            } catch (nsError) {
                console.error('Failed to generate north star:', nsError)
            }

            // Fetch living roadmap metadata (for likelihood score)
            const livingData = await api.getLivingRoadmap(id).catch(() => null)
            setLivingRoadmapData(livingData)

        } catch (error) {
            alert('Failed to generate roadmap: ' + error.message)
        } finally {
            setGenerating(false)
        }
    }

    async function handleRefreshRoadmap() {
        setGenerating(true)
        try {
            await api.refreshRoadmap(id)
            await loadData()
        } catch (error) {
            alert('Failed to refresh roadmap: ' + error.message)
        } finally {
            setGenerating(false)
        }
    }

    function startEditing() {
        setEditableMilestones(roadmap?.milestones?.map(m => ({ ...m })) || [{
            id: 'new-' + Date.now(),
            title: '',
            description: '',
            verification_criteria: '',
            target_date: '',
            status: 'pending'
        }])
        setIsEditingRoadmap(true)
    }

    function addMilestone() {
        setEditableMilestones([...editableMilestones, {
            id: 'new-' + Date.now(),
            title: '',
            description: '',
            verification_criteria: '',
            target_date: '',
            status: 'pending'
        }])
    }

    function removeMilestone(index) {
        setEditableMilestones(editableMilestones.filter((_, i) => i !== index))
    }

    function updateMilestone(index, updates) {
        const newMilestones = [...editableMilestones]
        newMilestones[index] = { ...newMilestones[index], ...updates }
        setEditableMilestones(newMilestones)
    }

    async function saveManualRoadmap() {
        if (editableMilestones.some(m => !m.title || !m.description)) {
            alert('Please fill in title and description for all milestones')
            return
        }

        setSavingRoadmap(true)
        try {
            const cleanedMilestones = editableMilestones.map(m => ({
                title: m.title,
                description: m.description,
                verification_criteria: m.verification_criteria,
                target_date: m.target_date && m.target_date !== '' ? m.target_date : null
            }))
            await api.saveManualRoadmap(id, cleanedMilestones)
            setIsEditingRoadmap(false)
            await loadData()
        } catch (error) {
            console.error('Manual roadmap save failed:', error)
            alert('Failed to save roadmap: ' + error.message)
        } finally {
            setSavingRoadmap(false)
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
                            <WeeklyGoalBanner resolutions={[resolution]} singleResolutionId={resolution.id} />

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
                                <div className="stat-card likelihood">
                                    <LineChart className="stat-icon" />
                                    <div className="stat-info">
                                        <span className="stat-value">
                                            {livingRoadmapData?.likelihood_score
                                                ? `${Math.round(livingRoadmapData.likelihood_score * 100)}%`
                                                : '--'}
                                        </span>
                                        <span className="stat-label">Success Likelihood</span>
                                    </div>
                                </div>
                            </div>

                            {northStar && (
                                <div className="north-star-section">
                                    <div className="north-star-header">
                                        <Trophy className="north-star-icon" size={20} />
                                        <h2>North Star Vision</h2>
                                        {!isEditingNorthStar && (
                                            <button
                                                className="btn btn-ghost btn-xs"
                                                onClick={() => {
                                                    setEditableNorthStar(northStar.goal_statement)
                                                    setIsEditingNorthStar(true)
                                                }}
                                                style={{ marginLeft: 'auto' }}
                                            >
                                                <Edit2 size={14} />
                                            </button>
                                        )}
                                    </div>
                                    {isEditingNorthStar ? (
                                        <div className="north-star-edit-form">
                                            <textarea
                                                className="input textarea input-sm"
                                                value={editableNorthStar}
                                                onChange={(e) => setEditableNorthStar(e.target.value)}
                                                rows={2}
                                            />
                                            <div className="edit-actions-right" style={{ marginTop: 'var(--space-2)' }}>
                                                <button className="btn btn-ghost btn-sm" onClick={() => setIsEditingNorthStar(false)}>
                                                    Cancel
                                                </button>
                                                <button className="btn btn-primary btn-sm" onClick={saveNorthStar}>
                                                    Save
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <>
                                            <p className="north-star-content">"{northStar.goal_statement}"</p>
                                            <div className="north-star-footer">
                                                <span className="north-star-meta">Target: Dec 31, {new Date().getFullYear()}</span>
                                                <AIFeedback
                                                    contentType="north_star"
                                                    contentId={northStar.id}
                                                    compact={true}
                                                    onRegenerated={(newNS) => setNorthStar(newNS)}
                                                />
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            <div className="daily-action-section">
                                {todayProgress ? (
                                    <div className="today-logged-card">
                                        <CheckCircle size={24} className="logged-icon" />
                                        <div className="logged-content">
                                            <h3>Today's Progress Logged</h3>
                                            <p>{todayProgress.content.slice(0, 100)}...</p>
                                            {!todayProgress.quiz_completed && (
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
                                    <button
                                        className="btn btn-sm btn-secondary"
                                        onClick={handleRefreshRoadmap}
                                        disabled={generating}
                                    >
                                        <RefreshCw size={14} className={generating ? 'animate-spin' : ''} />
                                        Refresh Now
                                    </button>
                                </div>
                            )}

                            <div className="roadmap-section">
                                <div className="section-header">
                                    <div className="section-title-wrap">
                                        <h2>Your Learning Roadmap</h2>
                                        {!isEditingRoadmap && (
                                            <AIFeedback
                                                contentType="roadmap"
                                                contentId={roadmap?.milestones?.[0]?.id || 0}
                                                compact={true}
                                                onRegenerated={(newRoadmap) => {
                                                    setRoadmap(newRoadmap)
                                                    loadData()
                                                }}
                                            />
                                        )}
                                    </div>
                                    {!isEditingRoadmap && (
                                        <button className="btn btn-ghost btn-sm" onClick={startEditing}>
                                            <Edit2 size={16} />
                                            Edit Roadmap
                                        </button>
                                    )}
                                </div>

                                {isEditingRoadmap ? (
                                    <div className="edit-roadmap-form">
                                        {editableMilestones.map((m, index) => (
                                            <div key={m.id} className="edit-milestone-card">
                                                <button
                                                    className="remove-milestone-btn btn-ghost"
                                                    onClick={() => removeMilestone(index)}
                                                >
                                                    <X size={16} />
                                                </button>
                                                <div className="milestone-edit-header">
                                                    <span className="milestone-index">{index + 1}</span>
                                                    <input
                                                        className="input input-sm"
                                                        placeholder="Milestone Title"
                                                        value={m.title}
                                                        onChange={(e) => updateMilestone(index, { title: e.target.value })}
                                                    />
                                                </div>
                                                <textarea
                                                    className="input textarea input-sm"
                                                    placeholder="Description of what you'll learn"
                                                    value={m.description}
                                                    onChange={(e) => updateMilestone(index, { description: e.target.value })}
                                                    rows={2}
                                                />
                                                <div className="input-row">
                                                    <div className="input-group">
                                                        <label className="input-label-sm">Verification Criteria</label>
                                                        <input
                                                            className="input input-sm"
                                                            placeholder="How will you prove it?"
                                                            value={m.verification_criteria}
                                                            onChange={(e) => updateMilestone(index, { verification_criteria: e.target.value })}
                                                        />
                                                    </div>
                                                    <div className="input-group">
                                                        <label className="input-label-sm">Target Date (Optional)</label>
                                                        <input
                                                            type="date"
                                                            className="input input-sm"
                                                            value={m.target_date || ''}
                                                            onChange={(e) => updateMilestone(index, { target_date: e.target.value })}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        ))}

                                        <button className="btn btn-secondary btn-sm" onClick={addMilestone}>
                                            <Plus size={16} />
                                            Add Milestone
                                        </button>

                                        <div className="edit-actions">
                                            <button
                                                className="btn btn-ghost"
                                                onClick={() => setIsEditingRoadmap(false)}
                                                disabled={savingRoadmap}
                                            >
                                                Cancel
                                            </button>
                                            <div className="edit-actions-right">
                                                <button
                                                    className="btn btn-primary"
                                                    onClick={saveManualRoadmap}
                                                    disabled={savingRoadmap}
                                                >
                                                    {savingRoadmap ? (
                                                        <>
                                                            <Loader2 className="animate-spin" size={16} />
                                                            Saving...
                                                        </>
                                                    ) : (
                                                        'Save Roadmap'
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
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
                                )}
                            </div>
                        </>
                    )}
                </div>
            </main>
        </div>
    )
}
