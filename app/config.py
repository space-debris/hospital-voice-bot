import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    NGROK_URL: str = os.getenv("NGROK_URL", "http://localhost:8000")
    HOSPITAL_RECEPTION_NUMBER: str = os.getenv("HOSPITAL_RECEPTION_NUMBER", "")

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'hospital.db'}"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "chroma_db")

    # Session
    SESSION_TIMEOUT_MINUTES: int = 30

    # Paths
    FAQ_DIR: str = str(Path(__file__).resolve().parent / "data" / "faqs")
    FRONTEND_DIR: str = str(BASE_DIR / "frontend")

    class Config:
        env_file = ".env"


settings = Settings()
