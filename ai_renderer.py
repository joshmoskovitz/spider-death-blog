#!/usr/bin/env python3
"""
Spider Death Blog — AI Scene Renderer

Generates Pillow drawing code for any spider death scene description using Claude,
then executes it safely within a restricted namespace containing only our existing
drawing primitives.

This module powers the "Create Your Own Spider Death" feature. It accepts a
scene_description (from the post concept) and returns a rendered PIL Image.
"""

import io
import math
import random
import re
import traceback
from typing import Optional, Tuple

import anthropic
from PIL import Image, ImageDraw, ImageFont

# Import all drawing primitives from render.py so they're available to generated code
from render import (
    WIDTH, HEIGHT, FONT,
    # Colors
    SKY_BLUE, GRASS_GREEN, DARK_GREEN, LIGHT_GREEN, WATER_BLUE, DEEP_WATER,
    SAND_YELLOW, FLOOR_TAN, WALL_YELLOW, WALL_TEAL, WALL_WHITE, WALL_PINK,
    BROWN, DARK_BROWN, LIGHT_BROWN, RED, BRIGHT_RED, ORANGE, BRIGHT_ORANGE,
    YELLOW, GRAY, LIGHT_GRAY, DARK_GRAY, WHITE, BLACK,
    LAVA_RED, LAVA_ORANGE, ICE_BLUE, LIGHT_ICE, PINK, BLUE, LIGHT_BLUE,
    TEAL, PURPLE, SKIN, GREEN, CREAM, SILVER, GOLD, MAROON, NAVY, BEIGE,
    TAN, CYAN, MAGENTA, LIME,
    # Drawing primitives
    spray_paint, spray_rect, speckle_layer, spray_cloud,
    draw_spidey,
    draw_palm_tree, draw_seagulls, draw_flower, draw_tree,
    draw_electrical_outlet, draw_framed_picture, draw_framed_text,
    draw_labeled_box, draw_rubber_duck, draw_lightning_bolts, draw_clock,
    draw_shelf, draw_potted_plant, draw_traffic_cone, draw_balloon,
    draw_hardhat,
    draw_sky, draw_sun, draw_ground, draw_water,
    draw_room, draw_checkered_floor, draw_tile_floor,
)


# The restricted namespace: only these names are available to generated code.
# This prevents filesystem access, network calls, imports, etc.
RENDERING_NAMESPACE = {
    # Python builtins needed for drawing math
    "int": int,
    "float": float,
    "abs": abs,
    "min": min,
    "max": max,
    "range": range,
    "len": len,
    "round": round,
    "enumerate": enumerate,
    "list": list,
    "tuple": tuple,
    # Math
    "math": math,
    "random": random,
    # Pillow (read-only — we provide the Image and Draw objects)
    "Image": Image,
    "ImageDraw": ImageDraw,
    "ImageFont": ImageFont,
    # Canvas constants
    "WIDTH": WIDTH,
    "HEIGHT": HEIGHT,
    "FONT": FONT,
    # Colors
    "SKY_BLUE": SKY_BLUE, "GRASS_GREEN": GRASS_GREEN, "DARK_GREEN": DARK_GREEN,
    "LIGHT_GREEN": LIGHT_GREEN, "WATER_BLUE": WATER_BLUE, "DEEP_WATER": DEEP_WATER,
    "SAND_YELLOW": SAND_YELLOW, "FLOOR_TAN": FLOOR_TAN,
    "WALL_YELLOW": WALL_YELLOW, "WALL_TEAL": WALL_TEAL,
    "WALL_WHITE": WALL_WHITE, "WALL_PINK": WALL_PINK,
    "BROWN": BROWN, "DARK_BROWN": DARK_BROWN, "LIGHT_BROWN": LIGHT_BROWN,
    "RED": RED, "BRIGHT_RED": BRIGHT_RED,
    "ORANGE": ORANGE, "BRIGHT_ORANGE": BRIGHT_ORANGE,
    "YELLOW": YELLOW, "GRAY": GRAY, "LIGHT_GRAY": LIGHT_GRAY,
    "DARK_GRAY": DARK_GRAY, "WHITE": WHITE, "BLACK": BLACK,
    "LAVA_RED": LAVA_RED, "LAVA_ORANGE": LAVA_ORANGE,
    "ICE_BLUE": ICE_BLUE, "LIGHT_ICE": LIGHT_ICE,
    "PINK": PINK, "BLUE": BLUE, "LIGHT_BLUE": LIGHT_BLUE,
    "TEAL": TEAL, "PURPLE": PURPLE, "SKIN": SKIN,
    "GREEN": GREEN, "CREAM": CREAM, "SILVER": SILVER, "GOLD": GOLD,
    "MAROON": MAROON, "NAVY": NAVY, "BEIGE": BEIGE, "TAN": TAN,
    "CYAN": CYAN, "MAGENTA": MAGENTA, "LIME": LIME,
    # Drawing primitives
    "spray_paint": spray_paint, "spray_rect": spray_rect,
    "speckle_layer": speckle_layer, "spray_cloud": spray_cloud,
    "draw_spidey": draw_spidey,
    "draw_palm_tree": draw_palm_tree, "draw_seagulls": draw_seagulls,
    "draw_flower": draw_flower, "draw_tree": draw_tree,
    "draw_electrical_outlet": draw_electrical_outlet,
    "draw_framed_picture": draw_framed_picture,
    "draw_framed_text": draw_framed_text,
    "draw_labeled_box": draw_labeled_box,
    "draw_rubber_duck": draw_rubber_duck,
    "draw_lightning_bolts": draw_lightning_bolts,
    "draw_clock": draw_clock, "draw_shelf": draw_shelf,
    "draw_potted_plant": draw_potted_plant,
    "draw_traffic_cone": draw_traffic_cone,
    "draw_balloon": draw_balloon, "draw_hardhat": draw_hardhat,
    "draw_sky": draw_sky, "draw_sun": draw_sun,
    "draw_ground": draw_ground, "draw_water": draw_water,
    "draw_room": draw_room, "draw_checkered_floor": draw_checkered_floor,
    "draw_tile_floor": draw_tile_floor,
}


