import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Brain, Sparkles, Target, TrendingUp, CheckCircle, Github, Youtube, ArrowRight, Loader2 } from 'lucide-react'
import './LoginPage.css'

export default function LoginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const { login } = useAuth()

    async function handleSubmit(e) {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            await login(email, password)
        } catch (err) {
            setError(err.message || 'Login failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="login-page">
            <div className="login-background">
                <div className="gradient-orb orb-1" />
                <div className="gradient-orb orb-2" />
                <div className="gradient-orb orb-3" />
            </div>

            <div className="login-container">
                <div className="login-hero">
                    <div className="hero-content">
                        <div className="logo animate-fadeIn">
                            <Brain className="logo-icon" />
                            <span className="logo-text">NeuroResolv</span>
                        </div>

                        <h1 className="hero-title animate-fadeIn">
                            Transform Your <span className="text-gradient">Resolutions</span> Into Reality
                        </h1>

                        <p className="hero-description animate-fadeIn">
                            Not just another habit tracker. NeuroResolv is your AI-powered adaptive tutor
                            that learns how you learn and adjusts to help you actually achieve your goals.
                        </p>

                        <div className="features-grid">
                            <div className="feature-card animate-fadeIn">
                                <div className="feature-icon">
                                    <Target />
                                </div>
                                <h3>Dynamic Syllabus</h3>
                                <p>AI creates personalized 30-day learning paths from your materials</p>
                            </div>

                            <div className="feature-card animate-fadeIn" style={{ animationDelay: '0.1s' }}>
                                <div className="feature-icon">
                                    <Sparkles />
                                </div>
                                <h3>Micro-Learning</h3>
                                <p>Daily 30-minute sessions with perfectly chunked content</p>
                            </div>

                            <div className="feature-card animate-fadeIn" style={{ animationDelay: '0.2s' }}>
                                <div className="feature-icon">
                                    <CheckCircle />
                                </div>
                                <h3>Active Recall</h3>
                                <p>AI-generated quizzes test understanding, not just completion</p>
                            </div>

                            <div className="feature-card animate-fadeIn" style={{ animationDelay: '0.3s' }}>
                                <div className="feature-icon">
                                    <TrendingUp />
                                </div>
                                <h3>Adaptive Loop</h3>
                                <p>Struggle with a quiz? Tomorrow's content adapts to reinforce weak areas</p>
                            </div>
                        </div>

                        <div className="hero-links animate-fadeIn" style={{ animationDelay: '0.4s' }}>
                            <a href="https://github.com/mrmaheshrajput/NeuroResolv" target="_blank" rel="noopener noreferrer" className="hero-link">
                                <Github size={20} />
                                View on GitHub
                            </a>
                            <a href="https://www.youtube.com/watch?v=dQw4w9WgXcQ" target="_blank" rel="noopener noreferrer" className="hero-link">
                                <Youtube size={20} />
                                Watch Demo
                            </a>
                        </div>

                        <div className="built-with animate-fadeIn" style={{ animationDelay: '0.5s' }}>
                            <span>Built with</span>
                            <div className="tech-badges">
                                <span className="tech-badge">Google ADK</span>
                                <span className="tech-badge">Gemini 2.0</span>
                                <span className="tech-badge">Opik</span>
                                <span className="tech-badge">FastAPI</span>
                                <span className="tech-badge">React</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="login-form-section">
                    <div className="login-form-container animate-fadeIn">
                        <div className="form-header">
                            <h2>Welcome Back</h2>
                            <p>Sign in to continue your learning journey</p>
                        </div>

                        {error && (
                            <div className="error-message">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="login-form">
                            <div className="input-group">
                                <label htmlFor="email" className="input-label">Email</label>
                                <input
                                    id="email"
                                    type="email"
                                    className="input"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </div>

                            <div className="input-group">
                                <label htmlFor="password" className="input-label">Password</label>
                                <input
                                    id="password"
                                    type="password"
                                    className="input"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </div>

                            <button type="submit" className="btn btn-primary btn-lg w-full" disabled={loading}>
                                {loading ? (
                                    <>
                                        <Loader2 className="animate-spin" size={20} />
                                        Signing in...
                                    </>
                                ) : (
                                    <>
                                        Sign In
                                        <ArrowRight size={20} />
                                    </>
                                )}
                            </button>
                        </form>

                        <div className="form-footer">
                            <p>
                                Don't have an account?{' '}
                                <Link to="/register">Create one free</Link>
                            </p>
                        </div>

                        <div className="demo-credentials">
                            <p>For demo, register a new account or use:</p>
                            <code>demo@neuroresolv.com / demo1234</code>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
