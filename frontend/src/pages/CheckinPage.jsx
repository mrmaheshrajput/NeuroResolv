import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../utils/api'
import {
    ArrowLeft, Mic, MicOff, Send, Loader2, ChevronRight,
    Upload, X, Camera, FileVideo, PenTool, Image as ImageIcon,
    Shield, CheckCircle, Brain
} from 'lucide-react'
import './CheckinPage.css'

export default function CheckinPage() {
    const { id } = useParams()
    const navigate = useNavigate()

    const [resolution, setResolution] = useState(null)
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    const [resultLog, setResultLog] = useState(null)

    // Form inputs
    const [activeTab, setActiveTab] = useState('media') // Default to media as requested
    const [content, setContent] = useState('')
    const [file, setFile] = useState(null)
    const [filePreview, setFilePreview] = useState(null)
    const [duration, setDuration] = useState(30)

    // Voice
    const [recording, setRecording] = useState(false)
    const mediaRecorderRef = useRef(null)
    const chunksRef = useRef([])
    const fileInputRef = useRef(null)

    useEffect(() => {
        loadData()
        return () => {
            if (filePreview) URL.revokeObjectURL(filePreview)
        }
    }, [id])

    async function loadData() {
        try {
            const resData = await api.getResolution(id)
            setResolution(resData)
        } catch (error) {
            console.error('Failed to load:', error)
        } finally {
            setLoading(false)
        }
    }

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const mediaRecorder = new MediaRecorder(stream)
            mediaRecorderRef.current = mediaRecorder
            chunksRef.current = []

            mediaRecorder.ondataavailable = (e) => {
                chunksRef.current.push(e.data)
            }

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
                const audioFile = new File([blob], "voice_note.webm", { type: 'audio/webm' })

                // Set as current file
                setFile(audioFile)
                setFilePreview(URL.createObjectURL(blob))

                stream.getTracks().forEach(track => track.stop())
            }

            mediaRecorder.start()
            setRecording(true)
        } catch (error) {
            alert('Could not access microphone: ' + error.message)
        }
    }

    function stopRecording() {
        if (mediaRecorderRef.current) {
            mediaRecorderRef.current.stop()
            setRecording(false)
        }
    }

    function handleFileSelect(e) {
        const selectedFile = e.target.files[0]
        if (selectedFile) {
            setFile(selectedFile)
            setFilePreview(URL.createObjectURL(selectedFile))
        }
    }

    function clearFile() {
        setFile(null)
        setFilePreview(null)
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    async function handleSubmit() {
        const isVoiceNote = activeTab === 'text' && file?.type?.startsWith('audio');

        if (activeTab === 'text' && !content.trim() && !isVoiceNote) {
            alert('Please describe your progress or record a voice note')
            return
        }
        if (activeTab === 'media' && !file) {
            alert('Please select an image or video to upload')
            return
        }

        setSubmitting(true)
        try {
            const formData = new FormData()

            // Determine input type
            let inputType = 'text'
            if (activeTab === 'media') {
                inputType = file.type.startsWith('video') ? 'video' : 'image'
            } else if (isVoiceNote) {
                inputType = 'audio'
            }

            formData.append('input_type', inputType)

            if (content.trim()) {
                formData.append('content', content)
            } else {
                // If no text but file exists (audio/image), we send descriptive dummy text or leave empty logic to backend
                // Backend uses 'content' argument for text, checks 'file' argument for media
            }

            if (file) {
                formData.append('file', file)
            }

            if (duration) {
                formData.append('duration_minutes', duration)
            }

            const log = await api.logCheckin(id, formData)
            setResultLog(log)

        } catch (error) {
            alert('Failed to log progress: ' + error.message)
            console.error(error)
        } finally {
            setSubmitting(false)
        }
    }

    if (loading) {
        return (
            <div className="checkin-page">
                <div className="loading-container">
                    <Loader2 className="spinner" size={48} />
                </div>
            </div>
        )
    }

    if (resultLog) {
        return (
            <div className="checkin-page">
                <header className="page-header">
                    <div className="container">
                        <Link to={`/resolution/${id}`} className="back-link">
                            <ArrowLeft size={18} />
                            Back to Resolution
                        </Link>
                    </div>
                </header>
                <div className="result-container">
                    <div className="result-logo">
                        <Brain className="logo-icon" />
                        <span className="logo-text">NeuroResolv</span>
                    </div>
                    <div className="result-card passed">
                        <div className="result-icon">
                            ✨
                        </div>
                        <h1>Check-in Completed!</h1>

                        <div className="reflection-box">
                            <div className="quote-icon-top">“</div>
                            <p className="reflection-text">
                                {resultLog.ai_reflection || "Great job logging your progress today!"}
                            </p>
                        </div>

                        <div className="streak-animation">
                            <span>🔥 Streak extended!</span>
                        </div>

                        <Link to={`/resolution/${id}`} className="continue-btn">
                            Continue Journey
                            <ChevronRight size={20} />
                        </Link>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="checkin-page">
            <header className="page-header">
                <div className="container">
                    <Link to={`/resolution/${id}`} className="back-link">
                        <ArrowLeft size={18} />
                        Back
                    </Link>
                </div>
            </header>

            <main className="page-main">
                <div className="checkin-container">
                    <div className="checkin-header">
                        <h1>Check In</h1>
                        <p>Share your progress to keep your streak alive</p>
                    </div>

                    <div className="checkin-card">
                        <div className="tabs">
                            <button
                                className={`tab-btn ${activeTab === 'media' ? 'active' : ''}`}
                                onClick={() => setActiveTab('media')}
                            >
                                <ImageIcon size={20} />
                                Camera / Upload
                            </button>
                            <button
                                className={`tab-btn ${activeTab === 'text' ? 'active' : ''}`}
                                onClick={() => setActiveTab('text')}
                            >
                                <PenTool size={20} />
                                Write
                            </button>
                        </div>

                        <div className="checkin-form">
                            {activeTab === 'text' ? (
                                <div className="input-group">
                                    <label className="input-label">What did you accomplish today?</label>
                                    <textarea
                                        className="input textarea"
                                        placeholder="Type your progress here..."
                                        value={content}
                                        onChange={(e) => setContent(e.target.value)}
                                        rows={6}
                                    />

                                    {/* Voice Note Preview in Text Tab */}
                                    {file && file.type.startsWith('audio') && (
                                        <div className="file-preview" style={{ marginTop: '1rem', background: '#334155' }}>
                                            <audio src={filePreview} controls style={{ width: '100%' }} />
                                            <button onClick={clearFile} className="remove-file-btn">
                                                <X size={16} />
                                            </button>
                                        </div>
                                    )}

                                    <div className="voice-controls">
                                        <span style={{ marginRight: 'auto', fontSize: '0.85rem', color: '#64748B', alignSelf: 'center' }}>
                                            {recording ? "Recording..." : "Or use voice note"}
                                        </span>

                                        {recording ? (
                                            <button onClick={stopRecording} className="voice-btn recording">
                                                <MicOff size={18} />
                                                Stop Recording
                                            </button>
                                        ) : (
                                            <button onClick={startRecording} className="voice-btn">
                                                <Mic size={18} />
                                                {file && file.type.startsWith('audio') ? "Record Again" : "Voice Note"}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="input-group">
                                    <label className="input-label">Upload Evidence</label>
                                    {!file || (file.type.startsWith('audio')) ? (
                                        <div
                                            className="file-upload-area"
                                            onClick={() => fileInputRef.current.click()}
                                        >
                                            <input
                                                type="file"
                                                ref={fileInputRef}
                                                accept="image/*,video/*"
                                                onChange={handleFileSelect}
                                            />
                                            <div className="upload-placeholder">
                                                <div className="icon-wrapper">
                                                    <Camera size={40} color="#94A3B8" />
                                                </div>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                    <span style={{ fontSize: '1.1rem', fontWeight: 600, color: '#E2E8F0' }}>Click to upload</span>
                                                    <span style={{ fontSize: '0.9rem' }}>Image or Video</span>
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="file-preview">
                                            {file.type.startsWith('video') ? (
                                                <video src={filePreview} controls />
                                            ) : (
                                                <img src={filePreview} alt="Preview" />
                                            )}
                                            <button onClick={clearFile} className="remove-file-btn">
                                                <X size={20} />
                                            </button>
                                        </div>
                                    )}
                                    <div className="privacy-note">
                                        <Shield size={14} />
                                        <span>Your media is analyzed by AI and <strong>NOT stored</strong>.</span>
                                    </div>
                                    <div className="upload-warning">
                                        <FileVideo size={16} />
                                        <span>Videos longer than 3 mins will be truncated.</span>
                                    </div>
                                </div>
                            )}

                            <div className="optional-section">
                                <div className="input-group">
                                    <label className="input-label">Time Spent (Optional)</label>
                                    <div className="duration-input">
                                        <input
                                            type="number"
                                            className="input"
                                            min={0}
                                            max={180}
                                            value={duration}
                                            onChange={(e) => setDuration(parseInt(e.target.value) || 0)}
                                        />
                                        <span>minutes</span>
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={handleSubmit}
                                className="btn btn-primary btn-lg submit-btn"
                                disabled={submitting || (activeTab === 'text' && !content.trim() && !file) || (activeTab === 'media' && !file)}
                            >
                                {submitting ? (
                                    <>
                                        <Loader2 className="animate-spin" size={24} />
                                        AI Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <Send size={20} />
                                        Log Progress & Verify
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}
