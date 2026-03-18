#!/usr/bin/env python3
"""
Spider Death Blog — Create Your Own API Server

A lightweight FastAPI server that powers the "Create Your Own Spider Death" feature.
Accepts a short user phrase, generates a full post concept and MS Paint illustration,
and returns everything needed to display the comic.

Usage:
    python3 server.py              # start on port 8888
    python3 server.py --port 9000  # custom port
"""

import argparse
import base64
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ai_renderer import render_from_description
from community_db import CommunityDB
from costs import TrackedClient, BudgetExceededError
from rate_limiter import RateLimiter

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

STYLE_BIBLE_PATH = PROJECT_DIR / "style_bible.txt"

# ---------------------------------------------------------------------------
# Persistent rate limiter and community board (SQLite-backed)
# ---------------------------------------------------------------------------

_rate_limiter = RateLimiter()
_community_db = CommunityDB()

MAX_CREATES_PER_HOUR = 5
MAX_VOTES_PER_HOUR = 20


# ---------------------------------------------------------------------------
# Content guardrails
# ---------------------------------------------------------------------------

INPUT_MAX_LENGTH = 120

BLOCKED_PATTERNS = [
    r'\b(suicide|self[- ]?harm|kill\s+(my|your)self)\b',
    r'\b(racial|ethnic)\s+slur',
    r'\b(nazi|hitler|holocaust)\b',
    r'\b(rape|sexual\s+assault)\b',
    r'\b(school\s+shoot|mass\s+shoot|bomb\s+threat)\b',
    r'\b(child|minor|kid)\s+(abuse|porn)',
]


def _check_input(phrase: str) -> Optional[str]:
    """Returns an error message if the input is disallowed, None if OK."""
    if not phrase or not phrase.strip():
        return "Please enter a phrase describing how the spider meets its end."
    if len(phrase) > INPUT_MAX_LENGTH:
        return f"Please keep your phrase under {INPUT_MAX_LENGTH} characters."
    lowered = phrase.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lowered):
            return "That topic isn't a good fit for Spider Death Blog. Try something whimsical!"
    return None


# ---------------------------------------------------------------------------
# Post concept generation
# ---------------------------------------------------------------------------

def _load_style_bible() -> str:
    with open(STYLE_BIBLE_PATH) as f:
        return f.read()


CONCEPT_SYSTEM_PROMPT = """\
You generate Spider Death Blog post concepts. The user gives you a short phrase \
describing how they want the spider to die. You produce a complete post in the \
blog's house style (see the style bible above).

CONTENT POLICY:
- Keep deaths WHIMSICAL and THEATRICAL — cartoonish, never graphic or gory.
- No real people, no hate, no self-harm references, no sexual content.
- If the user's phrase is dark, pivot it to something absurd and funny.
- The spider is always the victim. The narrator is always the calm murderer.

OUTPUT FORMAT:
Return ONLY a JSON object (no markdown fences) with these fields:
- "setting": where the death happens (2-4 words)
- "mechanism": how the spider dies (1-2 words)
- "intro": playful 1-2 sentence setup with a PUN (see style bible)
- "caption": deadpan first-person death confession (see style bible)
- "hashtags": hashtag string ending with "spider death"
- "hidden_touch": 1-2 charming hidden details for the illustration
- "scene_description": detailed description of what the illustration should show \
(setting, props, where spidey is, what's happening, key visual details)
"""


def generate_post_concept(phrase: str, client) -> dict:
    """Generate a full post concept from a user's phrase."""
    style_bible = _load_style_bible()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[
            {"type": "text", "text": style_bible, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": CONCEPT_SYSTEM_PROMPT.replace("{style_bible}", "")},
        ],
        messages=[{
            "role": "user",
            "content": f"Create a Spider Death Blog post where the spider dies by: {phrase}",
        }],
    )

    response_text = message.content[0].text.strip()
    # Handle markdown fences
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    return json.loads(response_text)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Spider Death Blog — Create Your Own")

_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class CreateRequest(BaseModel):
    phrase: str = Field(
        ...,
        min_length=1,
        max_length=INPUT_MAX_LENGTH,
        description="Short phrase describing how the spider should die",
    )


class CreateResponse(BaseModel):
    setting: str
    mechanism: str
    intro: str
    caption: str
    hashtags: str
    hidden_touch: str
    image_base64: str


