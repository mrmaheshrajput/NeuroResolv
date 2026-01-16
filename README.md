# NeuroResolv 🧠✨

**Adaptive AI Tutor & Accountability Partner for New Year Resolutions**

Transform your New Year's resolutions from simple task tracking into genuine learning journeys with AI-powered adaptive tutoring.

![NeuroResolv Banner](https://via.placeholder.com/800x400/1a1a2e/8b5cf6?text=NeuroResolv)

## 🎯 The Problem

Most resolution apps are just "tick-box" trackers. They tell you IF you did something, not if you LEARNED anything. NeuroResolv changes that.

## ✨ Key Features

### 🎓 Dynamic Syllabus Generation
Upload your learning materials (PDFs, EPUBs, text files), and our AI creates a personalized 30-day curriculum tailored to your goal.

### 📖 Micro-Learning Sessions
Daily 30-minute sessions with perfectly chunked content. No overwhelming walls of text—just digestible, focused learning.

### 🧪 Active Recall Engine
After each session, take an AI-generated quiz that tests genuine understanding, not just memorization.

### 🔄 The Adaptive Loop (Our Secret Sauce)
**This is what makes NeuroResolv different:**
- Fail a quiz? Tomorrow's content automatically adapts to reinforce your weak concepts
- We don't just track IF you did it—we track if you LEARNED it
- Personalized reinforcement sessions when you struggle

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React + Vite | Modern SPA with stunning UI |
| **Backend** | FastAPI | Async Python API with auto-docs |
| **AI Agents** | Google ADK | Multi-agent orchestration |
| **LLM** | Gemini 2.0 Flash | Fast, capable foundation model |
| **Vector DB** | ChromaDB | RAG for learning content |
| **Database** | SQLite/PostgreSQL | User data and history |
| **Observability** | Opik by Comet | LLM tracing and evaluation |

## 🚀 Quick Start

### Prerequisites
- Python 3.12
- Node.js 20+
- Docker & Docker Compose (optional but recommended)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/neuroresolv.git
cd neuroresolv

# Create your .env file
cp backend/.env.example backend/.env
# Edit backend/.env and add your API keys

# Start everything
docker-compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Manual Setup

#### Backend
```bash
cd backend

# Install Poetry if you haven't
pip install poetry

# Install dependencies
poetry install

# Create and configure .env
cp .env.example .env
# Add your GOOGLE_API_KEY and OPIK_API_KEY

# Run the server
poetry run uvicorn main:app --reload

# API available at http://localhost:8000
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# App available at http://localhost:3000
```

## 🔑 Configuration

Create a `backend/.env` file with your credentials:

```env
# Required for AI features
GOOGLE_API_KEY=your-gemini-api-key

# Required for LLM observability
OPIK_API_KEY=your-opik-api-key
OPIK_WORKSPACE=default
OPIK_PROJECT_NAME=neuroresolv

# Database (SQLite by default, or PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///./neuroresolv.db

# Security
SECRET_KEY=your-production-secret-key
```

## 📊 Opik Integration

NeuroResolv deeply integrates Opik for LLM observability:

- **Trace all LLM calls**: Every agent interaction is traced
- **Evaluate quiz quality**: Custom metrics for assessing AI-generated quizzes
- **Monitor adaptive decisions**: Track when and why the system adapts
- **Learning progression analytics**: Correlate quiz performance with content changes

## 🏗️ Project Structure

```
neuroresolv/
├── backend/
│   ├── app/
│   │   ├── agents/          # Google ADK agents
│   │   │   ├── syllabus_agent.py
│   │   │   ├── quiz_agent.py
│   │   │   └── adaptive_agent.py
│   │   ├── api/             # FastAPI routers
│   │   ├── db/              # Database models
│   │   ├── services/        # Business logic
│   │   └── observability/   # Opik integration
│   ├── main.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   ├── contexts/        # Auth context
│   │   └── utils/           # API client
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── README.md
```

## 🎨 Screenshots

### Login Page
Stunning hero section with feature highlights and glassmorphism login form.

### Dashboard
Overview of your resolutions with progress tracking and quick actions.

### Learning Session
Clean reading interface with progress tracking and concept tags.

### Quiz Interface
Interactive quizzes with multiple question types and immediate feedback.

### Results
Detailed breakdown of quiz performance with reinforcement suggestions.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google ADK** for the amazing agent development framework
- **Opik by Comet** for LLM observability and evaluation
- **FastAPI** for the lightning-fast Python backend
- **React & Vite** for the modern frontend experience

---

Built with ❤️ for the Comet Resolution Hackathon 2026
