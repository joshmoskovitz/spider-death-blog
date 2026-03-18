#!/usr/bin/env python3
"""
Spider Death Blog — Daily Autonomous Pipeline

Generates one new spider death post per day: concept, illustration,
iterative improvement, archive, and site rebuild. Designed to run
unattended via cron or GitHub Actions.

Usage:
    python3 daily_pipeline.py                    # generate and build
    python3 daily_pipeline.py --dry-run          # generate but don't archive
    python3 daily_pipeline.py --threshold 7.0    # lower quality bar
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

ARCHIVE_PATH = PROJECT_DIR / "archive" / "posts.json"
ARCHIVE_IMAGES = PROJECT_DIR / "archive" / "images"
DRAFTS_DIR = PROJECT_DIR / "drafts"
LOG_PATH = PROJECT_DIR / "daily_log.jsonl"


def log_event(event: str, **kwargs):
    """Append a structured log entry to daily_log.jsonl."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **kwargs,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  [{event}] {kwargs.get('message', '')}", flush=True)


def check_budget():
    """Abort early if we're close to the daily or monthly budget."""
    from costs import daily_total, monthly_total

    daily_limit = os.environ.get("DAILY_BUDGET")
    if daily_limit and daily_total() >= float(daily_limit) * 0.9:
        raise RuntimeError(
            f"Near daily budget: ${daily_total():.2f} / ${daily_limit}"
        )

    monthly_limit = os.environ.get("MONTHLY_BUDGET")
    if monthly_limit and monthly_total() >= float(monthly_limit) * 0.9:
        raise RuntimeError(
            f"Near monthly budget: ${monthly_total():.2f} / ${monthly_limit}"
        )


def generate_concept():
    """Generate a single post concept. Returns (posts_list, batch_path)."""
    from generate import generate_batch, save_drafts

    posts = generate_batch(count=1)
    batch_path = save_drafts(posts)
    return posts, str(batch_path)


def improve_post(batch_path, threshold, max_rounds):
    """Run the improvement loop on the first (only) post in the batch."""
    from costs import TrackedClient
    from improve import improve_single

    client = TrackedClient()
    score = improve_single(
        client, batch_path, index=0,
        threshold=threshold, max_rounds=max_rounds,
    )
    return score


def archive_post(batch_path, post_data):
    """Move the approved post from drafts into the permanent archive."""
    # Load current archive
    with open(ARCHIVE_PATH) as f:
        archive = json.load(f)

    next_id = len(archive) + 1

    # Find the rendered image
    setting_slug = post_data.get("setting", "scene").replace(" ", "_")
    image_name = f"draft_1_{setting_slug}.png"
    draft_image = Path(batch_path).parent / image_name

    # Determine archive image filename
    archive_image_name = f"{next_id:02d}_{setting_slug}.png"

    if draft_image.exists():
        ARCHIVE_IMAGES.mkdir(parents=True, exist_ok=True)
        shutil.copy2(draft_image, ARCHIVE_IMAGES / archive_image_name)
    else:
        log_event("warning", message=f"Draft image not found: {draft_image}")
        archive_image_name = image_name  # fallback

    # Build the archive entry
    entry = {
        "setting": post_data.get("setting", ""),
        "mechanism": post_data.get("mechanism", ""),
        "main_prop": post_data.get("main_prop", ""),
        "intro": post_data.get("intro", ""),
        "caption": post_data.get("caption", ""),
        "hashtags": post_data.get("hashtags", ""),
        "hidden_touch": post_data.get("hidden_touch", ""),
        "scene_description": post_data.get("scene_description", ""),
        "image": archive_image_name,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    archive.append(entry)

    with open(ARCHIVE_PATH, "w") as f:
        json.dump(archive, f, indent=2)

    return next_id


def rebuild_site():
    """Regenerate the static site from the archive."""
    from build_site import build_all
    return build_all()


def main():
    parser = argparse.ArgumentParser(
        description="Daily Spider Death Blog pipeline"
    )
    parser.add_argument(
        "--threshold", type=float, default=7.5,
        help="Quality threshold for improvement loop (default: 7.5)",
    )
    parser.add_argument(
        "--max-rounds", type=int, default=2,
        help="Max improvement rounds (default: 2, saves cost)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate and improve but don't archive or rebuild",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    start = time.time()
    log_event("pipeline_start", message="Daily pipeline started")

    # Step 1: Budget check
    try:
        check_budget()
    except RuntimeError as e:
        log_event("budget_abort", message=str(e))
        sys.exit(1)

    # Step 2: Generate concept
    try:
        posts, batch_path = generate_concept()
        post = posts[0]
        log_event("concept_generated", message=f"Setting: {post.get('setting')}")
    except Exception as e:
        log_event("concept_failed", message=str(e))
        sys.exit(1)

    # Step 3: Improve
    try:
        score = improve_post(batch_path, args.threshold, args.max_rounds)
        log_event("improvement_done", message=f"Score: {score:.1f}/10")
    except Exception as e:
        log_event("improvement_failed", message=str(e))
        # Continue anyway — we still have the initial render
        score = 0

    if args.dry_run:
        log_event("dry_run_complete", message="Skipping archive and rebuild")
        elapsed = time.time() - start
        log_event("pipeline_done", message=f"Dry run in {elapsed:.0f}s")
        return

    # Step 4: Archive
    try:
        post_id = archive_post(batch_path, post)
        log_event("archived", message=f"Post #{post_id}")
    except Exception as e:
        log_event("archive_failed", message=str(e))
        sys.exit(1)

    # Step 5: Rebuild site
    try:
        total = rebuild_site()
        log_event("site_rebuilt", message=f"{total} posts")
    except Exception as e:
        log_event("rebuild_failed", message=str(e))
        sys.exit(1)

    elapsed = time.time() - start
    log_event("pipeline_done", message=f"Post #{post_id} in {elapsed:.0f}s, score {score:.1f}/10")


if __name__ == "__main__":
    main()
