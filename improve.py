#!/usr/bin/env python3
"""
Spider Death Blog — Auto-Improvement Loop v2

Renders → reviews with 4 critics → art director rewrites scene code → re-renders → repeats.

Upgrades over v1:
- Art director sees full critic history from ALL prior rounds (no regression)
- Art director does complete rewrites, not patches (rethink composition)
- Before/after images are saved and compared each round

Usage:
    python3 improve.py drafts/batch_XXXXX.json                # improve all drafts
    python3 improve.py drafts/batch_XXXXX.json --index 0      # improve just draft 1
    python3 improve.py drafts/batch_XXXXX.json --threshold 8.5 # stop at avg 8.5/10
    python3 improve.py drafts/batch_XXXXX.json --max-rounds 4  # up to 4 rounds
"""

import argparse
import base64
import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

STYLE_BIBLE_PATH = PROJECT_DIR / "style_bible.txt"
RENDER_PATH = PROJECT_DIR / "render.py"

from review import CRITICS, image_to_base64, load_style_bible


def load_render_source():
    with open(RENDER_PATH) as f:
        return f.read()


def save_render_source(source):
    with open(RENDER_PATH, "w") as f:
        f.write(source)


def find_scene_function(render_source, setting, mechanism):
    """Find which _scene_* function handles this post, and extract its source.

    Strategy:
    1. Check if a dedicated _scene_{setting_slug} function exists in render_source
    2. Parse the routing block in render_scene() to find which function handles this setting
    3. Fall back to generic outdoor/indoor
    """
    setting_lower = setting.lower()

    # Strategy 1: Look for a dedicated scene function by setting slug
    setting_slug = setting_lower.replace(" ", "_").replace("/", "_")
    dedicated_name = f"_scene_{setting_slug}"
    pattern = rf"(def {re.escape(dedicated_name)}\(draw, post\):.*?)(?=\ndef |\Z)"
    match = re.search(pattern, render_source, re.DOTALL)
    if match:
        return dedicated_name, match.group(1).rstrip()

    # Strategy 2: Parse the elif routing block in render_scene()
    # Look for lines like: elif "golf course" in setting:\n        _scene_golf_course(draw, post)
    route_pattern = r'elif\s+"([^"]+)"\s+in\s+setting.*?:\s*\n\s+(_scene_\w+)\(draw, post\)'
    for m in re.finditer(route_pattern, render_source):
        route_key, func_name = m.group(1), m.group(2)
        if route_key in setting_lower:
            # Found a route — extract the function source
            func_pattern = rf"(def {re.escape(func_name)}\(draw, post\):.*?)(?=\ndef |\Z)"
            func_match = re.search(func_pattern, render_source, re.DOTALL)
            if func_match:
                return func_name, func_match.group(1).rstrip()
            return func_name, None

    # Strategy 3: Fall back to generic
    indoor_hints = ["office", "room", "store", "shop", "lab", "hospital", "basement",
                    "attic", "library", "museum", "restaurant", "bar", "cafe", "salon"]
    if any(k in setting_lower for k in indoor_hints):
        func_name = "_scene_generic_indoor"
    else:
        func_name = "_scene_generic_outdoor"

    pattern = rf"(def {re.escape(func_name)}\(draw, post\):.*?)(?=\ndef |\Z)"
    match = re.search(pattern, render_source, re.DOTALL)
    if match:
        return func_name, match.group(1).rstrip()
    return func_name, None


# ---------------------------------------------------------------------------
# Critics
# ---------------------------------------------------------------------------

