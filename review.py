#!/usr/bin/env python3
"""
Spider Death Blog — Multi-Agent Image Review

Sends rendered images to a panel of critic agents, each with a different lens,
all grounded in the blog's style bible. Returns structured feedback per image.

Usage:
    python3 review.py drafts/draft_1_laundromat.png
    python3 review.py drafts/draft_1_laundromat.png drafts/draft_2_post_office.png
    python3 review.py drafts/*.png
"""

import argparse
import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from costs import TrackedClient

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

STYLE_BIBLE_PATH = PROJECT_DIR / "style_bible.txt"


def load_style_bible():
    with open(STYLE_BIBLE_PATH) as f:
        return f.read()


def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# The four critics
# ---------------------------------------------------------------------------

CRITICS = {
    "clarity": {
        "name": "The Clarity Critic",
        "emoji": "🔍",
        "system": """You are the Clarity Critic for Spider Death Blog.

Your job: Can a stranger instantly understand what's happening in this image?

You care about:
- Can you tell what every object is at a glance? If something is ambiguous, name it.
- Is the death premise immediately readable? (e.g. "spider in dryer" should be obvious)
- Are objects overlapping in confusing ways?
- Is text readable?
- Is Spidey clearly visible and identifiable as a spider?
- Is the spatial layout logical? (things on the floor are on the floor, things on walls are on walls)

You do NOT care about artistic style, humor, or brand — only whether a viewer can parse what they're looking at.

Be specific. Name each unclear element and say what's wrong with it.""",
    },

    "skeptic": {
        "name": "The Skeptic",
        "emoji": "🤨",
        "system": """You are the Skeptic critic for Spider Death Blog.

Your job: Challenge everything. Push back on laziness, vagueness, and "good enough."

You care about:
- Does this actually look like an MS Paint drawing? Or does it look like a computer generated it?
- Are the proportions weird in a BAD way (not a charming way)?
- Is anything phoned in? Empty walls, missing details, obvious shortcuts?
- Would this actually work as a blog post or would someone scroll past it?
- Does the image earn its existence? Is there a reason to look at it twice?
- Are there enough details to reward a closer look?

Be tough but constructive. If something is genuinely good, say so. If something is mediocre, say that too.""",
    },

    "absurdist": {
        "name": "The Absurdist",
        "emoji": "🎪",
        "system": """You are the Absurdist critic for Spider Death Blog.

Your job: Is this image delightful? Does it have soul?

You care about:
- Is there a hidden detail that makes you smile? (a sign, a labeled object, a tiny joke)
- Does the scene have personality beyond just illustrating the caption?
- Is there tension between the cute and the morbid?
- Would this make someone want to share it with a friend?
- Is there anything unexpected or surprising in the composition?
- Does the world feel lived-in? Like someone drew this with love?

You LOVE: smiley suns, labeled food items, ironic signs, tiny hats, optimistic objects near tragedy.
You HATE: generic, soulless, could-be-anything scenes.""",
    },

    "brand": {
        "name": "The Brand Guardian",
        "emoji": "🎨",
        "system": """You are the Brand Guardian for Spider Death Blog.

Your job: Does this image match the blog's established visual identity?

The original blog posts (2012) had these specific qualities:
- MS Paint aesthetic: crude outlines, flat colors, spray-paint tool for clouds/grass
- 640x480 canvas
- Spidey: gray oval body, black stick legs, simple dot eyes with white sclera, expressive mouth
- Bright, saturated, flat color fills (no gradients, no shading)
- Each scene has 1-2 hidden charming details (labeled items, signs, tiny accessories)
- Scene is instantly readable — you glance and understand the death
- Spidey is relatively SMALL compared to the environment
- Handmade energy — imperfect, wobbly, lovingly crude

Compare what you see against these qualities. Be specific about what matches and what drifts.
Flag anything that looks too polished, too generic, or too computer-generated.
Flag if Spidey doesn't look like himself.""",
    },
}


