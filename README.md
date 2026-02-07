<h1 align="center" style="border-bottom: none">
    <div>
        <a href="https://neuro-resolv.vercel.app/"><picture>
            <img alt="NeuroResolv logo" src="https://raw.githubusercontent.com/mrmaheshrajput/NeuroResolv/refs/heads/main/frontend/public/icon.svg" width="60" />
        </picture></a>
        <br>
        NeuroResolv 🧠✨
    </div>
</h1>
<h2 align="center" style="border-bottom: none">Open-source Adaptive AI Tutor & Accountability Partner for New Year Resolutions</h2>
<p align="center">
Transform your New Year's resolutions from simple task tracking into genuine learning journeys with AI-powered adaptive tutoring.
</p>

<div align="center">

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#)
[![React](https://img.shields.io/badge/React-%2320232a.svg?logo=react&logoColor=%2361DAFB)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-009485.svg?logo=fastapi&logoColor=white)](#)
[![Opik](https://img.shields.io/badge/Opik-by_Comet-blue)](https://github.com/comet-ml/opik)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-886FBF?logo=googlegemini&logoColor=fff)](https://deepmind.google/models/gemini/)
[![Vercel](https://img.shields.io/badge/Vercel-%23000000.svg?logo=vercel&logoColor=white)](https://vercel.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff)](#)

</div>

## 🎯 The Problem

Most resolution apps are just "tick-box" trackers. They tell you IF you did something, not if you LEARNED anything. NeuroResolv changes that.

## ✨ Key Features

### 🎯 Milestone-Based Resolution Tracking
Move away from simple checklists to a structured, milestone-based learning journey that focuses on genuine progress.

### 🗺️ Dynamic Roadmap Generation
Our AI Roadmap Agent analyzes your goals and learning materials (PDFs, EPUBs, text) to create a personalized, multi-stage curriculum.

### 🎙️ Multi-Modal Progress Logging
Log your daily learning via text or voice notes (powered by Whisper API), allowing for a natural and friction-less reflection process.

### 🧪 Context-Aware Verification
The Verification Agent generates dynamic quizzes based *specifically* on your daily progress logs to ensure concepts are actually understood.

### 🔥 Accountability & Streaks
Maintain consistency with automated streak tracking, daily progress logs, and weekly AI-powered reflections.

### 🔄 Adaptive Failure Recovery
If you fall behind or struggle with certain concepts, the Adaptive Agent automatically adjusts your roadmap and provides reinforcement sessions.

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React + Vite | Modern SPA with stunning UI |
| **Backend** | FastAPI (Python 3.12) | Async API with automated migrations |
| **AI Agents** | Google ADK | Multi-agent orchestration system |
| **LLMs** | Gemini 2.5 Flash + Whisper | Fast foundation model & Voice transcription |
| **Database** | PostgreSQL + Alembic | Robust persistence and schema management |
| **Infrastructure** | AWS ECS + RDS | Scalable cloud deployment |
| **Observability** | Opik Cloud | LLM tracing and evaluation |

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

# AWS & Database (PostgreSQL)
AWS_REGION=us-east-1
DB_SECRET_NAME=your-db-secret-name

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
│   │   │   ├── roadmap_agent.py
│   │   │   ├── verification_agent.py
│   │   │   ├── syllabus_agent.py
│   │   │   ├── quiz_agent.py
│   │   │   └── adaptive_agent.py
│   │   ├── api/             # FastAPI routers (Resolutions, Sessions, Progress)
│   │   ├── aws/             # AWS integration (Secrets Manager)
│   │   ├── db/              # Database models & migrations
│   │   ├── services/        # Business logic
│   │   └── observability/   # Opik integration
│   ├── alembic/             # SQL migrations
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

Built for the Comet Resolution Hackathon 2026
