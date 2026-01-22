import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom'
import { api } from '../utils/api'
import {
    ArrowLeft, Mic, MicOff, Send, Clock, BookOpen,
    Loader2, CheckCircle, ChevronRight
} from 'lucide-react'
import './CheckinPage.css'

export default function CheckinPage() {
    const { id } = useParams()
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    const [resolution, setResolution] = useState(null)
    const [content, setContent] = useState('')
    const [sourceRef, setSourceRef] = useState('')
    const [duration, setDuration] = useState(30)
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    const [recording, setRecording] = useState(false)
    const [transcribing, setTranscribing] = useState(false)

    const [progressLog, setProgressLog] = useState(null)
    const [quiz, setQuiz] = useState(null)
    const [answers, setAnswers] = useState({})
    const [quizSubmitting, setQuizSubmitting] = useState(false)
    const [result, setResult] = useState(null)

    const mediaRecorderRef = useRef(null)
    const chunksRef = useRef([])

    useEffect(() => {
        loadData()
    }, [id])

    async function loadData() {
        try {
            const resData = await api.getResolution(id)
            setResolution(resData)

            const verifyLogId = searchParams.get('verify')
            if (verifyLogId) {
                const quizData = await api.generateVerificationQuiz(verifyLogId)
                setQuiz(quizData)
                setProgressLog({ id: parseInt(verifyLogId) })
            }
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

            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
                await transcribeAudio(blob)
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

    async function transcribeAudio(blob) {
        setTranscribing(true)
        try {
            const reader = new FileReader()
            reader.readAsDataURL(blob)
            reader.onloadend = async () => {
                const base64 = reader.result.split(',')[1]
                const result = await api.transcribeVoice(base64)
                setContent(prev => prev + (prev ? '\n' : '') + result.text)
                setTranscribing(false)
            }
        } catch (error) {
            alert('Transcription failed: ' + error.message)
            setTranscribing(false)
        }
    }

    async function handleSubmitProgress() {
        if (!content.trim()) {
            alert('Please describe what you worked on today')
            return
        }

        setSubmitting(true)
        try {
            const log = await api.logProgress(id, {
                content,
                input_type: 'text',
                source_reference: sourceRef || null,
                duration_minutes: duration,
            })
            setProgressLog(log)

            const quizData = await api.generateVerificationQuiz(log.id)
            setQuiz(quizData)
        } catch (error) {
            alert('Failed to log progress: ' + error.message)
        } finally {
            setSubmitting(false)
        }
    }

    async function handleSubmitQuiz() {
        const answerList = Object.entries(answers).map(([qId, answer]) => ({
            question_id: parseInt(qId),
            answer,
        }))

        if (answerList.length < quiz.questions.length) {
            alert('Please answer all questions')
            return
        }

        setQuizSubmitting(true)
        try {
            const resultData = await api.submitVerificationQuiz(quiz.id, answerList)
            setResult(resultData)
        } catch (error) {
            alert('Failed to submit quiz: ' + error.message)
        } finally {
            setQuizSubmitting(false)
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

    if (result) {
        return (
            <div className="checkin-page">
                <div className="result-container">
                    <div className={`result-card ${result.passed ? 'passed' : 'failed'}`}>
                        <div className="result-icon">
                            {result.passed ? '🎉' : '💪'}
                        </div>
                        <h1>{result.passed ? 'Verified!' : 'Keep Going!'}</h1>
                        <div className="result-score">
                            <span className="score-value">{Math.round(result.score)}%</span>
                        </div>
                        <p className="result-message">
                            {result.passed
                                ? "Great job! Your learning has been verified."
                                : "Don't worry! Review the concepts and try again tomorrow."
                            }
                        </p>
                        {result.streak_updated && (
                            <div className="streak-updated">
                                <span>🔥 Streak updated!</span>
                            </div>
                        )}
                        <Link to={`/resolution/${id}`} className="btn btn-primary btn-lg">
                            Back to Resolution
                            <ChevronRight size={20} />
                        </Link>
                    </div>
                </div>
            </div>
        )
    }

    if (quiz) {
        return (
            <div className="checkin-page">
                <header className="page-header">
                    <div className="container">
                        <span className="header-title">Verification Quiz</span>
                    </div>
                </header>

                <main className="page-main">
                    <div className="container quiz-container">
                        <div className="quiz-intro">
                            <h2>Let's verify your learning</h2>
                            <p>Answer these questions based on what you studied today.</p>
                        </div>

                        <div className="questions-list">
                            {quiz.questions.map((q, i) => (
                                <div key={q.id} className="question-card">
                                    <div className="question-header">
                                        <span className="question-number">Q{i + 1}</span>
                                        <span className={`question-type badge badge-${q.question_type === 'teach_back' ? 'warning' : 'primary'}`}>
                                            {q.question_type.replace('_', ' ')}
                                        </span>
                                    </div>
                                    <h3>{q.question_text}</h3>
                                    <textarea
                                        className="input textarea"
                                        placeholder="Your answer..."
                                        value={answers[q.id] || ''}
                                        onChange={(e) => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                                        rows={3}
                                    />
                                </div>
                            ))}
                        </div>

                        <button
                            onClick={handleSubmitQuiz}
                            className="btn btn-primary btn-lg submit-quiz-btn"
                            disabled={quizSubmitting}
                        >
                            {quizSubmitting ? (
                                <>
                                    <Loader2 className="animate-spin" size={20} />
                                    Evaluating...
                                </>
                            ) : (
                                <>
                                    <CheckCircle size={20} />
                                    Submit Answers
                                </>
                            )}
                        </button>
                    </div>
                </main>
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
                <div className="container checkin-container">
                    <div className="checkin-header">
                        <h1>What did you work on today?</h1>
                        <p>Log your progress to verify your learning</p>
                    </div>

                    <div className="checkin-form">
                        <div className="input-group">
                            <label className="input-label">Describe your progress</label>
                            <textarea
                                className="input textarea content-input"
                                placeholder="e.g., Read Chapter 3 of Atomic Habits, pages 45-68. Learned about the habit loop - cue, craving, response, reward..."
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                rows={6}
                            />

                            <div className="voice-controls">
                                {recording ? (
                                    <button onClick={stopRecording} className="btn btn-secondary voice-btn recording">
                                        <MicOff size={18} />
                                        Stop Recording
                                    </button>
                                ) : transcribing ? (
                                    <button className="btn btn-secondary voice-btn" disabled>
                                        <Loader2 className="animate-spin" size={18} />
                                        Transcribing...
                                    </button>
                                ) : (
                                    <button onClick={startRecording} className="btn btn-secondary voice-btn">
                                        <Mic size={18} />
                                        Voice Note
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="input-row">
                            <div className="input-group">
                                <label className="input-label">Source (Optional)</label>
                                <input
                                    className="input"
                                    placeholder="e.g., Atomic Habits, Chapter 3"
                                    value={sourceRef}
                                    onChange={(e) => setSourceRef(e.target.value)}
                                />
                            </div>
                            <div className="input-group">
                                <label className="input-label">Duration</label>
                                <div className="duration-input">
                                    <input
                                        type="number"
                                        className="input"
                                        min={5}
                                        max={180}
                                        value={duration}
                                        onChange={(e) => setDuration(parseInt(e.target.value) || 30)}
                                    />
                                    <span>minutes</span>
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={handleSubmitProgress}
                            className="btn btn-primary btn-lg submit-btn"
                            disabled={submitting || !content.trim()}
                        >
                            {submitting ? (
                                <>
                                    <Loader2 className="animate-spin" size={20} />
                                    Logging Progress...
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
            </main>
        </div>
    )
}