CODEGEN_SYSTEM_PROMPT = """\
You are an MS Paint artist for Spider Death Blog. You write Python/Pillow code \
to draw crude, charming, 640x480 illustrations of a small spider dying in \
whimsical ways.

STYLE RULES:
- Flat, bright colors. No gradients, no anti-aliasing, no realism.
- Use spray_paint() ONLY for clouds, smoke, fire, lava, tree canopies — never \
as a background filter.
- Backgrounds (walls, floors, sky) are flat color rectangle fills.
- Props are simple geometric shapes: rectangles, ellipses, polygons, lines.
- The spider (Spidey) MUST appear in every scene. Use draw_spidey(draw, x, y, \
size, expression). Expressions: "surprised", "dead", "sad", "happy", "alarmed", "content".
- Spidey should be clearly visible — not hidden or tiny. Typical size=18-26.
- Add 1-2 charming hidden details (a smiley sun, a sign, a tiny accessory).
- The scene should be instantly readable: glance at it and understand the death.

AVAILABLE OBJECTS:
You have `draw` (an ImageDraw.Draw object) and `img` (the PIL Image) pre-created.
Canvas is 640x480. You also have these helper functions:

Background helpers:
  draw_sky(draw) — blue sky with clouds
  draw_sun(draw, x=None, y=None, has_face=True) — sun with optional smiley face
  draw_ground(draw, y=None, color=None, grass=True) — ground with optional grass tufts
  draw_water(draw, y=None) — water surface
  draw_room(draw, wall_color=None, floor_color=None, floor_y=None) — indoor room
  draw_checkered_floor(draw, y=None, size=45) — checkered floor
  draw_tile_floor(draw, y=None, color1=None, color2=None, size=50) — tiled floor

Props:
  draw_spidey(draw, cx, cy, size=22, expression="surprised") — THE STAR
  draw_palm_tree(draw, x, y, height=120)
  draw_seagulls(draw, count=3)
  draw_flower(draw, x, y, color=None)
  draw_tree(draw, x, y)
  draw_electrical_outlet(draw, x, y)
  draw_framed_picture(draw, x, y, w=100, h=70, content="art")
  draw_framed_text(draw, x, y, text, w=110, h=75)
  draw_labeled_box(draw, x, y, w, h, label, fill_color, label_color=BLACK)
  draw_rubber_duck(draw, x, y, size=15)
  draw_lightning_bolts(draw, x, y, count=3)
  draw_clock(draw, x, y, r=15)
  draw_shelf(draw, x1, x2, y, items=None)
  draw_potted_plant(draw, x, y, size=1.0)
  draw_traffic_cone(draw, x, y, size=1.0)
  draw_balloon(draw, x, y, color, size=20)
  draw_hardhat(draw, x, y, size=1.0)

Texture helpers:
  spray_paint(draw, cx, cy, radius, color, density=200) — spray-paint circle
  spray_rect(draw, x1, y1, x2, y2, color, density=None) — spray-paint rectangle
  spray_cloud(draw, cx, cy, size=1.0) — fluffy cloud cluster
  speckle_layer(draw, region, color, density=300) — random noise

Colors (all RGB tuples): SKY_BLUE, GRASS_GREEN, DARK_GREEN, LIGHT_GREEN, \
WATER_BLUE, DEEP_WATER, SAND_YELLOW, FLOOR_TAN, WALL_YELLOW, WALL_TEAL, \
WALL_WHITE, WALL_PINK, BROWN, DARK_BROWN, LIGHT_BROWN, RED, BRIGHT_RED, \
ORANGE, BRIGHT_ORANGE, YELLOW, GRAY, LIGHT_GRAY, DARK_GRAY, WHITE, BLACK, \
LAVA_RED, LAVA_ORANGE, ICE_BLUE, LIGHT_ICE, PINK, BLUE, LIGHT_BLUE, TEAL, \
PURPLE, SKIN, GREEN, CREAM, SILVER, GOLD, MAROON, NAVY, BEIGE, TAN, CYAN, \
MAGENTA, LIME

Also available: math, random, int, float, abs, min, max, range, round, \
enumerate, len, list, tuple.
FONT is a loaded ImageFont for draw.text().

OUTPUT RULES:
- Output ONLY Python code. No markdown fences, no explanation.
- The code draws directly onto the provided `draw` and `img` objects.
- Do NOT create a new Image or call img.save() — just draw.
- Do NOT use import statements — everything is pre-provided.
- Do NOT use open(), exec(), eval(), __import__, os, sys, subprocess, or any \
file/network operations.
- Keep the code under 200 lines. Simple scenes are better.
- ALWAYS call draw_spidey() exactly once.
"""