def run_critics(client, image_path, post_data, style_bible):
    """Run all 4 critics in parallel. Returns (reviews, avg_score)."""
    img_b64 = image_to_base64(image_path)
    suffix = Path(image_path).suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"

    context = f"""POST CONTEXT:
- Setting: {post_data.get('setting', '?')}
- Mechanism: {post_data.get('mechanism', '?')}
- Caption: {post_data.get('caption', '?')}
- Hidden touch: {post_data.get('hidden_touch', '?')}
- Scene description: {post_data.get('scene_description', '?')}"""

    def call_critic(critic_key):
        critic = CRITICS[critic_key]
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=critic['system'],
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                    {"type": "text", "text": f"""Review this Spider Death Blog illustration.
{context}

Reply in this EXACT format (nothing else):
SCORE: [1-10]
VERDICT: [one sentence]
ISSUES: [bullet list, most critical first]
SUGGESTION: [single most impactful fix]"""},
                ],
            }],
        )
        return {"critic": critic_key, "name": critic["name"], "emoji": critic["emoji"],
                "review": msg.content[0].text}

    reviews = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(call_critic, k): k for k in CRITICS}
        for future in as_completed(futures):
            try:
                reviews.append(future.result())
            except Exception as e:
                print(f"    Critic {futures[future]} failed: {e}")

    scores = []
    for r in reviews:
        for line in r["review"].split("\n"):
            if line.strip().upper().startswith("SCORE:"):
                after_colon = line.split(":", 1)[1].strip()
                # Handle "7/10", "7 /10", "7", etc.
                m = re.match(r"(\d+)", after_colon)
                if m:
                    s = int(m.group(1))
                    if 1 <= s <= 10:
                        scores.append(s)
                        r["score"] = s
                        break

    avg = sum(scores) / len(scores) if scores else 0
    # Sort by critic order
    order = list(CRITICS.keys())
    reviews.sort(key=lambda r: order.index(r["critic"]))
    return reviews, avg


# ---------------------------------------------------------------------------
# Art Director — complete rewrite with full history + before/after
# ---------------------------------------------------------------------------

ART_DIRECTOR_SYSTEM = """You are the Art Director for Spider Death Blog.

Your job: READ all critic feedback from every round, LOOK at the current image (and previous
image if provided), and WRITE a complete new version of the scene rendering function.

THIS IS A COMPLETE REWRITE, NOT A PATCH. Reimagine the composition from scratch if needed.
You are free to rethink the layout, object placement, and visual storytelling entirely.

{style_bible}

AVAILABLE TOOLS (use these, don't reinvent them):
- draw_spidey(draw, cx, cy, size=22, expression="surprised")
  expressions: surprised, dead, sad, happy, alarmed, content
- draw_sky(draw), draw_sun(draw, x=None, y=None), draw_ground(draw, y=None, color=None, grass=True)
- draw_water(draw, y=None), draw_room(draw, wall_color, floor_color, floor_y)
- draw_checkered_floor(draw, y, size), draw_tile_floor(draw, y, color1, color2, size)
- draw_tree(draw, x, y), draw_palm_tree(draw, x, y, height)
- draw_flower(draw, x, y, color), draw_seagulls(draw, count)
- draw_framed_picture(draw, x, y, w, h, content) — content: "spider_web", "landscape", "tooth"
- draw_framed_text(draw, x, y, text, w, h)
- draw_labeled_box(draw, x, y, w, h, label, fill_color)
- draw_rubber_duck(draw, x, y, size)
- draw_lightning_bolts(draw, x, y, count)
- draw_clock(draw, x, y, r=15)
- draw_potted_plant(draw, x, y, size)
- draw_traffic_cone(draw, x, y, size)
- draw_balloon(draw, x, y, color, size)
- draw_hardhat(draw, x, y, size)
- draw_electrical_outlet(draw, x, y)
- spray_paint(draw, cx, cy, radius, color, density)
- spray_rect(draw, x1, y1, x2, y2, color, density)
- spray_cloud(draw, cx, cy, size)
- speckle_layer(draw, region_tuple, color, density)

COLORS: SKY_BLUE, GRASS_GREEN, DARK_GREEN, LIGHT_GREEN, WATER_BLUE, DEEP_WATER,
SAND_YELLOW, FLOOR_TAN, WALL_YELLOW, WALL_TEAL, WALL_WHITE, WALL_PINK, BROWN,
DARK_BROWN, LIGHT_BROWN, RED, BRIGHT_RED, ORANGE, BRIGHT_ORANGE, YELLOW, GRAY,
LIGHT_GRAY, DARK_GRAY, WHITE, BLACK, LAVA_RED, LAVA_ORANGE, ICE_BLUE, LIGHT_ICE,
PINK, BLUE, LIGHT_BLUE, TEAL, PURPLE, SKIN, FONT

Canvas: 640x480 (WIDTH, HEIGHT). FONT = ImageFont.load_default().

CRITICAL RULES:
1. Output ONLY the Python function. No explanation. No markdown fences. No commentary.
2. Start with "def {func_name}(draw, post):" — the full function.
3. SPIDEY IS THE STAR. He MUST be:
   - Drawn with draw_spidey(draw, cx, cy, size=18) — small but VISIBLE
   - Placed with HIGH CONTRAST against his background (not on gray surfaces!)
   - Clearly IN the death scenario (falling INTO the thing, being crushed BY the thing)
   - NOT just sitting near the danger — he must be actively dying
   - If he's inside something (dryer, mixer, etc.), draw him INSIDE it, centered and visible
4. The death premise must be INSTANTLY readable at a glance.
5. Every object must have CLEAN outlines (width=2 or 3) and be clearly identifiable.
6. Include ALL hidden touches/details mentioned in the post data.
7. Objects must NOT overlap in confusing ways. Leave clear space between elements.
8. DO NOT regress on issues that previous rounds already fixed.
9. Use import math if you need math functions — it's already imported globally.
10. KEEP IT SHORT — 80 LINES MAXIMUM. Use helpers instead of manual drawing.
    draw_room/draw_sky for backgrounds, draw_labeled_box for props. Don't draw
    complex shapes line-by-line when a rectangle + label does the same job.
11. COMPLETE THE FUNCTION. Every ( must have ), every [ must have ], every quote must close.
    Count your brackets before outputting. End cleanly with draw_spidey()."""


