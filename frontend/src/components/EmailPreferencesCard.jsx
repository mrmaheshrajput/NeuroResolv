import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Mail, Globe, Clock, Loader2, Check, X, Bell, BellOff } from 'lucide-react'
import './EmailPreferencesCard.css'

// Common timezones grouped by region
const TIMEZONE_OPTIONS = [
    { group: 'Americas', zones: [
        { value: 'America/New_York', label: 'New York (EST/EDT)' },
        { value: 'America/Chicago', label: 'Chicago (CST/CDT)' },
        { value: 'America/Denver', label: 'Denver (MST/MDT)' },
        { value: 'America/Los_Angeles', label: 'Los Angeles (PST/PDT)' },
        { value: 'America/Sao_Paulo', label: 'São Paulo (BRT)' },
    ]},
    { group: 'Europe', zones: [
        { value: 'Europe/London', label: 'London (GMT/BST)' },
        { value: 'Europe/Paris', label: 'Paris (CET/CEST)' },
        { value: 'Europe/Berlin', label: 'Berlin (CET/CEST)' },
        { value: 'Europe/Moscow', label: 'Moscow (MSK)' },
    ]},
    { group: 'Asia', zones: [
        { value: 'Asia/Dubai', label: 'Dubai (GST)' },
        { value: 'Asia/Kolkata', label: 'India (IST)' },
        { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
        { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
        { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
    ]},
    { group: 'Pacific', zones: [
        { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
        { value: 'Pacific/Auckland', label: 'Auckland (NZST/NZDT)' },
    ]},
    { group: 'Other', zones: [
        { value: 'UTC', label: 'UTC' },
    ]},
]

// Hour options in 12-hour format
const HOUR_OPTIONS = [
    { value: 0, label: 'Midnight' },
    { value: 1, label: '1 AM' },
    { value: 2, label: '2 AM' },
    { value: 3, label: '3 AM' },
    { value: 4, label: '4 AM' },
    { value: 5, label: '5 AM' },
    { value: 6, label: '6 AM' },
    { value: 7, label: '7 AM' },
    { value: 8, label: '8 AM' },
    { value: 9, label: '9 AM' },
    { value: 10, label: '10 AM' },
    { value: 11, label: '11 AM' },
    { value: 12, label: 'Noon' },
    { value: 13, label: '1 PM' },
    { value: 14, label: '2 PM' },
    { value: 15, label: '3 PM' },
    { value: 16, label: '4 PM' },
    { value: 17, label: '5 PM' },
    { value: 18, label: '6 PM' },
    { value: 19, label: '7 PM' },
    { value: 20, label: '8 PM' },
    { value: 21, label: '9 PM' },
    { value: 22, label: '10 PM' },
    { value: 23, label: '11 PM' },
]

export default function EmailPreferencesCard() {
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [preferences, setPreferences] = useState(null)
    const [isEnabled, setIsEnabled] = useState(false)
    const [timezone, setTimezone] = useState('')
    const [preferredHour, setPreferredHour] = useState(9)
    const [hasChanges, setHasChanges] = useState(false)
    const [showSuccess, setShowSuccess] = useState(false)

    useEffect(() => {
        loadPreferences()
        // Try to detect user's timezone
        const detectedTz = Intl.DateTimeFormat().resolvedOptions().timeZone
        if (detectedTz) {
            setTimezone(detectedTz)
        }
    }, [])

    async function loadPreferences() {
        try {
            const data = await api.getEmailPreferences()
            if (data) {
                setPreferences(data)
                setIsEnabled(data.email_opt_in)
                setTimezone(data.timezone || timezone)
                setPreferredHour(data.preferred_hour)
            }
        } catch (error) {
            console.error('Failed to load email preferences:', error)
        } finally {
            setLoading(false)
        }
    }

    function handleToggle() {
        setIsEnabled(!isEnabled)
        setHasChanges(true)
    }

    function handleTimezoneChange(e) {
        setTimezone(e.target.value)
        setHasChanges(true)
    }

    function handleHourChange(e) {
        setPreferredHour(parseInt(e.target.value))
        setHasChanges(true)
    }

    async function handleSave() {
        setSaving(true)
        try {
            if (isEnabled) {
                await api.updateEmailPreferences({
                    email_opt_in: true,
                    timezone,
                    preferred_hour: preferredHour,
                })
            } else {
                await api.deleteEmailPreferences()
            }
            setHasChanges(false)
            setShowSuccess(true)
            setTimeout(() => setShowSuccess(false), 3000)
            await loadPreferences()
        } catch (error) {
            console.error('Failed to save preferences:', error)
        } finally {
            setSaving(false)
        }
    }

    function handleCancel() {
        if (preferences) {
            setIsEnabled(preferences.email_opt_in)
            setTimezone(preferences.timezone)
            setPreferredHour(preferences.preferred_hour)
        } else {
            setIsEnabled(false)
        }
        setHasChanges(false)
    }

    if (loading) {
        return (
            <div className="email-prefs-card loading">
                <Loader2 className="spinner" size={24} />
            </div>
        )
    }

    return (
        <div className="email-prefs-card">
            <div className="email-prefs-header">
                <div className="email-prefs-icon">
                    <Mail size={20} />
                </div>
                <div className="email-prefs-title">
                    <h3>Email Reflections</h3>
                    <p>Personalized insights about your learning journey</p>
                </div>
            </div>

            <div className="email-prefs-toggle">
                <div className="toggle-info">
                    {isEnabled ? (
                        <>
                            <Bell size={18} className="toggle-icon enabled" />
                            <span>Emails enabled</span>
                        </>
                    ) : (
                        <>
                            <BellOff size={18} className="toggle-icon disabled" />
                            <span>Emails disabled</span>
                        </>
                    )}
                </div>
                <button
                    className={`toggle-switch ${isEnabled ? 'active' : ''}`}
                    onClick={handleToggle}
                    aria-label="Toggle email notifications"
                >
                    <span className="toggle-knob" />
                </button>
            </div>

            {isEnabled && (
                <div className="email-prefs-settings">
                    <div className="setting-row">
                        <div className="setting-label">
                            <Globe size={16} />
                            <span>Timezone</span>
                        </div>
                        <select
                            className="setting-select"
                            value={timezone}
                            onChange={handleTimezoneChange}
                        >
                            {TIMEZONE_OPTIONS.map(group => (
                                <optgroup key={group.group} label={group.group}>
                                    {group.zones.map(tz => (
                                        <option key={tz.value} value={tz.value}>
                                            {tz.label}
                                        </option>
                                    ))}
                                </optgroup>
                            ))}
                        </select>
                    </div>

                    <div className="setting-row">
                        <div className="setting-label">
                            <Clock size={16} />
                            <span>Preferred time</span>
                        </div>
                        <select
                            className="setting-select"
                            value={preferredHour}
                            onChange={handleHourChange}
                        >
                            {HOUR_OPTIONS.map(hour => (
                                <option key={hour.value} value={hour.value}>
                                    {hour.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <p className="email-prefs-hint">
                        You'll receive thoughtful emails about your streaks, milestones, and learning progress.
                    </p>
                </div>
            )}

            {hasChanges && (
                <div className="email-prefs-actions">
                    <button
                        className="btn btn-ghost btn-sm"
                        onClick={handleCancel}
                        disabled={saving}
                    >
                        Cancel
                    </button>
                    <button
                        className="btn btn-primary btn-sm"
                        onClick={handleSave}
                        disabled={saving}
                    >
                        {saving ? (
                            <>
                                <Loader2 className="animate-spin" size={16} />
                                Saving...
                            </>
                        ) : (
                            <>
                                <Check size={16} />
                                Save
                            </>
                        )}
                    </button>
                </div>
            )}

            {showSuccess && (
                <div className="email-prefs-success">
                    <Check size={16} />
                    <span>Preferences saved!</span>
                </div>
            )}
        </div>
    )
}
