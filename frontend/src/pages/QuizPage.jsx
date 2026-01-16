import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../utils/api'
import {
    ArrowLeft, CheckCircle, XCircle, AlertTriangle,
    Loader2, Trophy, ArrowRight, RefreshCw
} from 'lucide-react'
import './QuizPage.css'

export default function QuizPage() {
    const { sessionId } = useParams()
    const navigate = useNavigate()
    const [quiz, setQuiz] = useState(null)
    const [session, setSession] = useState(null)
    const [loading, setLoading] = useState(true)
    const [answers, setAnswers] = useState({})
    const [submitting, setSubmitting] = useState(false)
    const [result, setResult] = useState(null)
    const [currentQuestion, setCurrentQuestion] = useState(0)

    useEffect(() => {
        loadQuiz()
    }, [sessionId])

    async function loadQuiz() {
        try {
            const [quizData, sessionData] = await Promise.all([
                api.getQuiz(sessionId),
                api.getSession(sessionId),
            ])
            setQuiz(quizData)
            setSession(sessionData)
        } catch (error) {
            console.error('Failed to load quiz:', error)
        } finally {
            setLoading(false)
        }
    }

    function handleAnswer(questionId, answer) {
        setAnswers(prev => ({
            ...prev,
            [questionId]: answer,
        }))
    }

    async function handleSubmit() {
        const answerArray = Object.entries(answers).map(([questionId, answer]) => ({
            question_id: parseInt(questionId),
            answer: answer,
        }))

        if (answerArray.length < quiz.questions.length) {
            alert('Please answer all questions before submitting.')
            return
        }

        setSubmitting(true)
        try {
            const resultData = await api.submitQuiz(sessionId, answerArray)
            setResult(resultData)
        } catch (error) {
            alert('Failed to submit quiz: ' + error.message)
        } finally {
            setSubmitting(false)
        }
    }

    if (loading) {
        return (
            <div className="quiz-page">
                <div className="loading-container">
                    <Loader2 className="spinner" size={48} />
                    <p>Generating your quiz...</p>
                </div>
            </div>
        )
    }

    if (!quiz) {
        return (
            <div className="quiz-page">
                <div className="error-container">
                    <h2>Quiz not found</h2>
                    <Link to="/dashboard" className="btn btn-primary">
                        Back to Dashboard
                    </Link>
                </div>
            </div>
        )
    }

    if (result) {
        return (
            <div className="quiz-page">
                <div className="result-container">
                    <div className={`result-card ${result.passed ? 'passed' : 'failed'}`}>
                        <div className="result-icon">
                            {result.passed ? (
                                <Trophy size={64} />
                            ) : (
                                <AlertTriangle size={64} />
                            )}
                        </div>

                        <h1>{result.passed ? 'Congratulations! 🎉' : 'Keep Learning! 💪'}</h1>

                        <div className="result-score">
                            <span className="score-value">{Math.round(result.score)}%</span>
                            <span className="score-label">
                                {result.correct_answers} of {result.total_questions} correct
                            </span>
                        </div>

                        {result.passed ? (
                            <p className="result-message">
                                You've demonstrated a solid understanding of today's material.
                                You're ready to move on to the next day!
                            </p>
                        ) : (
                            <p className="result-message">
                                Don't worry! Learning takes time. The concepts you struggled with
                                will be reinforced in your next session.
                            </p>
                        )}

                        {result.weak_concepts && result.weak_concepts.length > 0 && (
                            <div className="weak-concepts-result">
                                <h3>
                                    <RefreshCw size={18} />
                                    Concepts to Reinforce
                                </h3>
                                <div className="concepts-list">
                                    {result.weak_concepts.map((concept, i) => (
                                        <span key={i} className="concept-chip">{concept}</span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="result-actions">
                            <Link to="/dashboard" className="btn btn-primary btn-lg">
                                Back to Dashboard
                                <ArrowRight size={20} />
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    const question = quiz.questions[currentQuestion]
    const totalQuestions = quiz.questions.length
    const answeredCount = Object.keys(answers).length

    return (
        <div className="quiz-page">
            <header className="quiz-header">
                <div className="container">
                    <div className="quiz-info">
                        <span className="quiz-title">Quiz: {session?.title}</span>
                        <span className="quiz-progress">
                            Question {currentQuestion + 1} of {totalQuestions}
                        </span>
                    </div>
                </div>
            </header>

            <div className="quiz-progress-bar">
                <div
                    className="quiz-progress-fill"
                    style={{ width: `${((currentQuestion + 1) / totalQuestions) * 100}%` }}
                />
            </div>

            <main className="quiz-main">
                <div className="container">
                    <div className="question-card">
                        <div className="question-header">
                            <span className={`question-type badge badge-${question.question_type === 'multiple_choice' ? 'primary' :
                                    question.question_type === 'true_false' ? 'warning' : 'success'
                                }`}>
                                {question.question_type.replace('_', ' ')}
                            </span>
                            <span className={`difficulty badge badge-${question.difficulty === 'easy' ? 'success' :
                                    question.difficulty === 'medium' ? 'warning' : 'danger'
                                }`}>
                                {question.difficulty}
                            </span>
                        </div>

                        <h2 className="question-text">{question.question_text}</h2>

                        <div className="answer-section">
                            {question.question_type === 'multiple_choice' && question.options && (
                                <div className="options-grid">
                                    {question.options.map((option, i) => (
                                        <button
                                            key={i}
                                            className={`option-btn ${answers[question.id] === option ? 'selected' : ''}`}
                                            onClick={() => handleAnswer(question.id, option)}
                                        >
                                            <span className="option-letter">{String.fromCharCode(65 + i)}</span>
                                            <span className="option-text">{option}</span>
                                            {answers[question.id] === option && <CheckCircle size={20} />}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {question.question_type === 'true_false' && (
                                <div className="options-grid two-col">
                                    {['True', 'False'].map((option) => (
                                        <button
                                            key={option}
                                            className={`option-btn ${answers[question.id] === option.toLowerCase() ? 'selected' : ''}`}
                                            onClick={() => handleAnswer(question.id, option.toLowerCase())}
                                        >
                                            <span className="option-text">{option}</span>
                                            {answers[question.id] === option.toLowerCase() && <CheckCircle size={20} />}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {question.question_type === 'short_answer' && (
                                <textarea
                                    className="input textarea short-answer"
                                    placeholder="Type your answer here..."
                                    value={answers[question.id] || ''}
                                    onChange={(e) => handleAnswer(question.id, e.target.value)}
                                />
                            )}
                        </div>
                    </div>

                    <div className="quiz-navigation">
                        <button
                            className="btn btn-secondary"
                            onClick={() => setCurrentQuestion(prev => Math.max(0, prev - 1))}
                            disabled={currentQuestion === 0}
                        >
                            Previous
                        </button>

                        <div className="question-dots">
                            {quiz.questions.map((q, i) => (
                                <button
                                    key={i}
                                    className={`dot ${i === currentQuestion ? 'active' : ''} ${answers[q.id] ? 'answered' : ''}`}
                                    onClick={() => setCurrentQuestion(i)}
                                >
                                    {answers[q.id] && <CheckCircle size={12} />}
                                </button>
                            ))}
                        </div>

                        {currentQuestion < totalQuestions - 1 ? (
                            <button
                                className="btn btn-primary"
                                onClick={() => setCurrentQuestion(prev => Math.min(totalQuestions - 1, prev + 1))}
                            >
                                Next
                                <ArrowRight size={18} />
                            </button>
                        ) : (
                            <button
                                className="btn btn-primary"
                                onClick={handleSubmit}
                                disabled={submitting || answeredCount < totalQuestions}
                            >
                                {submitting ? (
                                    <>
                                        <Loader2 className="animate-spin" size={18} />
                                        Submitting...
                                    </>
                                ) : (
                                    <>
                                        Submit Quiz
                                        <CheckCircle size={18} />
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </main>
        </div>
    )
}