def generate_rewrite(client, func_name, func_source, post_data,
                     round_history, style_bible, current_image_path, prev_image_path=None):
    """Art director does a complete rewrite with full history and before/after comparison."""

    # Build the full history narrative
    history_text = ""
    for i, entry in enumerate(round_history, 1):
        history_text += f"\n{'='*40}\nROUND {i} (avg score: {entry['avg_score']:.1f}/10)\n{'='*40}\n"
        for r in entry["reviews"]:
            history_text += f"\n{r['emoji']} {r['name']} (Score: {r.get('score', '?')}/10):\n{r['review']}\n"

    # Build message content with images
    content = []

    # Previous image (if we have one) for before/after comparison
    if prev_image_path and os.path.exists(prev_image_path):
        prev_b64 = image_to_base64(prev_image_path)
        suffix = Path(prev_image_path).suffix.lower()
        mt = "image/png" if suffix == ".png" else "image/jpeg"
        content.append({"type": "text", "text": "PREVIOUS VERSION (for comparison — do not regress on improvements):"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": prev_b64}})

    # Current image
    cur_b64 = image_to_base64(current_image_path)
    suffix = Path(current_image_path).suffix.lower()
    mt = "image/png" if suffix == ".png" else "image/jpeg"
    content.append({"type": "text", "text": "CURRENT VERSION (this is what needs to be improved):"})
    content.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": cur_b64}})

    # The prompt
    content.append({"type": "text", "text": f"""POST DATA:
{json.dumps(post_data, indent=2)}

FULL CRITIC HISTORY (all rounds — pay attention to recurring issues and DO NOT regress):
{history_text}

CURRENT CODE:
```python
{func_source}
```

Write a COMPLETE NEW VERSION of this function. Reimagine the composition to address ALL
recurring critic issues. The death premise must be instantly clear. Every detail must be readable.
Output ONLY the Python function."""})

    system = ART_DIRECTOR_SYSTEM.replace("{style_bible}", style_bible).replace("{func_name}", func_name)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": content}],
    )

    new_code = msg.content[0].text.strip()
    # Strip markdown fences
    if new_code.startswith("```"):
        lines = new_code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        new_code = "\n".join(lines)

    if not new_code.strip().startswith(f"def {func_name}"):
        print(f"    WARNING: Art director output doesn't start with def {func_name}")
        return None

    ok, err = validate_function_code(new_code, func_name)
    if ok:
        return new_code

    # Retry once — ask the model to fix the syntax error
    print(f"    Syntax error in rewrite: {err}. Retrying with fix prompt...")
    fix_msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system,
        messages=[
            {"role": "user", "content": content},
            {"role": "assistant", "content": new_code},
            {"role": "user", "content": f"That code has a syntax error: {err}. Output the COMPLETE corrected function. Close all brackets and quotes. Keep it under 90 lines."},
        ],
    )
    new_code = fix_msg.content[0].text.strip()
    if new_code.startswith("```"):
        lines = new_code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        new_code = "\n".join(lines)

    if not new_code.strip().startswith(f"def {func_name}"):
        return None

    ok, err = validate_function_code(new_code, func_name)
    if not ok:
        print(f"    Retry also failed: {err}")
        return None

    return new_code


