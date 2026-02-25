from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.data.seed import seed_database
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.services.audit import AuditLog  # noqa: F401 — registers model for create_all
from app.services.metrics import metrics
from app.routers import chat, auth, voice


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # ── Startup ──
    print("\n🏥 Starting City General Hospital Voice Assistant...\n")

    # Initialize database
    print("📦 Initializing database...")
    init_db()
    seed_database()

    # Initialize RAG service
    print("🔍 Initializing RAG knowledge base...")
    rag_service.initialize()

    # Initialize LLM service
    print("🤖 Initializing LLM service...")
    llm_service.initialize()

    print("\n✅ All systems ready!")
    print("🌐 Open http://localhost:8000 in your browser\n")
    print("=" * 50)
    print("  Test Patient Accounts:")
    print("  Phone: 9876543210 (Amit Kumar)")
    print("  Phone: 9876543211 (Sneha Verma)")
    print("  Phone: 9876543212 (Ravi Shankar)")
    print("  Phone: 9876543213 (Deepa Nair)")
    print("  Phone: 9876543214 (Mahesh Choudhary)")
    print("=" * 50)
    print("  OTPs will be printed in this console.\n")

    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_ACCOUNT_SID != "your_twilio_account_sid":
        print("📞 Twilio telephony ENABLED")
        print(f"   Phone: {settings.TWILIO_PHONE_NUMBER}")
        print(f"   Webhook URL: {settings.NGROK_URL}/voice/incoming\n")
    else:
        print("📞 Twilio telephony NOT configured (set TWILIO_* in .env)\n")

    yield

    # ── Shutdown ──
    print("\n👋 Shutting down Hospital Assistant...")


# ── Create FastAPI App ───────────────────────────────

app = FastAPI(
    title="City General Hospital - Voice Assistant",
    description="AI-powered hospital assistant with RAG and tool calling",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(voice.router)

# Mount static files (frontend)
frontend_dir = Path(settings.FRONTEND_DIR)
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Hospital Voice Assistant API is running. Frontend not found."}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "City General Hospital Assistant",
        "llm_ready": llm_service._initialized,
        "rag_ready": rag_service._initialized,
    }


@app.get("/metrics")
async def get_metrics():
    """Expose application metrics for monitoring."""
    return metrics.snapshot()
