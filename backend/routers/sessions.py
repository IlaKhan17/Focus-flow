"""
Focus sessions: start/end sessions, list recent ones (Phase 3),
calendar link for blocking focus time (Phase 4),
and persistence via SQLite/SQLModel (long-term data).
"""
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from db import get_session
from models import FocusSession

router = APIRouter(prefix="/api", tags=["sessions"])


class StartSessionRequest(BaseModel):
    task_title: str


def _require_user_id(user_id: str | None) -> str:
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    return user_id


@router.post("/sessions")
def start_session(
    req: StartSessionRequest,
    db: Session = Depends(get_session),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    """Start a focus session. Returns the new session with id and started_at."""
    uid = _require_user_id(user_id)
    session = FocusSession(
        id=str(uuid.uuid4()),
        user_id=uid,
        task_title=req.task_title.strip() or "Focus",
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.patch("/sessions/{session_id}")
def end_session(
    session_id: str,
    db: Session = Depends(get_session),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    """End a focus session. Sets ended_at to now."""
    uid = _require_user_id(user_id)
    statement = select(FocusSession).where(
        FocusSession.id == session_id, FocusSession.user_id == uid
    )
    focus_session = db.exec(statement).one_or_none()
    if not focus_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if focus_session.ended_at is not None:
        raise HTTPException(status_code=400, detail="Session already ended")
    focus_session.ended_at = datetime.now(timezone.utc)
    db.add(focus_session)
    db.commit()
    db.refresh(focus_session)
    return focus_session


@router.get("/sessions")
def list_sessions(
    limit: int = 20,
    db: Session = Depends(get_session),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    """List recent sessions (newest first) for this user."""
    uid = _require_user_id(user_id)
    statement = (
        select(FocusSession)
        .where(FocusSession.user_id == uid)
        .order_by(FocusSession.started_at.desc())
    )
    sessions = db.exec(statement).all()
    return sessions[:limit]


# --- Stats (Phase 5) ---


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_session),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    """Basic focus stats for this user: today and all-time."""
    uid = _require_user_id(user_id)
    statement = select(FocusSession).where(FocusSession.user_id == uid)
    sessions = db.exec(statement).all()

    now = datetime.now(timezone.utc)
    today = now.date()

    total_sessions = len(sessions)
    total_minutes = 0
    today_sessions = 0
    today_minutes = 0

    for s in sessions:
        if not s.started_at or not s.ended_at:
            continue
        duration_min = max(
            0, int((s.ended_at - s.started_at).total_seconds() // 60)
        )
        total_minutes += duration_min
        if s.started_at.date() == today:
            today_sessions += 1
            today_minutes += duration_min

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "today_sessions": today_sessions,
        "today_minutes": today_minutes,
    }


# --- Calendar link helpers ---

def _to_google_calendar_format(dt: datetime) -> str:
    """Format as YYYYMMDDTHHMMSSZ for Google Calendar URL."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


@router.get("/sessions/{session_id}/calendar-link")
def get_calendar_link(
    session_id: str,
    db: Session = Depends(get_session),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    """
    Get a Google Calendar URL for this session so the user can block time.
    For an active session (no ended_at), end time is set to start + 60 minutes.
    """
    uid = _require_user_id(user_id)
    statement = select(FocusSession).where(
        FocusSession.id == session_id, FocusSession.user_id == uid
    )
    session = db.exec(statement).one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    start_dt = session.started_at
    end_dt = session.ended_at or (start_dt + timedelta(minutes=60))
    title = (session.task_title or "Focus").strip()
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{_to_google_calendar_format(start_dt)}/{_to_google_calendar_format(end_dt)}",
    }
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"https://calendar.google.com/calendar/render?{qs}"
    return {"url": url, "title": title}