SCENE_CREATOR_SYSTEM = """You are the Art Director for Spider Death Blog.

Your job: CREATE a brand new scene rendering function from scratch based on the post description.

{style_bible}

AVAILABLE TOOLS (use these, don't reinvent them):
- draw_spidey(draw, cx, cy, size=22, expression="surprised")
  expressions: surprised, dead, sad, happy, alarmed, content
- draw_sky(draw), draw_sun(draw, x=None, y=None), draw_ground(draw, y=None, color=None, grass=True)
- draw_water(draw, y=None), draw_room(draw, wall_color, floor_color, floor_y)
- draw_checkered_floor(draw, y, size), draw_tile_floor(draw, y, color1, color2, size)
- draw_tree(draw, x, y), draw_palm_tree(draw, x, y, height)
- draw_flower(draw, x, y, color), draw_seagulls(draw, count)
- draw_framed_picture(draw, x, y, w, h, content) — content: "spider_web", "landscape", "tooth"
- draw_framed_text(draw, x, y, text, w, h)
- draw_labeled_box(draw, x, y, w, h, label, fill_color)
- draw_rubber_duck(draw, x, y, size)
- draw_clock(draw, x, y, r=15)
- draw_potted_plant(draw, x, y, size)
- draw_traffic_cone(draw, x, y, size)
- draw_balloon(draw, x, y, color, size)
- draw_hardhat(draw, x, y, size)
- draw_electrical_outlet(draw, x, y)
- spray_paint(draw, cx, cy, radius, color, density)
- spray_cloud(draw, cx, cy, size) — size is a float multiplier (0.5 = small, 1.5 = big)
- draw.rectangle, draw.ellipse, draw.line, draw.polygon, draw.arc, draw.text, draw.rounded_rectangle

COLORS: SKY_BLUE, GRASS_GREEN, DARK_GREEN, LIGHT_GREEN, WATER_BLUE, DEEP_WATER,
SAND_YELLOW, FLOOR_TAN, WALL_YELLOW, WALL_TEAL, WALL_WHITE, WALL_PINK, BROWN,
DARK_BROWN, LIGHT_BROWN, RED, BRIGHT_RED, ORANGE, BRIGHT_ORANGE, YELLOW, GRAY,
LIGHT_GRAY, DARK_GRAY, WHITE, BLACK, LAVA_RED, LAVA_ORANGE, ICE_BLUE, LIGHT_ICE,
PINK, BLUE, LIGHT_BLUE, TEAL, PURPLE, SKIN, FONT

Canvas: 640x480 (WIDTH, HEIGHT). FONT = ImageFont.load_default().

DESIGN PRIORITIES (in order):
1. THE DEATH IS THE HERO. The viewer must understand HOW the spider dies at a glance.
   Compose the scene around the death mechanism — it should be center stage.
2. SPIDEY IS VISIBLE. Draw him with draw_spidey(draw, cx, cy, size=18).
   Place him where he CONTRASTS with the background. He must be actively dying,
   not just standing near danger.
3. HIDDEN TOUCHES EARN THE SECOND LOOK. Include every detail from the post data.
   These are what make someone want to share the image.
4. CLEAN MS PAINT STYLE. Flat color fills for surfaces, NO spray/speckle on walls or floors.
   Thick outlines (width=2-3). Only use spray for clouds, foliage, smoke — things that ARE spray in real MS Paint.
5. LABELED OBJECTS. When in doubt, label it. "SOAP", "REDS", "WET CEMENT" — this is the blog's signature charm.

OUTPUT RULES:
1. Output ONLY the Python function. No explanation. No markdown fences.
2. Start with "def {func_name}(draw, post):"
3. Build the environment FIRST (sky/room, ground/floor), then props, then Spidey last (so he's on top).
4. Use import math if needed — it's already imported globally.
5. KEEP IT SHORT — 80 LINES MAXIMUM. Use helpers instead of manual drawing.
   draw_room/draw_sky for backgrounds, draw_labeled_box for props. Don't draw
   complex shapes line-by-line when a rectangle + label does the same job.
6. COMPLETE THE FUNCTION. Every ( must have ), every [ must have ], every quote must close.
   Count your brackets before outputting. End cleanly with draw_spidey()."""


