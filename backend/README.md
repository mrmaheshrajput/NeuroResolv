# NeuroResolv Backend 🧠⚙️

The engine room of NeuroResolv, powered by FastAPI and Google Gemini, with deep observability through Opik.

## 🚀 Technical Highlights

- **FastAPI Core:** High-performance asynchronous API handling for resolutions, check-ins, and user management.
- **Agentic Logic:** Orchestrated LLM calls using the Gemini 2.5 series for complex decision-making.
- **Deep Observability:** Custom decorators and middleware to trace every LLM interaction via Opik.
- **Automated Refinement:** Integrated MetaPromptOptimizer logic for feedback-driven system improvements.

## 📂 Architecture

### [Agents](file:///Users/mahesh/US/NeuroResolv/backend/app/agents)
The core intelligence of the app:
- `negotiation_agent.py`: Challenges unrealistic user goals and suggests sustainable cadences.
- `roadmap_agent.py`: Generates structured, multi-milestone growth plans.
- `checkin_agent.py`: Processes multi-modal (text/audio/video) progress logs.
- `email_reflection_agent.py`: Handles high-impact user communications.

### [Observability](file:///Users/mahesh/US/NeuroResolv/backend/app/observability)
- `opik_integration.py`: The heart of our Best Use of Opik submission. Contains logic for tracing, evaluation, and the automatic prompt optimization "Data Flywheel".

## 🛠️ Performance & Security
- **Latency Insensitive Prompts:** Stored and versioned in Opik Cloud for rapid iteration without code changes.
- **Slack Alerts:** Real-time monitoring of budget, latency, and error rates via Opik integrations.
- **PostgreSQL:** Reliable persistence for user data, resolutions, and system states.

## 🔧 Development

```bash
# Start postgres container
docker run -e POSTGRES_PASSWORD=postgres -dp 5432:5432 postgres:16

# Install dependencies
poetry install

# Run migration
poetry run alembic upgrade head

# Start development server
poetry run uvicorn main:app --reload
```