def review_image(client, image_path, post_data, style_bible, critic_key):
    """Send an image to one critic agent and get their review."""
    critic = CRITICS[critic_key]

    # Build the caption context if we have post data
    context = ""
    if post_data:
        context = f"""
POST CONTEXT:
- Setting: {post_data.get('setting', '?')}
- Mechanism: {post_data.get('mechanism', '?')}
- Caption: {post_data.get('caption', '?')}
- Hidden touch: {post_data.get('hidden_touch', '?')}
"""

    img_b64 = image_to_base64(image_path)

    # Determine media type
    suffix = Path(image_path).suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=[
            {"type": "text", "text": style_bible, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": critic["system"]},
        ],
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    },
                },
                {
                    "type": "text",
                    "text": f"""Review this Spider Death Blog illustration.
{context}
Give your critique in this format:

SCORE: [1-10]
VERDICT: [one sentence summary]
STRENGTHS: [bullet list]
ISSUES: [bullet list, most important first]
SUGGESTION: [single most impactful improvement]""",
                },
            ],
        }],
    )

    return {
        "critic": critic_key,
        "name": critic["name"],
        "emoji": critic["emoji"],
        "review": message.content[0].text,
    }


def find_post_data(image_path):
    """Try to find the matching post data from the batch JSON."""
    image_name = Path(image_path).stem  # e.g. "draft_1_laundromat"
    batch_dir = Path(image_path).parent

    # Look for batch JSON files in the same directory
    for json_file in sorted(batch_dir.glob("batch_*.json")):
        with open(json_file) as f:
            posts = json.load(f)
        # Try to match by index from filename
        try:
            idx_str = image_name.split("_")[1]
            idx = int(idx_str) - 1  # draft_1 = index 0
            if 0 <= idx < len(posts):
                return posts[idx]
        except (IndexError, ValueError):
            pass
        # Try to match by setting name
        setting_part = "_".join(image_name.split("_")[2:])
        for post in posts:
            if post.get("setting", "").replace(" ", "_").lower() == setting_part:
                return post

    return None


def print_review(image_path, reviews):
    """Pretty-print the reviews for one image."""
    print(f"\n{'='*70}")
    print(f"  IMAGE: {Path(image_path).name}")
    print(f"{'='*70}")

    scores = []
    for r in reviews:
        print(f"\n{r['emoji']}  {r['name']}")
        print(f"{'─'*50}")
        print(r["review"])
        # Try to extract score
        for line in r["review"].split("\n"):
            if line.strip().startswith("SCORE:"):
                try:
                    score = int("".join(c for c in line.split(":")[1] if c.isdigit())[:2])
                    scores.append(score)
                except ValueError:
                    pass

    if scores:
        avg = sum(scores) / len(scores)
        print(f"\n{'─'*50}")
        print(f"  AVERAGE SCORE: {avg:.1f}/10")
        if avg >= 8:
            print("  STATUS: Ready to publish")
        elif avg >= 6:
            print("  STATUS: Needs minor tweaks")
        elif avg >= 4:
            print("  STATUS: Needs significant revision")
        else:
            print("  STATUS: Back to the drawing board")
    print()


def review_images(image_paths):
    """Review multiple images with all four critics in parallel."""
    client = TrackedClient()
    style_bible = load_style_bible()

    for image_path in image_paths:
        if not os.path.exists(image_path):
            print(f"  Skipping {image_path} — not found")
            continue

        post_data = find_post_data(image_path)
        print(f"\n  Reviewing {Path(image_path).name} with 4 critics...")

        # Run all 4 critics in parallel
        reviews = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    review_image, client, image_path, post_data, style_bible, critic_key
                ): critic_key
                for critic_key in CRITICS
            }
            for future in as_completed(futures):
                try:
                    reviews.append(future.result())
                except Exception as e:
                    critic_key = futures[future]
                    print(f"    {CRITICS[critic_key]['name']} failed: {e}")

        # Sort by critic order
        critic_order = list(CRITICS.keys())
        reviews.sort(key=lambda r: critic_order.index(r["critic"]))

        print_review(image_path, reviews)


def main():
    parser = argparse.ArgumentParser(description="Review Spider Death Blog illustrations")
    parser.add_argument("images", nargs="+", help="Image file(s) to review")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY in .env first.")
        sys.exit(1)

    review_images(args.images)


if __name__ == "__main__":
    main()
