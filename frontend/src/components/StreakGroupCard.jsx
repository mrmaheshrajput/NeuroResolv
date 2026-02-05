import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Link2, Users, UserPlus, X, Check, Loader2, ShieldAlert, LogOut, Plus } from 'lucide-react'
import './StreakGroupCard.css'

export default function StreakGroupCard({ resolutions }) {
    const [loading, setLoading] = useState(true)
    const [group, setGroup] = useState(null)
    const [showCreate, setShowCreate] = useState(false)
    const [memberEmails, setMemberEmails] = useState(['', ''])
    const [validEmails, setValidEmails] = useState([null, null])
    const [validating, setValidating] = useState([false, false])
    const [selectedResId, setSelectedResId] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [isCollapsed, setIsCollapsed] = useState(true)

    useEffect(() => {
        loadGroup()
        if (resolutions && resolutions.length > 0) {
            setSelectedResId(resolutions[0].id)
        }
    }, [resolutions])

    async function loadGroup() {
        setLoading(true)
        try {
            const data = await api.getMyStreakGroup()
            setGroup(data)
        } catch (err) {
            console.error('Failed to load group:', err)
        } finally {
            setLoading(false)
        }
    }

    async function handleEmailChange(index, value) {
        const newEmails = [...memberEmails]
        newEmails[index] = value
        setMemberEmails(newEmails)

        if (value.includes('@') && value.includes('.')) {
            const newValids = [...validating]
            newValids[index] = true
            setValidating(newValids)

            try {
                const res = await api.validateStreakEmail(value)
                const newValidsStatus = [...validEmails]
                newValidsStatus[index] = res.exists
                setValidEmails(newValidsStatus)
            } catch (err) {
                console.error('Email validation error:', err)
            } finally {
                const finishedValids = [...validating]
                finishedValids[index] = false
                setValidating(finishedValids)
            }
        } else {
            const newValidsStatus = [...validEmails]
            newValidsStatus[index] = null
            setValidEmails(newValidsStatus)
        }
    }

    async function handleCreateGroup(e) {
        e.preventDefault()
        const emails = memberEmails.filter(email => email.trim() !== '')
        if (emails.length === 0) {
            setError('Please add at least one member')
            return
        }

        setIsSubmitting(true)
        setError('')
        try {
            await api.createStreakGroup({
                member_emails: emails,
                resolution_id: parseInt(selectedResId)
            })
            await loadGroup()
            setShowCreate(false)
        } catch (err) {
            setError(err.message || 'Failed to create group')
        } finally {
            setIsSubmitting(false)
        }
    }

    async function handleLeaveGroup() {
        if (!group) return
        if (!confirm('Are you sure you want to leave this group? This will deactivate the group for everyone.')) return

        setLoading(true)
        try {
            await api.leaveStreakGroup(group.id)
            setGroup(null)
        } catch (err) {
            alert('Failed to leave group: ' + err.message)
        } finally {
            setLoading(false)
        }
    }

    if (loading && !group) {
        return (
            <div className="streak-group-card loading">
                <Loader2 className="spinner" size={24} />
            </div>
        )
    }

    if (group) {
        return (
            <div
                className={`streak-group-card active ${isCollapsed ? 'collapsed' : ''}`}
                onClick={() => setIsCollapsed(!isCollapsed)}
            >
                <div className="group-card-header">
                    <div className="group-icon">
                        <Link2 size={20} />
                    </div>
                    <div className="group-info">
                        <h3>Streak Squad</h3>
                        {!isCollapsed && <p>{group.members.length} members linked</p>}
                    </div>
                    {isCollapsed && (
                        <div className="tile-status active">
                            <span>Active</span>
                        </div>
                    )}
                </div>

                {!isCollapsed && (
                    <div className="card-content" onClick={e => e.stopPropagation()}>
                        <div className="members-list">
                            {group.members && group.members.map((member, i) => (
                                <div key={member.user_id} className="member-item">
                                    <div className="member-avatar">
                                        {member.full_name ? member.full_name.charAt(0) : '?'}
                                    </div>
                                    <div className="member-details">
                                        <span className="member-name">{member.full_name || 'Group Member'}</span>
                                        <span className="member-streak">{member.current_streak || 0} day streak</span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <button className="btn btn-outline btn-sm leave-btn" onClick={handleLeaveGroup}>
                            <LogOut size={14} />
                            Leave Group
                        </button>
                    </div>
                )}
            </div>
        )
    }

    if (showCreate) {
        return (
            <div className="streak-group-card create">
                <div className="create-header">
                    <h3>Create Streak Group</h3>
                    <button className="close-btn" onClick={() => setShowCreate(false)}>
                        <X size={18} />
                    </button>
                </div>

                <p className="create-description">
                    Link your streak with up to 2 other people. High stakes, high accountability!
                </p>

                <form onSubmit={handleCreateGroup}>
                    <div className="res-select-group">
                        <label>Select Resolution to Link</label>
                        <select
                            value={selectedResId}
                            onChange={(e) => setSelectedResId(e.target.value)}
                            className="form-select"
                            required
                        >
                            {resolutions && resolutions.map(res => (
                                <option key={res.id} value={res.id}>{res.goal_statement}</option>
                            ))}
                        </select>
                    </div>

                    <div className="emails-input-group">
                        <label>Member Emails</label>
                        {memberEmails.map((email, i) => (
                            <div key={i} className="email-input-wrapper">
                                <input
                                    type="email"
                                    placeholder="friend@email.com"
                                    value={email}
                                    onChange={(e) => handleEmailChange(i, e.target.value)}
                                    className={`form-input ${validEmails[i] === false ? 'invalid' : ''}`}
                                />
                                <div className="input-indicator">
                                    {validating[i] && <Loader2 size={14} className="animate-spin" />}
                                    {validEmails[i] === true && <Check size={14} className="text-emerald" />}
                                    {validEmails[i] === false && < ShieldAlert size={14} className="text-red" title="User not found" />}
                                </div>
                            </div>
                        ))}
                    </div>

                    {error && <div className="error-message">{error}</div>}

                    <button className="btn btn-primary w-full" disabled={isSubmitting}>
                        {isSubmitting ? <><Loader2 className="animate-spin" size={16} /> Creating...</> : 'Launch Group Streak'}
                    </button>
                </form>
            </div>
        )
    }

    return (
        <div
            className={`streak-group-card empty ${isCollapsed ? 'collapsed' : ''}`}
            onClick={() => isCollapsed && setIsCollapsed(false)}
        >
            <div
                className="group-card-header"
                onClick={() => !isCollapsed && setIsCollapsed(true)}
                style={{ cursor: isCollapsed ? 'inherit' : 'pointer' }}
            >
                <div className="group-icon empty-state-icon">
                    <Users size={20} />
                </div>
                <div className="group-info">
                    <h3>Streak Squad</h3>
                    {!isCollapsed && <p>Link streaks with friends. If one breaks, all break.</p>}
                </div>
                {isCollapsed && (
                    <div className="tile-action">
                        <Plus size={16} />
                    </div>
                )}
            </div>

            {!isCollapsed && (
                <div className="empty-content" onClick={e => e.stopPropagation()}>
                    <div className="empty-icon-large">
                        <Users size={48} />
                    </div>
                    <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
                        <UserPlus size={18} />
                        Create Linked Group
                    </button>
                </div>
            )}
        </div>
    )
}