def validate_function_code(code, func_name):
    """Try to compile a function in isolation. Returns (ok, error_msg)."""
    # Wrap in minimal context so imports/constants don't cause false errors
    test_code = "import math\n" + code
    try:
        compile(test_code, f"{func_name}.py", "exec")
        return True, None
    except SyntaxError as e:
        return False, f"line {e.lineno}: {e.msg}"


def generate_new_scene(client, func_name, post_data, style_bible, max_attempts=2):
    """Art director creates a brand new scene function from post data."""
    system = SCENE_CREATOR_SYSTEM.replace("{style_bible}", style_bible).replace("{func_name}", func_name)

    user_msg = f"""Create a scene rendering function for this Spider Death Blog post.

POST DATA:
{json.dumps(post_data, indent=2)}

Write the complete function "def {func_name}(draw, post):" that renders this scene.
Focus on making the death mechanism instantly readable and the hidden touches delightful."""

    for attempt in range(max_attempts):
        messages = [{"role": "user", "content": user_msg}]
        # On retry, tell the model about the previous error
        if attempt > 0:
            messages.append({"role": "assistant", "content": prev_code})
            messages.append({"role": "user", "content": f"That code has a syntax error: {prev_err}. Please fix it and output the COMPLETE corrected function. Remember to close all brackets and quotes."})

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=system,
            messages=messages,
        )

        new_code = msg.content[0].text.strip()
        if new_code.startswith("```"):
            lines = new_code.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            new_code = "\n".join(lines)

        if not new_code.strip().startswith(f"def {func_name}"):
            print(f"    WARNING: Scene creator output doesn't start with def {func_name}")
            return None

        ok, err = validate_function_code(new_code, func_name)
        if ok:
            return new_code

        print(f"    Syntax error (attempt {attempt + 1}): {err}")
        prev_code = new_code
        prev_err = err

    print(f"    Failed after {max_attempts} attempts")
    return None


def inject_new_scene(render_source, func_name, func_code, setting, mechanism):
    """Add a new scene function and routing entry to render.py."""
    # Skip if this function already exists (avoid duplicates)
    if f"def {func_name}(draw, post):" in render_source:
        # Replace existing function instead of adding a new one
        pattern = rf"(def {re.escape(func_name)}\(draw, post\):.*?)(?=\ndef |\Z)"
        match = re.search(pattern, render_source, re.DOTALL)
        if match:
            func_code = func_code.rstrip() + "\n"
            render_source = render_source[:match.start()] + func_code + "\n\n" + render_source[match.end():]
            return render_source

    # Add the function before the generic scenes
    marker = "def _scene_generic_indoor"
    if marker not in render_source:
        marker = "def _scene_generic_outdoor"
    idx = render_source.find(marker)
    if idx == -1:
        print("    ERROR: Could not find insertion point in render.py")
        return None

    # Ensure function code ends with a clean newline
    func_code = func_code.rstrip() + "\n"
    render_source = render_source[:idx] + func_code + "\n\n" + render_source[idx:]

    # Add routing entry — but only if one doesn't already exist
    setting_key = setting.lower()
    if f'"{setting_key}" in setting' in render_source:
        # Route already exists, skip
        return render_source

    # Insert elif before the else: fallback
    else_marker = '\n    else:\n        # Smart fallback'
    else_idx = render_source.find(else_marker)
    if else_idx == -1:
        print("    WARNING: Could not add routing entry")
        return render_source

    route_line = f'\n    elif "{setting_key}" in setting:\n        {func_name}(draw, post)'
    render_source = render_source[:else_idx] + route_line + render_source[else_idx:]

    return render_source


def apply_code_fix(render_source, scene_func_name, new_func_code):
    """Replace a scene function in render.py with the new version."""
    pattern = rf"(def {re.escape(scene_func_name)}\(draw, post\):.*?)(?=\ndef |\Z)"
    match = re.search(pattern, render_source, re.DOTALL)
    if not match:
        print(f"    ERROR: Could not find {scene_func_name} in render.py")
        return None
    return render_source[:match.start()] + new_func_code + "\n\n" + render_source[match.end():]