@app.post("/api/create", response_model=CreateResponse)
async def create_spider_death(req: CreateRequest, request: Request):
    """Generate a custom spider death post from a user's phrase."""
    client_ip = request.client.host if request.client else "unknown"

    # Rate limit (persistent across restarts)
    if _rate_limiter.is_rate_limited(client_ip, MAX_CREATES_PER_HOUR, 3600):
        return JSONResponse(
            status_code=429,
            content={
                "error": "You've been very creative! Please wait a bit before generating another."
            },
        )

    # Validate input
    error = _check_input(req.phrase)
    if error:
        return JSONResponse(status_code=400, content={"error": error})

    client = TrackedClient()

    # Step 1: Generate the post concept
    try:
        concept = generate_post_concept(req.phrase, client)
    except BudgetExceededError as e:
        print(f"[BUDGET] {e}", flush=True)
        return JSONResponse(
            status_code=503,
            content={"error": "Spidey's on a budget today. Try again later!"},
        )
    except Exception as e:
        print(f"[ERROR] Concept generation failed: {e}", flush=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Spidey's ghost is busy. Please try again."},
        )

    # Step 2: Render the illustration
    try:
        img, _code = render_from_description(concept["scene_description"], client)
    except BudgetExceededError as e:
        print(f"[BUDGET] {e}", flush=True)
        return JSONResponse(
            status_code=503,
            content={"error": "Spidey's on a budget today. Try again later!"},
        )
    except Exception as e:
        print(f"[ERROR] Rendering failed: {e}", flush=True)
        return JSONResponse(
            status_code=500,
            content={"error": "The MS Paint gods are displeased. Please try again."},
        )

    # Encode image as base64 PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    _rate_limiter.record_request(client_ip)

    return CreateResponse(
        setting=concept.get("setting", ""),
        mechanism=concept.get("mechanism", ""),
        intro=concept.get("intro", ""),
        caption=concept.get("caption", ""),
        hashtags=concept.get("hashtags", ""),
        hidden_touch=concept.get("hidden_touch", ""),
        image_base64=image_b64,
    )


# ---------------------------------------------------------------------------
# Community board endpoints
# ---------------------------------------------------------------------------

class CommunitySubmission(BaseModel):
    phrase: str
    intro: str
    caption: str
    hashtags: str
    image_base64: str


class CommunityEntry(BaseModel):
    id: str
    phrase: str
    intro: str
    caption: str
    hashtags: str
    image_base64: str
    upvotes: int
    downvotes: int
    score: int
    created_at: str


class VoteRequest(BaseModel):
    entry_id: str
    direction: Optional[str] = Field(None, description="'up', 'down', or null")
    previous: Optional[str] = Field(None, description="Previous vote to undo: 'up', 'down', or null")


@app.post("/api/community/submit")
async def community_submit(submission: CommunitySubmission, request: Request):
    """Add a generated spider death to the community board."""
    client_ip = request.client.host if request.client else "unknown"

    if _rate_limiter.is_rate_limited(client_ip, MAX_CREATES_PER_HOUR, 3600):
        return JSONResponse(
            status_code=429,
            content={"error": "Slow down! Try again in a bit."},
        )

    try:
        result = _community_db.submit(
            phrase=submission.phrase,
            intro=submission.intro,
            caption=submission.caption,
            hashtags=submission.hashtags,
            image_base64=submission.image_base64,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return {"id": result["id"], "message": "Added to the community board!"}


@app.get("/api/community/board")
async def community_board():
    """Return the top 20 community spider deaths by vote score."""
    entries = _community_db.top_entries(limit=20)
    return {"entries": entries}


@app.post("/api/community/vote")
async def community_vote(req: VoteRequest, request: Request):
    """Vote on a community board entry."""
    valid_directions = ("up", "down", None)
    if req.direction not in valid_directions:
        return JSONResponse(
            status_code=400,
            content={"error": "Direction must be 'up', 'down', or null."},
        )
    if req.previous not in valid_directions:
        return JSONResponse(
            status_code=400,
            content={"error": "Previous must be 'up', 'down', or null."},
        )

    client_ip = request.client.host if request.client else "unknown"
    if _rate_limiter.is_rate_limited(client_ip, MAX_VOTES_PER_HOUR, 3600):
        return JSONResponse(
            status_code=429,
            content={"error": "Easy on the votes! Try again later."},
        )

    result = _community_db.vote(req.entry_id, req.direction, req.previous)
    if result is None:
        return JSONResponse(status_code=404, content={"error": "Entry not found."})

    _rate_limiter.record_request(client_ip)
    return result


@app.get("/api/health")
async def health():
    return {"status": "alive", "message": "Spidey awaits his fate."}


def main():
    parser = argparse.ArgumentParser(description="Spider Death Blog API Server")
    parser.add_argument("--port", type=int, default=8888, help="Port (default: 8888)")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY in .env or environment.")
        sys.exit(1)

    print(f"Starting Spider Death Blog API on http://{args.host}:{args.port}")
    print(f"  POST /api/create       — generate a custom spider death")
    print(f"  POST /api/community/*  — community board submit/vote")
    print(f"  GET  /api/community/board — top 20 community deaths")
    print(f"  GET  /api/health       — health check")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
