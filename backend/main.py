"""
Focus Flow – Backend API
Start with: uvicorn main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Focus Flow API",
    description="AI-powered deep work assistant",
    version="0.1.0",
)

# Allow frontend (Next.js) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Check that the API is running. Frontend can call this first."""
    return {"status": "ok", "message": "Focus Flow API is running"}


@app.get("/")
def root():
    """Root welcome."""
    return {"app": "Focus Flow", "docs": "/docs"}