def render_single(batch_path, index):
    """Render a single draft and return the image path."""
    import importlib
    import render as render_module
    importlib.reload(render_module)

    with open(batch_path) as f:
        posts = json.load(f)

    post = posts[index]
    import random
    random.seed(hash(json.dumps(post, sort_keys=True)))

    img = render_module.render_scene(post)
    setting_slug = post.get("setting", "scene").replace(" ", "_")
    filename = f"draft_{index + 1}_{setting_slug}.png"
    filepath = Path(batch_path).parent / filename
    img.save(filepath)
    return str(filepath), post


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------

def print_round_summary(round_num, reviews, avg_score, prev_score=None):
    """Print a compact summary of one review round."""
    delta = ""
    if prev_score is not None:
        diff = avg_score - prev_score
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
        delta = f"  ({arrow} {abs(diff):.1f})"

    print(f"\n  {'─'*55}")
    print(f"  Round {round_num} — Score: {avg_score:.1f}/10{delta}")
    print(f"  {'─'*55}")
    for r in reviews:
        score = r.get("score", "?")
        verdict = ""
        for line in r["review"].split("\n"):
            if line.strip().upper().startswith("VERDICT:"):
                verdict = line.split(":", 1)[1].strip()
                break
        print(f"  {r['emoji']} {score}/10 — {verdict[:65]}")


# ---------------------------------------------------------------------------
# Main improvement loop
# ---------------------------------------------------------------------------

def improve_single(client, batch_path, index, threshold=8.0, max_rounds=3):
    """Run the full improve loop for a single draft."""
    style_bible = load_style_bible()
    round_history = []      # full critic history for art director
    prev_image_path = None  # for before/after comparison
    best_score = 0
    best_render_source = None  # saved so we can rollback on regression

    # Create a versions directory to save each round's image
    versions_dir = Path(batch_path).parent / "versions"
    versions_dir.mkdir(exist_ok=True)

    # Load post data to check if we need to create a scene function
    with open(batch_path) as f:
        posts = json.load(f)
    post_data = posts[index]
    setting = post_data.get("setting", "?")
    mechanism = post_data.get("mechanism", "")

    print(f"\n{'='*60}")
    print(f"  Scene: {setting}")
    print(f"{'='*60}")

    # Step 0: Create scene function if none exists for this post
    render_source = load_render_source()
    func_name, func_source = find_scene_function(render_source, setting, mechanism)

    if func_name in ("_scene_generic_outdoor", "_scene_generic_indoor") or not func_source:
        # No dedicated scene — create one from scratch
        setting_slug = setting.lower().replace(" ", "_").replace("/", "_")
        new_func_name = f"_scene_{setting_slug}"
        print(f"\n  Creating new scene function: {new_func_name}...")

        new_code = generate_new_scene(client, new_func_name, post_data, style_bible)
        if new_code:
            new_source = inject_new_scene(render_source, new_func_name, new_code, setting, mechanism)
            if new_source:
                try:
                    compile(new_source, RENDER_PATH, "exec")
                    save_render_source(new_source)
                    func_name = new_func_name
                    print(f"  Created and injected {new_func_name}")
                except SyntaxError as e:
                    print(f"  Syntax error in generated scene: {e}")
                    print(f"  Falling back to generic scene")

    for round_num in range(1, max_rounds + 1):
        # Step 1: Render
        print(f"\n  Round {round_num}: Rendering...")
        try:
            image_path, post_data = render_single(batch_path, index)
        except Exception as e:
            print(f"    Runtime error during render: {e}")
            # Rollback to best version if we have one
            if best_render_source:
                save_render_source(best_render_source)
                print(f"    Rolled back to best version. Retrying...")
            continue

        # Save versioned copy for before/after tracking
        setting_slug = setting.replace(" ", "_")
        version_path = versions_dir / f"{setting_slug}_v{round_num}.png"
        shutil.copy2(image_path, version_path)

        # Step 2: Review with 4 critics
        print(f"  Round {round_num}: Reviewing with 4 critics...")
        reviews, avg_score = run_critics(client, image_path, post_data, style_bible)

        # Store in history
        round_history.append({
            "round": round_num,
            "avg_score": avg_score,
            "reviews": reviews,
            "image_path": str(version_path),
        })

        prev_score = best_score if best_score > 0 else None
        print_round_summary(round_num, reviews, avg_score, prev_score)

        # Rollback check: if we regressed, revert to the best version
        if round_num > 1 and avg_score < best_score:
            print(f"\n  ⚠ Regression! {avg_score:.1f} < {best_score:.1f}. Rolling back to best version.")
            save_render_source(best_render_source)
            # Don't update best — keep the previous best
        else:
            best_score = avg_score
            best_render_source = load_render_source()

        # Step 3: Check threshold
        if best_score >= threshold:
            print(f"\n  ✓ Best score {best_score:.1f} meets threshold {threshold}. Done!")
            print(f"  Versions saved in: {versions_dir}/")
            return best_score

        if round_num == max_rounds:
            print(f"\n  Max rounds reached. Best score: {best_score:.1f}/10")
            print(f"  Versions saved in: {versions_dir}/")
            return best_score

        # Step 4: Art Director complete rewrite
        print(f"\n  Round {round_num}: Art Director rewriting (with {len(round_history)} rounds of history)...")
        render_source = load_render_source()
        func_name, func_source = find_scene_function(
            render_source, post_data.get("setting", ""), post_data.get("mechanism", ""))

        # NEVER rewrite generic scene functions — they're shared across posts
        if func_name in ("_scene_generic_outdoor", "_scene_generic_indoor"):
            print(f"    Skipping rewrite — {func_name} is shared. Attempting scene creation instead...")
            setting_slug = setting.lower().replace(" ", "_").replace("/", "_")
            new_func_name = f"_scene_{setting_slug}"
            new_code = generate_new_scene(client, new_func_name, post_data, style_bible)
            if new_code:
                new_source = inject_new_scene(render_source, new_func_name, new_code, setting, mechanism)
                if new_source:
                    try:
                        compile(new_source, RENDER_PATH, "exec")
                        save_render_source(new_source)
                        func_name = new_func_name
                        print(f"    Created {new_func_name} instead")
                    except SyntaxError as e:
                        print(f"    Scene creation failed: {e}")
            continue

        if not func_source:
            print(f"    Could not find scene function {func_name}. Continuing...")
            continue

        new_code = generate_rewrite(
            client, func_name, func_source, post_data,
            round_history, style_bible, image_path, prev_image_path)

        if not new_code:
            print("    Art Director failed to generate valid code. Retrying next round...")
            continue

        # Step 5: Apply and validate
        new_source = apply_code_fix(render_source, func_name, new_code)
        if not new_source:
            continue

        try:
            compile(new_source, RENDER_PATH, "exec")
        except SyntaxError as e:
            print(f"    Syntax error: {e}. Retrying next round...")
            continue

        save_render_source(new_source)
        prev_image_path = str(version_path)  # current becomes "previous" for next round
        print(f"  Round {round_num}: Rewrote {func_name}. Moving to next round...")

    return best_score


