"""
Focus Flow – Backend API
Start with: uvicorn main:app --reload
"""
import json
import os
import re
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env (OPENAI_API_KEY)
from dotenv import load_dotenv
load_dotenv()

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


# --- Phase 2: Task breakdown ---

class BreakdownRequest(BaseModel):
    task: str


class BreakdownStep(BaseModel):
    title: str
    estimated_minutes: int


BREAKDOWN_SYSTEM = """You are a deep work coach. The user will give you a vague or high-level task.
Your job is to break it into 3–7 concrete, actionable steps that someone can do in focused blocks.
For each step:
- Use a short, clear title (e.g. "Outline the introduction", "Draft section 2").
- Give a realistic estimated_minutes (typically 15–60 per step).
Reply with ONLY a JSON array of objects, no other text. Each object must have exactly:
"title" (string) and "estimated_minutes" (integer).
Example: [{"title": "Read the brief", "estimated_minutes": 10}, {"title": "Draft outline", "estimated_minutes": 25}]"""


def parse_steps_from_response(content: str) -> list[dict]:
    """Extract JSON array from model response (may be wrapped in markdown)."""
    content = content.strip()
    # Remove markdown code block if present
    if "```" in content:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1).strip()
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array")
    return [
        {"title": str(s.get("title", "")), "estimated_minutes": int(s.get("estimated_minutes", 25))}
        for s in data
    ]


@app.post("/api/breakdown", response_model=list)
def breakdown_task(req: BreakdownRequest):
    """
    Break a vague task into concrete steps with time estimates.
    Requires OPENAI_API_KEY in .env.
    """
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or api_key.startswith("your-"):
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured. Add OPENAI_API_KEY to backend/.env (see .env.example).",
        )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": BREAKDOWN_SYSTEM},
                {"role": "user", "content": req.task},
            ],
            temperature=0.3,
        )
        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise ValueError("Empty response from model")
        steps = parse_steps_from_response(content)
        return steps
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Could not parse AI response as JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# --- Phase 3: Focus sessions ---

# In-memory store (resets when server restarts). Use SQLite later if you want persistence.
sessions_store: list[dict] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StartSessionRequest(BaseModel):
    task_title: str


@app.post("/api/sessions")
def start_session(req: StartSessionRequest):
    """Start a focus session. Returns the new session with id and started_at."""
    session = {
        "id": str(uuid.uuid4()),
        "task_title": req.task_title.strip() or "Focus",
        "started_at": _now_iso(),
        "ended_at": None,
    }
    sessions_store.append(session)
    return session


@app.patch("/api/sessions/{session_id}")
def end_session(session_id: str):
    """End a focus session. Sets ended_at to now."""
    for s in sessions_store:
        if s["id"] == session_id:
            if s["ended_at"] is not None:
                raise HTTPException(status_code=400, detail="Session already ended")
            s["ended_at"] = _now_iso()
            return s
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/sessions")
def list_sessions(limit: int = 20):
    """List recent sessions (newest first)."""
    sorted_sessions = sorted(sessions_store, key=lambda x: x["started_at"], reverse=True)
    return sorted_sessions[:limit]
