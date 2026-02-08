# NeuroResolv Tasks ⚙️

Background intelligence and maintenance operations for the NeuroResolv ecosystem.

## Key Operations

### 📧 Email Reflections
The `email_reflection_agent` handles periodic outreach based on user lifecycle triggers (Inactivity, Milestone Completion, Streak Break).

### 🎯 Roadmap Refresh (Weekly)
Trigger the NeuroResolv API to identify and refresh roadmaps that are due. The AI agent will auto-evolve roadmaps based on user progress logs and streak data.

### 🔄 Prompt Optimization (Weekly)
A scheduled process that leverages the `MetaPromptOptimizer` from Opik. It retrieves user feedback (Thumbs Down) from the past week and automatically generates refined system prompts for our Roadmap and Negotiation agents.

## 🚀 Potential Extensions
- **Batch Processing:** Analyzing long-form video check-ins for deeper sentiment analysis.
- **Predictive Health:** Flagging resolutions at high risk of failure based on early engagement patterns.