def main():
    parser = argparse.ArgumentParser(description="Auto-improve Spider Death Blog illustrations")
    parser.add_argument("batch_file", help="Path to a batch JSON file")
    parser.add_argument("--index", type=int, default=None,
                        help="Improve only the draft at this index (0-based)")
    parser.add_argument("--threshold", type=float, default=8.0,
                        help="Stop when average critic score reaches this (default: 8.0)")
    parser.add_argument("--max-rounds", type=int, default=3,
                        help="Maximum improvement rounds per image (default: 3)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY in .env first.")
        sys.exit(1)

    if not os.path.exists(args.batch_file):
        print(f"Error: {args.batch_file} not found")
        sys.exit(1)

    with open(args.batch_file) as f:
        posts = json.load(f)

    from costs import TrackedClient
    client = TrackedClient()

    if args.index is not None:
        indices = [args.index]
    else:
        indices = list(range(len(posts)))

    results = {}
    for idx in indices:
        setting = posts[idx].get("setting", "?")
        score = improve_single(client, args.batch_file, idx,
                                threshold=args.threshold, max_rounds=args.max_rounds)
        results[setting] = score

    # Final summary
    print(f"\n{'='*60}")
    print(f"  FINAL RESULTS")
    print(f"{'='*60}")
    for setting, score in results.items():
        status = "✓" if score >= args.threshold else "○"
        print(f"  {status} {setting}: {score:.1f}/10")

    avg_all = sum(results.values()) / len(results) if results else 0
    print(f"\n  Overall average: {avg_all:.1f}/10")
    print()


if __name__ == "__main__":
    main()
