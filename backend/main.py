from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from db import engine
from routers import breakdown, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


load_dotenv()

app = FastAPI(
    title="Focus Flow API",
    description="AI-powered deep work assistant",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Check that the API is running."""
    return {"status": "ok", "message": "Focus Flow API is running"}


@app.get("/")
def root():
    """Root welcome."""
    return {"app": "Focus Flow", "docs": "/docs"}


app.include_router(breakdown.router)
app.include_router(sessions.router)
