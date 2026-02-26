"""
Task breakdown: break vague tasks into concrete steps with time estimates (Phase 2).
"""
import json
import os
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["breakdown"])


class BreakdownRequest(BaseModel):
    task: str


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


@router.post("/breakdown", response_model=list)
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
        return parse_steps_from_response(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Could not parse AI response as JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
