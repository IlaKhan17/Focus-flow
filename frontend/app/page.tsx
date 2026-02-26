"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8000";

type Step = { title: string; estimated_minutes: number };
type Session = {
  id: string;
  task_title: string;
  started_at: string;
  ended_at: string | null;
};

type Stats = {
  total_sessions: number;
  total_minutes: number;
  today_sessions: number;
  today_minutes: number;
};

function formatDuration(start: string, end: string | null): string {
  if (!end) return "—";
  const a = new Date(start).getTime();
  const b = new Date(end).getTime();
  const mins = Math.round((b - a) / 60000);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Home() {
  const [backendStatus, setBackendStatus] = useState<string>("checking...");
  const [task, setTask] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [recentSessions, setRecentSessions] = useState<Session[]>([]);
  const [clientId, setClientId] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);

  // Stable anonymous user id per browser
  useEffect(() => {
    if (typeof window === "undefined") return;
    const key = "focusflow_client_id";
    let existing = window.localStorage.getItem(key);
    if (!existing) {
      if (window.crypto && "randomUUID" in window.crypto) {
        existing = window.crypto.randomUUID();
      } else {
        existing = Math.random().toString(36).slice(2);
      }
      window.localStorage.setItem(key, existing);
    }
    setClientId(existing);
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setBackendStatus(data.status === "ok" ? "connected" : "error"))
      .catch(() => setBackendStatus("disconnected"));
  }, []);

  function fetchSessions() {
    if (!clientId) return;
    fetch(`${API_URL}/api/sessions`, {
      headers: {
        "X-User-Id": clientId,
      },
    })
      .then((res) => res.json())
      .then((data) => setRecentSessions(Array.isArray(data) ? data : []))
      .catch(() => setRecentSessions([]));
  }

  function fetchStats() {
    if (!clientId) return;
    fetch(`${API_URL}/api/stats`, {
      headers: {
        "X-User-Id": clientId,
      },
    })
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => setStats(null));
  }

  useEffect(() => {
    fetchSessions();
    fetchStats();
  }, [clientId]);

  // Timer tick when a session is active
  useEffect(() => {
    if (!activeSession) return;
    const start = new Date(activeSession.started_at).getTime();
    const tick = () => setElapsedSeconds(Math.floor((Date.now() - start) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [activeSession]);

  async function handleBreakdown(e: React.FormEvent) {
    e.preventDefault();
    if (!task.trim()) return;
    setLoading(true);
    setError(null);
    setSteps([]);
    try {
      const res = await fetch(`${API_URL}/api/breakdown`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: task.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || res.statusText || "Request failed");
        return;
      }
      setSteps(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  async function startFocus(stepTitle: string) {
    if (!clientId) return;
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": clientId,
        },
        body: JSON.stringify({ task_title: stepTitle }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to start");
      setActiveSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session");
    }
  }

  async function endFocus() {
    if (!activeSession) return;
    const id = activeSession.id;
    try {
      if (!clientId) return;
      await fetch(`${API_URL}/api/sessions/${id}`, {
        method: "PATCH",
        headers: {
          "X-User-Id": clientId,
        },
      });
      setActiveSession(null);
      fetchSessions();
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to end session");
    }
  }

  async function addToCalendar() {
    if (!activeSession) return;
    try {
      if (!clientId) return;
      const res = await fetch(
        `${API_URL}/api/sessions/${activeSession.id}/calendar-link`,
        {
          headers: {
            "X-User-Id": clientId,
          },
        }
      );
      const data = await res.json();
      if (data?.url) window.open(data.url, "_blank", "noopener,noreferrer");
    } catch {
      setError("Could not open calendar link");
    }
  }

  const timerDisplay =
    activeSession &&
    `${Math.floor(elapsedSeconds / 60)}:${String(elapsedSeconds % 60).padStart(2, "0")}`;

  return (
    <main className="ff-page">
      <header className="ff-header">
        <div>
          <h1 className="ff-title">Focus Flow</h1>
          <p className="ff-subtitle">
            AI-powered deep work assistant – turn vague intentions into concrete focus blocks you
            actually defend.
          </p>
        </div>
        <div
          className={[
            "ff-badge",
            backendStatus === "connected" && "ff-badge-connected",
            backendStatus === "error" && "ff-badge-error",
            backendStatus === "disconnected" && "ff-badge-disconnected",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <span className="ff-badge-dot" />
          <span>
            Backend: <strong>{backendStatus}</strong>
          </span>
        </div>
      </header>

      {backendStatus === "disconnected" && (
        <div className="ff-alert" style={{ marginTop: "0.9rem" }}>
          Start the backend with <code>cd backend && uvicorn main:app --reload</code>.
        </div>
      )}

      {activeSession && (
        <section className="ff-card ff-session-card">
          <span className="ff-session-pill">
            <span className="ff-session-pill-dot" />
            Focusing
          </span>
          <p className="ff-session-title">{activeSession.task_title}</p>
          <p className="ff-timer">{timerDisplay}</p>
          <p className="ff-helper">
            Close distractions, put your phone away, and switch on Do Not Disturb for this block.
          </p>
          <div className="ff-session-footer">
            <button type="button" onClick={addToCalendar} className="ff-btn ff-btn-ghost">
              Add to Google Calendar
            </button>
            <button type="button" onClick={endFocus} className="ff-btn ff-btn-secondary">
              End session
            </button>
          </div>
        </section>
      )}

      <div className="ff-main-grid">
        <div className="ff-main-column">
          <section className="ff-card">
            <div className="ff-card-header">
              <h2 className="ff-card-title">Break down a task</h2>
              <span className="ff-helper">Phase 1 · clarify &amp; scope</span>
            </div>
            <p className="ff-card-description">
              Describe what you&apos;re trying to do. Focus Flow turns it into concrete steps with
              realistic time estimates.
            </p>
            <form onSubmit={handleBreakdown} className="ff-form-row">
              <input
                className="ff-input"
                type="text"
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="e.g. Finish the quarterly report, from data cleanup to slides"
                disabled={loading}
              />
              <div className="ff-actions-row">
                <button
                  type="submit"
                  disabled={loading}
                  className="ff-btn ff-btn-primary"
                >
                  {loading ? "Breaking it down…" : "Break it down"}
                </button>
                <span className="ff-helper">
                  Enter a single task you could reasonably finish in one focused sitting.
                </span>
              </div>
            </form>

            {error && <div className="ff-alert">{error}</div>}

            {steps.length > 0 && (
              <div style={{ marginTop: "1rem" }}>
                <h3 className="ff-card-title" style={{ fontSize: "0.95rem" }}>
                  Suggested steps
                </h3>
                <ol className="ff-steps-list">
                  {steps.map((s, i) => (
                    <li key={i}>
                      <strong>{s.title}</strong>
                      <span className="ff-steps-meta">(~{s.estimated_minutes} min)</span>
                      {!activeSession && (
                        <button
                          type="button"
                          onClick={() => startFocus(s.title)}
                          className="ff-btn ff-btn-secondary ff-btn-small"
                          style={{ marginLeft: "0.6rem" }}
                        >
                          Start focus
                        </button>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </section>
        </div>

        <div className="ff-main-column">
          <section className="ff-card">
            <div className="ff-card-header">
              <h2 className="ff-card-title">Recent sessions</h2>
              <span className="ff-helper">Phase 4 · review &amp; log</span>
            </div>
            {recentSessions.length === 0 ? (
              <p className="ff-card-description">
                No sessions yet. Break down a task and start a focus block to see your history here.
              </p>
            ) : (
              <ul className="ff-list-unstyled">
                {recentSessions.map((s) => (
                  <li key={s.id} className="ff-session-row">
                    <span className="ff-session-main">{s.task_title}</span>
                    <span className="ff-session-meta">
                      <span>
                        {formatTime(s.started_at)}
                        {s.ended_at && ` · ${formatDuration(s.started_at, s.ended_at)}`}
                      </span>
                      <a
                        href="#"
                        className="ff-link"
                        onClick={async (e) => {
                          e.preventDefault();
                          try {
                            if (!clientId) return;
                            const res = await fetch(
                              `${API_URL}/api/sessions/${s.id}/calendar-link`,
                              {
                                headers: {
                                  "X-User-Id": clientId,
                                },
                              }
                            );
                            const data = await res.json();
                            if (data?.url) {
                              window.open(data.url, "_blank", "noopener,noreferrer");
                            }
                          } catch {
                            // ignore
                          }
                        }}
                      >
                        Add to calendar
                      </a>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="ff-card">
            <div className="ff-card-header">
              <h2 className="ff-card-title">Focus stats</h2>
              <span className="ff-helper">Phase 5 · spot patterns</span>
            </div>
            {!stats ? (
              <p className="ff-card-description">
                No stats yet. Run a few focus sessions to see where your time actually goes.
              </p>
            ) : (
              <div className="ff-stats-grid">
                <div className="ff-stat">
                  <div className="ff-stat-label">Today</div>
                  <div className="ff-stat-value">
                    {stats.today_sessions} session{stats.today_sessions === 1 ? "" : "s"} ·{" "}
                    {stats.today_minutes} min
                  </div>
                </div>
                <div className="ff-stat">
                  <div className="ff-stat-label">All time</div>
                  <div className="ff-stat-value">
                    {stats.total_sessions} session{stats.total_sessions === 1 ? "" : "s"} ·{" "}
                    {stats.total_minutes} min
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
