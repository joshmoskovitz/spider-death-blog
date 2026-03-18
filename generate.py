#!/usr/bin/env python3
"""
Spider Death Blog — Post Generator

Generates a batch of new post concepts + captions in the blog's house style.
Reads the archive to avoid repetition, writes drafts to drafts/ as JSON.

Usage:
    python3 generate.py              # generate 5 drafts
    python3 generate.py --count 10   # generate 10 drafts
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")
ARCHIVE_PATH = PROJECT_DIR / "archive" / "posts.json"
STYLE_BIBLE_PATH = PROJECT_DIR / "style_bible.txt"
DRAFTS_DIR = PROJECT_DIR / "drafts"


def load_archive():
    """Load the original archive plus all previous drafts to avoid repeats."""
    with open(ARCHIVE_PATH) as f:
        posts = json.load(f)

    # Also scan drafts/ for previous batch files
    if DRAFTS_DIR.exists():
        for batch_file in sorted(DRAFTS_DIR.glob("batch_*.json")):
            with open(batch_file) as f:
                drafts = json.load(f)
                posts.extend(drafts)

    return posts


def load_style_bible():
    with open(STYLE_BIBLE_PATH) as f:
        return f.read()


def build_prompt(archive, style_bible, count):
    # Summarize what's already been done so the model avoids repeats
    used_settings = [p["setting"] for p in archive]
    used_mechanisms = [p["mechanism"] for p in archive]
    used_props = [p["main_prop"] for p in archive]

    return f"""{style_bible}

EXISTING POSTS (do NOT repeat these settings, mechanisms, or props):
- Settings used: {", ".join(used_settings)}
- Mechanisms used: {", ".join(used_mechanisms)}
- Main props used: {", ".join(used_props)}

YOUR TASK:
Generate exactly {count} new Spider Death Blog posts. Each must use a DIFFERENT setting and mechanism from the existing posts and from each other.

For each post, output a JSON object with these fields:
- "setting": where the death happens
- "mechanism": how the spider dies (one or two words)
- "main_prop": the key object involved
- "intro": the playful 1-2 sentence setup with a PUN or DOUBLE MEANING related to the death (see INTRO STYLE in style bible)
- "caption": the deadpan death confession in first person (see DEATH CAPTION STYLE in style bible)
- "hashtags": hashtag string in blog format, ending with "spider death"
- "hidden_touch": 1-2 charming hidden details that would appear in the MS Paint illustration
- "scene_description": a brief description of what the illustration would show (for later image generation)

Output ONLY a JSON array of {count} objects. No other text."""


def generate_batch(count):
    archive = load_archive()
    style_bible = load_style_bible()
    prompt = build_prompt(archive, style_bible, count)

    from costs import TrackedClient
    client = TrackedClient()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text

    # Parse JSON from response (handle markdown code fences if present)
    json_str = response_text.strip()
    if json_str.startswith("```"):
        # Strip markdown code fence
        lines = json_str.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        json_str = "\n".join(lines)

    return json.loads(json_str)


def save_drafts(posts):
    DRAFTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_file = DRAFTS_DIR / f"batch_{timestamp}.json"

    with open(batch_file, "w") as f:
        json.dump(posts, f, indent=2)

    return batch_file


def print_drafts(posts):
    for i, post in enumerate(posts, 1):
        print(f"\n{'='*60}")
        print(f"  DRAFT {i}")
        print(f"{'='*60}")
        print(f"  Setting:     {post.get('setting', '?')}")
        print(f"  Mechanism:   {post.get('mechanism', '?')}")
        print(f"  Prop:        {post.get('main_prop', '?')}")
        print(f"  Intro:       {post.get('intro', '?')}")
        print(f"  Caption:     {post.get('caption', '?')}")
        print(f"  Hashtags:    {post.get('hashtags', '?')}")
        print(f"  Hidden:      {post.get('hidden_touch', '?')}")
        print(f"  Scene:       {post.get('scene_description', '?')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Generate Spider Death Blog posts")
    parser.add_argument("--count", type=int, default=5, help="Number of posts to generate (default: 5)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY environment variable first.")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    print(f"Generating {args.count} Spider Death Blog drafts...")
    posts = generate_batch(args.count)
    batch_file = save_drafts(posts)
    print_drafts(posts)
    print(f"Saved to: {batch_file}")


if __name__ == "__main__":
    main()
