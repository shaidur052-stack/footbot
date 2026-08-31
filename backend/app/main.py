from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import user as models          # registers tables with Base
from app.routers import chat, profile, auth, conversations, feedback
from app.services.classifier_service import classifier_service

# Create tables on startup. Safe to run every time — existing tables are
# left alone.
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pay the model-loading cost at boot, where nobody is waiting.

    Measured before this change: the first request after a restart spent
    10.4 seconds inside classify() loading a 1.1 GB model. Startup is a few
    seconds slower now; every user request is 10 seconds faster.
    """
    print("[startup] warming classifier...")
    classifier_service.warmup()
    print("[startup] ready")
    yield


app = FastAPI(title="NutriBot BD", lifespan=lifespan)

# Vite may land on 5173, 5174, ... depending on what's free, and the browser
# also distinguishes localhost from 127.0.0.1. A regex covers all of them.
# Locked to a single origin at deploy time.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(profile.router)
app.include_router(conversations.router)
app.include_router(feedback.router)


@app.get("/health")
def health():
    return {"status": "ok"}