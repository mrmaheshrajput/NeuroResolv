import { useState } from 'react'
import { ThumbsUp, ThumbsDown, RefreshCw, Loader2, MessageSquare } from 'lucide-react'
import { api } from '../utils/api'
import './AIFeedback.css'

/**
 * AIFeedback - Thumbs up/down feedback component for AI-generated content
 * When user dislikes content, prompts for feedback and offers regeneration with better model
 */
export default function AIFeedback({
    contentType,  // 'weekly_goal', 'north_star', 'roadmap'
    contentId,
    onRegenerated = null,  // Callback when content is regenerated
    compact = false,  // Compact mode for inline use
}) {
    const [rating, setRating] = useState(null)
    const [showFeedbackInput, setShowFeedbackInput] = useState(false)
    const [feedbackText, setFeedbackText] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isRegenerating, setIsRegenerating] = useState(false)
    const [feedbackId, setFeedbackId] = useState(null)
    const [submitted, setSubmitted] = useState(false)

    async function handleRating(newRating) {
        if (submitted) return

        setRating(newRating)

        if (newRating === 'thumbs_up') {
            await submitFeedback(newRating, null)
        } else {
            setShowFeedbackInput(true)
        }
    }

    async function submitFeedback(ratingValue, text) {
        setIsSubmitting(true)
        try {
            const response = await api.submitAIFeedback({
                content_type: contentType,
                content_id: contentId,
                rating: ratingValue,
                feedback_text: text,
            })
            setFeedbackId(response.id)
            setSubmitted(true)

            if (ratingValue === 'thumbs_up') {
                setTimeout(() => {
                    setShowFeedbackInput(false)
                }, 1500)
            }
        } catch (error) {
            console.error('Failed to submit feedback:', error)
        } finally {
            setIsSubmitting(false)
        }
    }

    async function handleSubmitNegativeFeedback(e) {
        e.preventDefault()
        await submitFeedback('thumbs_down', feedbackText)
    }

    async function handleRegenerate() {
        if (!feedbackId) return

        setIsRegenerating(true)
        try {
            const result = await api.regenerateFromFeedback(feedbackId)
            if (onRegenerated) {
                onRegenerated(result.new_content)
            }
            // Reset state after successful regeneration
            setRating(null)
            setShowFeedbackInput(false)
            setFeedbackText('')
            setFeedbackId(null)
            setSubmitted(false)
        } catch (error) {
            console.error('Failed to regenerate:', error)
        } finally {
            setIsRegenerating(false)
        }
    }

    if (compact && !showFeedbackInput) {
        return (
            <div className="ai-feedback compact">
                <button
                    className={`feedback-btn ${rating === 'thumbs_up' ? 'active' : ''}`}
                    onClick={() => handleRating('thumbs_up')}
                    disabled={isSubmitting || submitted}
                    title="Like this"
                >
                    <ThumbsUp size={14} />
                </button>
                <button
                    className={`feedback-btn ${rating === 'thumbs_down' ? 'active' : ''}`}
                    onClick={() => handleRating('thumbs_down')}
                    disabled={isSubmitting || submitted}
                    title="Could be better"
                >
                    <ThumbsDown size={14} />
                </button>
            </div>
        )
    }

    return (
        <div className="ai-feedback">
            {!showFeedbackInput && (
                <div className="feedback-prompt">
                    <span className="prompt-text">Was this helpful?</span>
                    <div className="feedback-buttons">
                        <button
                            className={`feedback-btn ${rating === 'thumbs_up' ? 'active success' : ''}`}
                            onClick={() => handleRating('thumbs_up')}
                            disabled={isSubmitting || submitted}
                        >
                            <ThumbsUp size={16} />
                            {rating === 'thumbs_up' && submitted && <span>Thanks!</span>}
                        </button>
                        <button
                            className={`feedback-btn ${rating === 'thumbs_down' ? 'active' : ''}`}
                            onClick={() => handleRating('thumbs_down')}
                            disabled={isSubmitting || submitted}
                        >
                            <ThumbsDown size={16} />
                        </button>
                    </div>
                </div>
            )}

            {showFeedbackInput && !submitted && (
                <form className="feedback-form" onSubmit={handleSubmitNegativeFeedback}>
                    <div className="form-header">
                        <MessageSquare size={16} />
                        <span>What could be better?</span>
                    </div>
                    <textarea
                        value={feedbackText}
                        onChange={(e) => setFeedbackText(e.target.value)}
                        placeholder="Tell us what you'd prefer (optional but helpful)"
                        rows={2}
                    />
                    <div className="form-actions">
                        <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => {
                                setShowFeedbackInput(false)
                                setRating(null)
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? <Loader2 className="animate-spin" size={14} /> : 'Submit'}
                        </button>
                    </div>
                </form>
            )}

            {submitted && rating === 'thumbs_down' && (
                <div className="regeneration-offer">
                    <p>Thanks for your feedback!</p>
                    <button
                        className="regenerate-btn"
                        onClick={handleRegenerate}
                        disabled={isRegenerating}
                    >
                        {isRegenerating ? (
                            <>
                                <Loader2 className="animate-spin" size={14} />
                                <span>Regenerating...</span>
                            </>
                        ) : (
                            <>
                                <RefreshCw size={14} />
                                <span>Try a new suggestion</span>
                            </>
                        )}
                    </button>
                </div>
            )}
        </div>
    )
}
