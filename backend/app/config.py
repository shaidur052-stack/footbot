import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "models/gemini-3.5-flash-lite"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nutribot.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-before-deploy")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7      # one week