def _validate_generated_code(code: str) -> Optional[str]:
    """
    Check generated code for dangerous operations.
    Returns an error message if the code is unsafe, None if it passes.
    """
    forbidden_patterns = [
        (r'\bimport\b', "import statements are not allowed"),
        (r'\b__import__\b', "__import__ is not allowed"),
        (r'\bopen\s*\(', "file operations are not allowed"),
        (r'\bexec\s*\(', "exec() is not allowed"),
        (r'\beval\s*\(', "eval() is not allowed"),
        (r'\bos\.', "os module access is not allowed"),
        (r'\bsys\.', "sys module access is not allowed"),
        (r'\bsubprocess', "subprocess is not allowed"),
        (r'\b__builtins__', "builtins access is not allowed"),
        (r'\bglobals\s*\(', "globals() is not allowed"),
        (r'\blocals\s*\(', "locals() is not allowed"),
        (r'\bgetattr\s*\(', "getattr() is not allowed"),
        (r'\bsetattr\s*\(', "setattr() is not allowed"),
        (r'\bdelattr\s*\(', "delattr() is not allowed"),
        (r'\bcompile\s*\(', "compile() is not allowed"),
        (r'\.save\s*\(', ".save() is not allowed"),
        (r'\.write\s*\(', ".write() is not allowed"),
    ]
    for pattern, message in forbidden_patterns:
        if re.search(pattern, code):
            return message
    return None


def generate_scene_code(scene_description: str, client: anthropic.Anthropic) -> str:
    """Ask Claude to write Pillow drawing code for the given scene."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=CODEGEN_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Draw this spider death scene:\n\n{scene_description}\n\n"
                "Write the Pillow drawing code. Output ONLY code, nothing else."
            ),
        }],
    )
    code = message.content[0].text.strip()
    # Strip markdown fences if the model includes them despite instructions
    if code.startswith("```"):
        lines = code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        code = "\n".join(lines)
    return code


def execute_scene_code(code: str) -> Image.Image:
    """
    Execute generated Pillow code in a restricted namespace.
    Returns the rendered PIL Image.

    Raises ValueError if the code is unsafe.
    Raises RuntimeError if execution fails.
    """
    safety_error = _validate_generated_code(code)
    if safety_error:
        raise ValueError(f"Generated code failed safety check: {safety_error}")

    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    namespace = dict(RENDERING_NAMESPACE)
    namespace["__builtins__"] = {}
    namespace["img"] = img
    namespace["draw"] = draw

    try:
        # Use a single dict for both globals and locals so that functions
        # defined in the generated code can access draw, img, colors, etc.
        exec(code, namespace)
    except Exception as e:
        raise RuntimeError(
            f"Scene rendering failed: {type(e).__name__}: {e}\n"
            f"{traceback.format_exc()}"
        )

    return img


def render_from_description(
    scene_description: str,
    client: anthropic.Anthropic,
    max_retries: int = 2,
) -> Tuple[Image.Image, str]:
    """
    Full pipeline: generate drawing code for a scene, execute it, return the image.

    Returns (image, code) tuple.
    Retries on execution failure up to max_retries times.
    """
    last_error = None
    for attempt in range(1 + max_retries):
        code = generate_scene_code(scene_description, client)
        try:
            img = execute_scene_code(code)
            return img, code
        except (ValueError, RuntimeError) as e:
            last_error = e
            if attempt < max_retries:
                # On retry, include the error so Claude can fix it
                scene_description = (
                    f"{scene_description}\n\n"
                    f"PREVIOUS ATTEMPT FAILED with: {e}\n"
                    f"Please fix the code and try again."
                )
    raise RuntimeError(f"Failed to render scene after {1 + max_retries} attempts: {last_error}")
