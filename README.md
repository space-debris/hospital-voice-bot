# 🏥 City General Hospital — AI Voice Assistant (MVP)

An AI-powered hospital assistant built with **FastAPI**, **Google Gemini**, and **ChromaDB RAG**, featuring a premium dark-themed chat interface.

## ✨ Features

- **RAG-Grounded FAQ Answers** — Answers from a real hospital knowledge base (6 documents)
- **LLM Tool Calling** — Gemini intelligently calls tools for appointments, reports, billing
- **Guest vs Registered Flows** — Guest users get FAQs; verified patients get personalized services
- **OTP Authentication** — Mock OTP flow (printed to console) for patient verification
- **WebSocket Real-Time Chat** — Instant responses with typing indicators
- **Premium Dark UI** — Glassmorphism theme with micro-animations

## 🏗️ Architecture

```
User ──► WebSocket ──► Orchestrator ──► RAG (ChromaDB) ──► Gemini LLM
                                    └──► Tool Router ──► DB Tools
                                    └──► Auth Service ──► Session Store
```

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- [Gemini API Key](https://aistudio.google.com/app/apikey) (free)

### 2. Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Run
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Open
Navigate to **http://localhost:8000** in your browser.

## 🧪 Test Accounts

| Patient         | Phone        |
|-----------------|-------------|
| Amit Kumar      | 9876543210  |
| Sneha Verma     | 9876543211  |
| Ravi Shankar    | 9876543212  |
| Deepa Nair      | 9876543213  |
| Mahesh Choudhary| 9876543214  |

> **OTPs are printed in the server console.** Check your terminal after clicking "Send OTP".

## 🗂️ Project Structure

```
app/
├── main.py              # FastAPI entry point
├── config.py            # Environment settings
├── database.py          # SQLite + SQLAlchemy
├── models.py            # DB models (6 tables)
├── schemas.py           # Pydantic schemas
├── guardrails.py        # Safety filters
├── routers/
│   ├── chat.py          # Chat REST + WebSocket endpoints
│   └── auth.py          # Login + OTP endpoints
├── services/
│   ├── orchestrator.py  # Central conversation controller
│   ├── llm_service.py   # Gemini integration + tool calling
│   ├── rag_service.py   # ChromaDB FAQ retrieval
│   ├── auth_service.py  # OTP generation/verification
│   ├── session_store.py # In-memory session management
│   └── tool_router.py   # Tool dispatch + auth checking
├── tools/
│   ├── appointment.py   # Book/cancel/list appointments
│   ├── doctor_schedule.py # Doctor search + availability
│   ├── reports.py       # Lab report status
│   └── billing.py       # Billing summary
└── data/
    ├── seed.py          # Mock hospital data
    └── faqs/            # 6 FAQ markdown documents
frontend/
├── index.html           # Chat UI
├── styles.css           # Dark theme styling
└── app.js               # WebSocket + chat logic
```

## 🔧 Tech Stack

| Component    | Technology        |
|-------------|-------------------|
| Backend     | FastAPI (Python)  |
| LLM         | Google Gemini 2.0 |
| RAG         | ChromaDB          |
| Database    | SQLite + SQLAlchemy |
| Frontend    | HTML/CSS/JS       |
| Real-time   | WebSockets        |

## 📝 Sample Queries

**Guest (no login needed):**
- "What are your OPD timings?"
- "Which departments do you have?"
- "Where is the hospital located?"
- "Do you accept health insurance?"
- "What are the visiting hours?"

**Registered (login required):**
- "Book an appointment with Dr. Sharma"
- "Show my upcoming appointments"
- "Check my lab report status"
- "What's my billing summary?"

---

*Built as a learning project demonstrating RAG + Tool Calling + FastAPI architecture.*
