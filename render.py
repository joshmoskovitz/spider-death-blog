#!/usr/bin/env python3
"""
Spider Death Blog — Image Renderer v2

Renders MS Paint-style illustrations for spider death posts using Pillow.
Aims to match the dense, charming, detail-packed style of the original blog.

Usage:
    python3 render.py drafts/batch_XXXXX.json          # render all drafts in batch
    python3 render.py drafts/batch_XXXXX.json --index 0 # render just the first draft
"""

import argparse
import json
import math
import os
import re
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Canvas size matches the originals
WIDTH, HEIGHT = 640, 480

# House palette — bright flat colors from the original posts
SKY_BLUE = (173, 233, 250)
GRASS_GREEN = (80, 200, 80)
DARK_GREEN = (30, 150, 30)
LIGHT_GREEN = (140, 220, 100)
WATER_BLUE = (80, 180, 230)
DEEP_WATER = (50, 100, 200)
SAND_YELLOW = (230, 220, 130)
FLOOR_TAN = (220, 195, 165)
WALL_YELLOW = (250, 210, 90)
WALL_TEAL = (100, 210, 180)
WALL_WHITE = (240, 240, 240)
WALL_PINK = (255, 210, 210)
BROWN = (140, 90, 40)
DARK_BROWN = (100, 60, 20)
LIGHT_BROWN = (180, 140, 80)
RED = (220, 40, 30)
BRIGHT_RED = (255, 30, 30)
ORANGE = (240, 160, 40)
BRIGHT_ORANGE = (255, 140, 0)
YELLOW = (255, 240, 50)
GRAY = (180, 180, 180)
LIGHT_GRAY = (210, 210, 210)
DARK_GRAY = (100, 100, 100)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LAVA_RED = (220, 60, 20)
LAVA_ORANGE = (240, 140, 20)
ICE_BLUE = (180, 220, 245)
LIGHT_ICE = (210, 235, 250)
PINK = (240, 150, 170)
BLUE = (60, 120, 220)
LIGHT_BLUE = (140, 190, 240)
TEAL = (80, 200, 200)
PURPLE = (160, 80, 200)
SKIN = (220, 185, 150)

# Aliases — AI-generated scene code sometimes uses these shorthand names
GREEN = GRASS_GREEN
CREAM = (255, 253, 230)
SILVER = LIGHT_GRAY
GOLD = (218, 165, 32)
MAROON = (128, 0, 0)
NAVY = (0, 0, 128)
BEIGE = (245, 235, 220)
TAN = FLOOR_TAN
CYAN = TEAL
MAGENTA = (200, 0, 200)
LIME = LIGHT_GREEN

FONT = ImageFont.load_default()


# ===========================================================================
# Texture helpers — the spray-paint look
# ===========================================================================

def spray_paint(draw, cx, cy, radius, color, density=200):
    """Spray-paint circle effect, like the MS Paint spray can tool."""
    for _ in range(int(density)):
        angle = random.uniform(0, 2 * math.pi)
        r = random.gauss(0, radius / 2.5)
        x = int(cx + r * math.cos(angle))
        y = int(cy + r * math.sin(angle))
        draw.point((x, y), fill=color)


def spray_rect(draw, x1, y1, x2, y2, color, density=None):
    """Fill a rectangle with spray-paint texture."""
    area = abs((x2 - x1) * (y2 - y1))
    if density is None:
        density = max(100, area // 3)
    for _ in range(int(density)):
        x = random.randint(min(x1, x2), max(x1, x2))
        y = random.randint(min(y1, y2), max(y1, y2))
        draw.point((x, y), fill=color)


def speckle_layer(draw, region, color, density=300):
    """Add random speckle/noise over a region for that handmade feel."""
    x1, y1, x2, y2 = region
    for _ in range(int(density)):
        x = random.randint(x1, x2)
        y = random.randint(y1, y2)
        draw.point((x, y), fill=color)


def spray_cloud(draw, cx, cy, size=1.0):
    """A fluffy spray-paint cloud cluster."""
    s = int(40 * size)
    spray_paint(draw, cx, cy, s, WHITE, density=int(800 * size))
    spray_paint(draw, cx + int(35 * size), cy - int(8 * size), int(28 * size), WHITE, density=int(500 * size))
    spray_paint(draw, cx - int(30 * size), cy + int(5 * size), int(25 * size), WHITE, density=int(400 * size))
    spray_paint(draw, cx + int(10 * size), cy + int(15 * size), int(20 * size), WHITE, density=int(300 * size))


# ===========================================================================
# Spidey — the star of the show
# ===========================================================================

def draw_spidey(draw, cx, cy, size=22, expression="surprised"):
    """
    Draw Spidey at (cx, cy). Matches the original blog art style:
    thick straight legs, round gray body, big white eyes with pupils.

    The thick black outline on the body and legs provides natural contrast
    against any background — no halo needed.

    Expressions: surprised, dead, sad, happy, alarmed, content
    """
    body_color = (150, 150, 150)
    leg_color = BLACK

    body_w = size
    body_h = int(size * 0.75)
    leg_width = max(3, size // 4)  # thicker legs than before
    leg_len = int(size * 2.2)      # long dramatic legs like the original art

    # Leg angles — 4 per side, simple straight lines radiating out (no knees)
    leg_angles = [-60, -25, 15, 50]  # degrees from horizontal

    # --- LEGS --- thick straight black lines, drawn before body
    for side in [-1, 1]:
        for i, angle_deg in enumerate(leg_angles):
            attach_x = cx + side * (body_w - 2)
            attach_y = cy + int(body_h * 0.3 * (i - 1.5) / 1.5)
            rad = math.radians(angle_deg)
            tip_x = attach_x + side * int(leg_len * math.cos(rad))
            tip_y = attach_y + int(leg_len * math.sin(rad))
            draw.line([(attach_x, attach_y), (tip_x, tip_y)],
                      fill=leg_color, width=leg_width)

    # --- BODY --- gray oval with thick black outline, drawn OVER leg roots
    draw.ellipse(
        [cx - body_w, cy - body_h, cx + body_w, cy + body_h],
        fill=body_color, outline=BLACK, width=max(3, size // 6)
    )

    # --- FACE --- big expressive eyes like the original
    eye_size = max(4, size // 3)  # bigger than before
    eye_y = cy - body_h // 4
    left_eye_x = cx - body_w // 3
    right_eye_x = cx + body_w // 3

    if expression == "dead":
        s = eye_size
        for ex in [left_eye_x, right_eye_x]:
            draw.line([(ex - s, eye_y - s), (ex + s, eye_y + s)], fill=BLACK, width=2)
            draw.line([(ex + s, eye_y - s), (ex - s, eye_y + s)], fill=BLACK, width=2)
    else:
        for ex in [left_eye_x, right_eye_x]:
            # Big white sclera with black outline
            draw.ellipse([ex - eye_size, eye_y - eye_size, ex + eye_size, eye_y + eye_size],
                         fill=WHITE, outline=BLACK, width=2)
            # Pupil
            pupil = max(2, eye_size // 2)
            draw.ellipse([ex - pupil, eye_y - pupil, ex + pupil, eye_y + pupil], fill=BLACK)

    mouth_y = cy + body_h // 3
    mouth_w = max(4, size // 3)
    if expression == "surprised":
        r = max(3, mouth_w // 2)
        draw.ellipse([cx - r, mouth_y - r, cx + r, mouth_y + r], fill=BLACK)
    elif expression == "sad":
        draw.arc([cx - mouth_w, mouth_y - mouth_w // 2, cx + mouth_w, mouth_y + mouth_w],
                  start=200, end=340, fill=BLACK, width=2)
    elif expression == "happy":
        draw.arc([cx - mouth_w, mouth_y - mouth_w, cx + mouth_w, mouth_y],
                  start=10, end=170, fill=BLACK, width=2)
    elif expression == "alarmed":
        draw.ellipse([cx - mouth_w, mouth_y - 3, cx + mouth_w, mouth_y + 5], fill=BLACK)
    elif expression == "dead":
        draw.line([(cx - mouth_w, mouth_y), (cx + mouth_w, mouth_y)], fill=BLACK, width=2)
    elif expression == "content":
        draw.arc([cx - mouth_w, mouth_y - mouth_w, cx + mouth_w, mouth_y],
                  start=20, end=160, fill=BLACK, width=2)
    else:
        draw.ellipse([cx - 3, mouth_y - 2, cx + 3, mouth_y + 2], fill=BLACK)


# ===========================================================================
# Reusable prop primitives — building blocks for rich scenes
# ===========================================================================

def draw_palm_tree(draw, x, y, height=120):
    """Palm tree with cross-hatched trunk and droopy fronds."""
    # Trunk
    tw = 12
    for ty in range(y, y - height, -4):
        draw.line([(x - tw // 2, ty), (x + tw // 2, ty)], fill=BROWN, width=2)
        draw.line([(x - tw // 2, ty), (x + tw // 2, ty + 3)], fill=DARK_BROWN, width=1)
    top_y = y - height
    # Fronds — big droopy green arcs
    for angle_offset in [-50, -20, 10, 40, 70]:
        rad = math.radians(angle_offset)
        ex = x + int(60 * math.cos(rad))
        ey = top_y + int(40 * math.sin(rad)) - 10
        # Draw thick curved frond
        mid_x = x + int(30 * math.cos(rad))
        mid_y = top_y - 15
        draw.line([(x, top_y), (mid_x, mid_y), (ex, ey)], fill=(30, 170, 30), width=5)
        draw.line([(x, top_y), (mid_x, mid_y - 3), (ex - 5, ey + 5)], fill=DARK_GREEN, width=3)


def draw_seagulls(draw, count=3):
    """Simple V-shaped birds in the sky."""
    for _ in range(count):
        bx = random.randint(100, WIDTH - 100)
        by = random.randint(30, 150)
        draw.arc([bx - 8, by - 5, bx, by + 5], start=200, end=340, fill=BLACK, width=2)
        draw.arc([bx, by - 5, bx + 8, by + 5], start=200, end=340, fill=BLACK, width=2)


def draw_flower(draw, x, y, color=None):
    """A tiny MS Paint flower."""
    color = color or random.choice([PINK, YELLOW, ORANGE, (255, 100, 100)])
    # Stem
    draw.line([(x, y), (x, y + 20)], fill=DARK_GREEN, width=2)
    # Petals
    r = 5
    for angle in range(0, 360, 72):
        px = x + int(r * math.cos(math.radians(angle)))
        py = y + int(r * math.sin(math.radians(angle)))
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=color)
    # Center
    draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=YELLOW)


def draw_tree(draw, x, y):
    """A simple tree with brown trunk and spray-paint foliage."""
    # Trunk
    draw.rectangle([x - 8, y, x + 8, y + 60], fill=BROWN, outline=DARK_BROWN, width=2)
    # Hole in trunk
    draw.ellipse([x - 4, y + 30, x + 4, y + 40], fill=DARK_BROWN)
    # Foliage
    spray_paint(draw, x, y - 15, 35, GRASS_GREEN, density=800)
    spray_paint(draw, x - 15, y - 5, 25, DARK_GREEN, density=400)
    spray_paint(draw, x + 15, y - 10, 25, LIGHT_GREEN, density=300)


def draw_electrical_outlet(draw, x, y):
    """Wall outlet with optional cord."""
    draw.rectangle([x, y, x + 20, y + 28], fill=WHITE, outline=BLACK, width=2)
    draw.rectangle([x + 6, y + 6, x + 8, y + 12], fill=BLACK)
    draw.rectangle([x + 12, y + 6, x + 14, y + 12], fill=BLACK)


def draw_framed_picture(draw, x, y, w=100, h=70, content="art"):
    """A framed picture on a wall with actual content inside."""
    # Frame
    draw.rectangle([x, y, x + w, y + h], fill=WHITE, outline=BLACK, width=3)
    draw.rectangle([x + 4, y + 4, x + w - 4, y + h - 4], outline=GRAY, width=1)
    inner_x, inner_y = x + 8, y + 8
    iw, ih = w - 16, h - 16

    if content == "spider_web":
        # Spider web pattern like the original bathtub scene
        cx, cy = inner_x + iw // 2, inner_y + ih // 2
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            draw.line([(cx, cy), (cx + int(iw // 2 * math.cos(rad)),
                                   cy + int(ih // 2 * math.sin(rad)))], fill=GRAY, width=1)
        for r in range(8, max(iw, ih) // 2, 8):
            draw.arc([cx - r, cy - r, cx + r, cy + r], start=0, end=360, fill=GRAY, width=1)
        # Tiny spider in web
        draw.ellipse([cx - 3, cy - 2, cx + 3, cy + 2], fill=BLACK)
    elif content == "landscape":
        # Tiny landscape painting
        draw.rectangle([inner_x, inner_y, inner_x + iw, inner_y + ih], fill=SKY_BLUE)
        draw.rectangle([inner_x, inner_y + ih // 2, inner_x + iw, inner_y + ih], fill=GRASS_GREEN)
        spray_paint(draw, inner_x + iw // 3, inner_y + ih // 3, 8, (30, 140, 30), density=80)
    elif content == "tooth":
        draw.rectangle([inner_x, inner_y, inner_x + iw, inner_y + ih], fill=(240, 240, 220))
        # Draw a cartoon tooth
        tcx, tcy = inner_x + iw // 2, inner_y + ih // 2
        draw.ellipse([tcx - 8, tcy - 10, tcx + 8, tcy + 2], fill=WHITE, outline=BLACK, width=1)
        draw.rectangle([tcx - 6, tcy, tcx - 1, tcy + 10], fill=WHITE, outline=BLACK, width=1)
        draw.rectangle([tcx + 1, tcy, tcx + 6, tcy + 10], fill=WHITE, outline=BLACK, width=1)
        draw.arc([tcx - 4, tcy - 6, tcx + 4, tcy], start=10, end=170, fill=BLACK, width=1)


def draw_framed_text(draw, x, y, text, w=110, h=75):
    """A framed sign with text, like 'Home is where the heart is'."""
    draw.rectangle([x, y, x + w, y + h], fill=WHITE, outline=BLACK, width=2)
    draw.rectangle([x + 3, y + 3, x + w - 3, y + h - 3], outline=GRAY, width=1)
    lines = text.split('\n')
    ty = y + 8
    for line in lines:
        # Center text roughly
        tx = x + 8
        draw.text((tx, ty), line, fill=BLACK, font=FONT)
        ty += 14


def draw_labeled_box(draw, x, y, w, h, label, fill_color, label_color=BLACK):
    """A box/container with a label on it."""
    draw.rectangle([x, y, x + w, y + h], fill=fill_color, outline=BLACK, width=2)
    draw.text((x + 4, y + h // 2 - 6), label, fill=label_color, font=FONT)


def draw_rubber_duck(draw, x, y, size=15):
    """A tiny rubber duck."""
    draw.ellipse([x, y, x + size, y + size], fill=YELLOW, outline=BLACK, width=1)
    # Beak
    draw.polygon([(x + size, y + size // 3), (x + size + 5, y + size // 2),
                   (x + size, y + size * 2 // 3)], fill=ORANGE)
    # Eye
    draw.ellipse([x + size // 2 + 1, y + size // 3 - 1, x + size // 2 + 3, y + size // 3 + 1], fill=BLACK)


def draw_lightning_bolts(draw, x, y, count=3):
    """Jagged yellow lightning bolts."""
    for i in range(count):
        bx = x + random.randint(-20, 20)
        by = y + random.randint(-15, 15)
        points = [(bx, by), (bx - 5, by + 8), (bx + 3, by + 8),
                  (bx - 3, by + 18), (bx + 8, by + 5), (bx + 2, by + 5)]
        draw.polygon(points, fill=YELLOW, outline=BLACK)


def draw_clock(draw, x, y, r=15):
    """A simple wall clock."""
    draw.ellipse([x - r, y - r, x + r, y + r], fill=WHITE, outline=BLACK, width=2)
    # Numbers at 12, 3, 6, 9
    draw.text((x - 3, y - r + 3), "12", fill=BLACK, font=FONT)
    draw.text((x + r - 10, y - 4), "3", fill=BLACK, font=FONT)
    draw.text((x - 3, y + r - 12), "6", fill=BLACK, font=FONT)
    draw.text((x - r + 3, y - 4), "9", fill=BLACK, font=FONT)
    # Hands
    draw.line([(x, y), (x, y - r + 6)], fill=BLACK, width=2)
    draw.line([(x, y), (x + r - 6, y)], fill=BLACK, width=1)


def draw_shelf(draw, x1, x2, y, items=None):
    """A wall shelf with optional items on it."""
    draw.line([(x1, y), (x2, y)], fill=DARK_BROWN, width=3)
    # Brackets
    for bx in [x1 + 15, x2 - 15]:
        draw.line([(bx, y), (bx, y + 12)], fill=DARK_BROWN, width=2)
        draw.line([(bx, y + 12), (bx - 10, y + 12)], fill=DARK_BROWN, width=2)


def draw_potted_plant(draw, x, y, size=1.0):
    """A small potted plant."""
    pw, ph = int(20 * size), int(25 * size)
    # Pot
    draw.polygon([(x - pw // 2, y), (x + pw // 2, y),
                   (x + pw // 3, y + ph), (x - pw // 3, y + ph)],
                  fill=(180, 80, 40), outline=DARK_BROWN, width=2)
    # Plant
    spray_paint(draw, x, y - int(15 * size), int(15 * size), GRASS_GREEN, density=int(200 * size))
    spray_paint(draw, x + int(5 * size), y - int(10 * size), int(10 * size), DARK_GREEN, density=int(100 * size))


def draw_traffic_cone(draw, x, y, size=1.0):
    """An orange traffic cone."""
    w = int(25 * size)
    h = int(45 * size)
    draw.polygon([(x - w // 2, y + h), (x + w // 2, y + h), (x, y)],
                  fill=ORANGE, outline=BLACK, width=2)
    draw.rectangle([x - w // 2 - 3, y + h, x + w // 2 + 3, y + h + 8],
                    fill=ORANGE, outline=BLACK, width=1)
    # White stripe
    draw.line([(x - w // 4, y + h // 2), (x + w // 4, y + h // 2)], fill=WHITE, width=3)


def draw_balloon(draw, x, y, color, size=20):
    """A single balloon with string."""
    draw.ellipse([x - size // 2, y - size, x + size // 2, y], fill=color, outline=BLACK, width=1)
    # Knot
    draw.polygon([(x - 2, y), (x + 2, y), (x, y + 4)], fill=color)
    # String
    draw.line([(x, y + 4), (x + random.randint(-8, 8), y + 35)], fill=BLACK, width=1)


def draw_hardhat(draw, x, y, size=1.0):
    """A construction hardhat."""
    w = int(30 * size)
    draw.arc([x - w, y - int(15 * size), x + w, y + int(10 * size)],
              start=180, end=0, fill=YELLOW, width=4)
    draw.line([(x - w - 2, y + 2), (x + w + 2, y + 2)], fill=YELLOW, width=3)


# ===========================================================================
# Environment building blocks
# ===========================================================================

def draw_sky(draw):
    """Blue sky with heavy spray-paint clouds like the originals."""
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=SKY_BLUE)
    # 4-6 big puffy spray-paint clouds
    for _ in range(random.randint(4, 6)):
        cx = random.randint(60, WIDTH - 60)
        cy = random.randint(25, 170)
        size = random.uniform(0.7, 1.3)
        spray_cloud(draw, cx, cy, size)


def draw_sun(draw, x=None, y=None, has_face=True):
    """Simple yellow sun with rays and optional smiley face."""
    x = x or random.choice([45, WIDTH - 45])
    y = y or random.randint(35, 55)
    # Rays — thick and spiky
    for angle in range(0, 360, 25):
        rad = math.radians(angle)
        length = random.randint(40, 55)
        ex = x + int(length * math.cos(rad))
        ey = y + int(length * math.sin(rad))
        draw.line([(x, y), (ex, ey)], fill=(255, 230, 0), width=3)
    # Circle
    draw.ellipse([x - 28, y - 28, x + 28, y + 28], fill=YELLOW)
    if has_face:
        # Eyes
        draw.ellipse([x - 10, y - 8, x - 5, y - 3], fill=BLACK)
        draw.ellipse([x + 5, y - 8, x + 10, y - 3], fill=BLACK)
        # Smile
        draw.arc([x - 12, y - 2, x + 12, y + 14], start=10, end=170, fill=BLACK, width=2)


def draw_ground(draw, y=None, color=None, grass=True):
    """Flat ground with dense grass texture."""
    y = y or 370
    color = color or GRASS_GREEN
    draw.rectangle([0, y, WIDTH, HEIGHT], fill=color)
    if grass:
        # Dense grass blades
        for _ in range(200):
            gx = random.randint(0, WIDTH)
            gy = random.randint(y + 5, HEIGHT)
            blade_h = random.randint(6, 18)
            draw.line([(gx, gy), (gx + random.randint(-4, 4), gy - blade_h)],
                      fill=DARK_GREEN, width=1)
        # Light grass speckle
        spray_rect(draw, 0, y, WIDTH, HEIGHT, DARK_GREEN, density=120)


def draw_water(draw, y=None):
    """Wavy ocean water from y to bottom, with heavy wave texture."""
    y = y or 300
    draw.rectangle([0, y, WIDTH, HEIGHT], fill=WATER_BLUE)
    # Dense wave lines
    for wy in range(y + 5, HEIGHT, 20):
        for wx in range(0, WIDTH, 40):
            offset = random.randint(-15, 15)
            draw.arc([wx + offset, wy, wx + 45 + offset, wy + 15],
                      start=0, end=180, fill=DEEP_WATER, width=2)
    # Light wave shimmer
    spray_rect(draw, 0, y, WIDTH, HEIGHT, (60, 150, 210), density=120)


def draw_room(draw, wall_color=None, floor_color=None, floor_y=None):
    """Simple interior room: wall + floor + baseboard."""
    wall_color = wall_color or WALL_YELLOW
    floor_color = floor_color or FLOOR_TAN
    floor_y = floor_y or 390
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=wall_color)
    draw.rectangle([0, floor_y, WIDTH, HEIGHT], fill=floor_color)
    # Baseboard line
    draw.line([(0, floor_y), (WIDTH, floor_y)], fill=DARK_BROWN, width=3)


def draw_checkered_floor(draw, y=None, size=45):
    """Black and white checkered floor."""
    y = y or 400
    colors = [BLACK, WHITE]
    cols = WIDTH // size + 2
    rows = (HEIGHT - y) // size + 2
    for row in range(rows):
        for col in range(cols):
            color = colors[(row + col) % 2]
            x1 = col * size
            y1 = y + row * size
            draw.rectangle([x1, y1, x1 + size, y1 + size], fill=color)


def draw_tile_floor(draw, y=None, color1=None, color2=None, size=50):
    """Tiled floor with grout lines."""
    y = y or 400
    color1 = color1 or LIGHT_GRAY
    color2 = color2 or (195, 195, 195)
    draw.rectangle([0, y, WIDTH, HEIGHT], fill=color1)
    for ty in range(y, HEIGHT, size):
        draw.line([(0, ty), (WIDTH, ty)], fill=color2, width=1)
    for tx in range(0, WIDTH, size):
        draw.line([(tx, y), (tx, HEIGHT)], fill=color2, width=1)


# ===========================================================================
# Scene renderer
# ===========================================================================

def render_scene(post):
    """Render an illustration for a post."""
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    setting = post.get("setting", "").lower()
    mechanism = post.get("mechanism", "").lower()
    hidden_touch = post.get("hidden_touch", "")
    scene_desc = post.get("scene_description", "").lower()

    # Route to specific scene renderer
    if any(k in setting for k in ["laundry", "laundromat"]) or "tumble" in mechanism or "dryer" in mechanism:
        _scene_laundromat(draw, post)
    elif any(k in setting for k in ["dentist", "dental"]) or "nitrous" in mechanism:
        _scene_dentist(draw, post)
    elif "post office" in setting or "mail" in mechanism:
        _scene_post_office(draw, post)
    elif "freezer" in setting or "froze" in mechanism or "freeze" in mechanism:
        _scene_freezer(draw, post)
    elif any(k in setting for k in ["circus", "carnival"]) or "cannon" in mechanism:
        _scene_circus(draw, post)
    elif "construction" in setting or "cement" in mechanism:
        _scene_construction(draw, post)
    elif "volcano" in setting:
        _scene_volcano(draw, post)
    elif any(k in setting for k in ["kitchen", "oven"]) or "bake" in mechanism:
        _scene_kitchen(draw, post)
    elif "bathroom" in setting or "bath" in setting or "tub" in mechanism:
        _scene_bathroom(draw, post)
    elif any(k in setting for k in ["island", "beach"]):
        _scene_island(draw, post)
    elif any(k in setting for k in ["garden", "yard", "park"]):
        _scene_garden(draw, post)
    elif "sky" in setting or "space" in setting or "balloon" in mechanism or "float" in mechanism:
        _scene_sky(draw, post)
    elif any(k in setting for k in ["elevator", "shaft"]):
        _scene_elevator(draw, post)
    elif any(k in setting for k in ["gym", "fitness"]):
        _scene_gym(draw, post)
    elif "golf course" in setting:
        _scene_golf_course(draw, post)
    elif "movie theater" in setting:
        _scene_movie_theater(draw, post)
    elif "hair salon" in setting:
        _scene_hair_salon(draw, post)
    elif "ski resort" in setting:
        _scene_ski_resort(draw, post)
    elif "aquarium" in setting:
        _scene_aquarium(draw, post)
    elif "backyard barbecue" in setting:
        _scene_backyard_barbecue(draw, post)
    elif "car wash" in setting:
        _scene_car_wash(draw, post)
    elif "library" in setting:
        _scene_library(draw, post)
    elif any(k in setting for k in ["rocket", "launchpad", "launch pad"]):
        _scene_rocket_launchpad(draw, post)
    elif "bowling" in setting:
        _scene_bowling_alley(draw, post)
    else:
        # Smart fallback: indoor if it feels indoor, outdoor otherwise
        indoor_hints = ["office", "room", "store", "shop", "lab", "hospital", "basement",
                        "attic", "library", "museum", "restaurant", "bar", "cafe"]
        if any(k in setting for k in indoor_hints):
            _scene_generic_indoor(draw, post)
        else:
            _scene_generic_outdoor(draw, post)

    # No global speckle — originals use flat clean colors, spray only for objects

    return img


# ===========================================================================
# Specific scene renderers — each one is dense with detail
# ===========================================================================

def _scene_laundromat(draw, post):
    import math

    # --- WALL: flat warm gray ---
    draw.rectangle([0, 0, WIDTH, 415], fill=(220, 220, 218))

    # --- FLUORESCENT LIGHT BAR at top ---
    draw.rectangle([40, 5, 600, 20], fill=(255, 255, 210), outline=(180, 180, 140), width=2)
    for lx in range(70, 590, 35):
        draw.line([(lx, 8), (lx, 17)], fill=(230, 230, 180), width=1)

    # --- FLOOR: white linoleum tiles ---
    draw.rectangle([0, 415, WIDTH, HEIGHT], fill=(248, 248, 245))
    for x in range(0, WIDTH + 1, 80):
        draw.line([(x, 415), (x, HEIGHT)], fill=(210, 210, 205), width=1)
    for y in range(415, HEIGHT + 1, 40):
        draw.line([(0, y), (WIDTH, y)], fill=(210, 210, 205), width=1)
    draw.line([(0, 415), (WIDTH, 415)], fill=(160, 160, 155), width=3)

    # === DRYER — large orange, left side ===
    dx, dy = 55, 45
    dw, dh = 350, 360

    # Dryer body
    draw.rectangle([dx, dy, dx + dw, dy + dh], fill=BRIGHT_ORANGE, outline=BLACK, width=4)

    # Control panel strip
    draw.rectangle([dx + 5, dy + 5, dx + dw - 5, dy + 70], fill=LIGHT_GRAY, outline=DARK_GRAY, width=2)

    # Brand name
    draw.text((dx + 80, dy + 12), "SPINNMASTER3000", fill=DARK_GRAY, font=FONT)

    # Dial — left side of panel
    dcx, dcy = dx + 55, dy + 47
    draw.ellipse([dcx - 24, dcy - 24, dcx + 24, dcy + 24], fill=WHITE, outline=BLACK, width=2)
    for tick_a in range(-150, 31, 30):
        ta = math.radians(tick_a)
        tx1 = dcx + int(15 * math.cos(ta))
        ty1 = dcy + int(15 * math.sin(ta))
        tx2 = dcx + int(21 * math.cos(ta))
        ty2 = dcy + int(21 * math.sin(ta))
        draw.line([(tx1, ty1), (tx2, ty2)], fill=DARK_GRAY, width=1)
    # Needle pointing to HIGH (far left = hottest)
    na = math.radians(-148)
    nx = dcx + int(17 * math.cos(na))
    ny = dcy + int(17 * math.sin(na))
    draw.line([(dcx, dcy), (nx, ny)], fill=RED, width=3)
    draw.ellipse([dcx - 3, dcy - 3, dcx + 3, dcy + 3], fill=DARK_GRAY)
    # HIGH label with underline
    draw.text((dcx + 30, dcy - 22), "HIGH", fill=RED, font=FONT)
    draw.line([(dcx + 28, dcy - 10), (dcx + 62, dcy - 10)], fill=RED, width=2)

    # HOT button — right of panel
    draw.rectangle([dx + dw - 88, dy + 16, dx + dw - 14, dy + 58], fill=RED, outline=BLACK, width=2)
    draw.text((dx + dw - 76, dy + 30), "HOT", fill=WHITE, font=FONT)

    # === PORTHOLE ===
    pcx = dx + dw // 2 + 10
    pcy = dy + 70 + (dh - 70) // 2 + 5
    pr = 118

    # Outer rubber gasket ring
    draw.ellipse([pcx - pr - 24, pcy - pr - 24, pcx + pr + 24, pcy + pr + 24],
                 fill=DARK_GRAY, outline=BLACK, width=5)
    # Inner glass — bright sky blue for HIGH contrast with gray spider
    drum_color = (145, 200, 245)
    draw.ellipse([pcx - pr, pcy - pr, pcx + pr, pcy + pr],
                 fill=drum_color, outline=BLACK, width=2)

    # Spin motion arcs inside drum
    draw.arc([pcx - 90, pcy - 90, pcx + 90, pcy + 90], start=180, end=290, fill=(100, 150, 200), width=6)
    draw.arc([pcx - 65, pcy - 65, pcx + 65, pcy + 65], start=10, end=120, fill=(100, 150, 200), width=5)
    draw.arc([pcx - 42, pcy - 42, pcx + 42, pcy + 42], start=120, end=210, fill=(100, 150, 200), width=4)

    # --- TUMBLING CLOTHES — pushed to drum edges, clearly sock/shirt shaped ---

    # BLUE T-SHIRT — upper right quadrant
    tx, ty = pcx + 18, pcy - 108
    # Shirt body
    draw.rectangle([tx, ty + 22, tx + 48, ty + 72], fill=BLUE, outline=BLACK, width=2)
    # Left sleeve
    draw.polygon([(tx, ty + 22), (tx - 22, ty + 8), (tx - 18, ty + 30), (tx, ty + 40)],
                 fill=BLUE, outline=BLACK, width=2)
    # Right sleeve
    draw.polygon([(tx + 48, ty + 22), (tx + 70, ty + 8), (tx + 66, ty + 30), (tx + 48, ty + 40)],
                 fill=BLUE, outline=BLACK, width=2)
    # Collar V
    draw.polygon([(tx + 10, ty + 22), (tx + 24, ty + 38), (tx + 38, ty + 22)],
                 fill=(100, 140, 210), outline=BLACK, width=1)

    # PINK SOCK — upper left, drawn as clear L-shape sock
    sock1x, sock1y = pcx - 112, pcy - 88
    draw.rectangle([sock1x, sock1y, sock1x + 22, sock1y + 52], fill=(220, 100, 150), outline=BLACK, width=2)
    draw.rectangle([sock1x, sock1y + 38, sock1x + 48, sock1y + 54], fill=(220, 100, 150), outline=BLACK, width=2)
    draw.ellipse([sock1x + 32, sock1y + 34, sock1x + 54, sock1y + 56], fill=(220, 100, 150), outline=BLACK, width=2)

    # RED SOCK — lower right, L-shape
    sock2x, sock2y = pcx + 60, pcy + 36
    draw.rectangle([sock2x, sock2y, sock2x + 22, sock2y + 52], fill=RED, outline=BLACK, width=2)
    draw.rectangle([sock2x, sock2y + 38, sock2x + 46, sock2y + 54], fill=RED, outline=BLACK, width=2)
    draw.ellipse([sock2x + 30, sock2y + 34, sock2x + 52, sock2y + 56], fill=RED, outline=BLACK, width=2)

    # YELLOW SMILEY SOCK — lower left (HIDDEN DETAIL: smiley face on toe)
    ssx, ssy = pcx - 115, pcy + 32
    draw.rectangle([ssx, ssy, ssx + 22, ssy + 50], fill=YELLOW, outline=BLACK, width=2)
    draw.rectangle([ssx, ssy + 36, ssx + 44, ssy + 52], fill=YELLOW, outline=BLACK, width=2)
    # Toe bump
    draw.ellipse([ssx + 28, ssy + 32, ssx + 52, ssy + 56], fill=YELLOW, outline=BLACK, width=2)
    # Smiley face on toe — clear and charming
    draw.ellipse([ssx + 32, ssy + 36, ssx + 38, ssy + 42], fill=BLACK)
    draw.ellipse([ssx + 42, ssy + 36, ssx + 48, ssy + 42], fill=BLACK)
    draw.arc([ssx + 30, ssy + 42, ssx + 50, ssy + 54], start=10, end=170, fill=BLACK, width=2)

    # === SPIDEY — center of drum, SMALL, tumbling ragdoll pose ===
    # Small size = pathetic and overwhelmed by the big drum
    spx, spy = pcx - 5, pcy + 5

    # Tilted body — 35 degree tilt for tumbling feel
    tilt = math.radians(35)
    sz_w = 18
    sz_h = 12
    body_pts = []
    for i in range(36):
        a = math.radians(i * 10)
        px_r = math.cos(a) * sz_w
        py_r = math.sin(a) * sz_h
        rx = px_r * math.cos(tilt) - py_r * math.sin(tilt) + spx
        ry = px_r * math.sin(tilt) + py_r * math.cos(tilt) + spy
        body_pts.append((rx, ry))
    draw.polygon(body_pts, fill=(185, 185, 185), outline=BLACK, width=2)

    # 8 legs — splayed outward chaotically (centrifugal tumble)
    leg_pairs = [
        (-14, -10, -55, -48),
        (-16,  -2, -58,  -2),
        (-14,   8, -52,  38),
        ( -4,  14,  -8,  54),
        ( 14, -10,  55, -48),
        ( 16,  -2,  58,  -2),
        ( 14,   8,  54,  38),
        (  4,  14,  10,  54),
    ]
    for lx1, ly1, lx2, ly2 in leg_pairs:
        draw.line([(spx + lx1, spy + ly1), (spx + lx2, spy + ly2)], fill=BLACK, width=2)

    # Eyes — large relative to body, alarmed/dizzy
    # Rotated with body tilt
    ex_off = int(8 * math.cos(tilt))
    ey_off = int(8 * math.sin(tilt))
    # Left eye
    draw.ellipse([spx - ex_off - 8, spy - ey_off - 10, spx - ex_off + 2, spy - ey_off], fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([spx - ex_off - 6, spy - ey_off - 8, spx - ex_off, spy - ey_off - 2], fill=BLACK)
    # Right eye
    draw.ellipse([spx + ex_off - 2, spy + ey_off - 10, spx + ex_off + 8, spy + ey_off], fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([spx + ex_off, spy + ey_off - 8, spx + ex_off + 6, spy + ey_off - 2], fill=BLACK)

    # Alarmed open mouth
    draw.ellipse([spx - 6, spy + 4, spx + 6, spy + 14], fill=BLACK, outline=BLACK, width=1)
    draw.ellipse([spx - 3, spy + 6, spx + 3, spy + 12], fill=DARK_GRAY)

    # One leg pressed against porthole glass (panic/stuck detail)
    draw.line([(spx + 4, spy + 14), (spx + 28, spy + 72)], fill=BLACK, width=2)
    draw.line([(spx + 28, spy + 72), (spx + 68, spy + 68)], fill=BLACK, width=2)

    # Porthole glass sheen
    draw.arc([pcx - pr + 8, pcy - pr + 8, pcx - pr + 50, pcy - pr + 50],
             start=210, end=290, fill=(220, 240, 255), width=4)

    # === "NO SPIDERS" SIGN — upper right wall ===
    sx, sy = 448, 30
    draw.rectangle([sx, sy, sx + 172, sy + 96], fill=WHITE, outline=BLACK, width=3)
    # Tack holes
    draw.ellipse([sx + 4, sy + 4, sx + 14, sy + 14], fill=DARK_GRAY, outline=BLACK, width=1)
    draw.ellipse([sx + 158, sy + 4, sx + 168, sy + 14], fill=DARK_GRAY, outline=BLACK, width=1)
    draw.text((sx + 66, sy + 12), "NO", fill=BLACK, font=FONT)
    draw.text((sx + 30, sy + 38), "SPIDERS", fill=BLACK, font=FONT)
    # Big red X
    draw.line([(sx + 14, sy + 14), (sx + 158, sy + 82)], fill=RED, width=8)
    draw.line([(sx + 158, sy + 14), (sx + 14, sy + 82)], fill=RED, width=8)
    # Redraw border on top of X
    draw.rectangle([sx, sy, sx + 172, sy + 96], outline=BLACK, width=3)

    # === RIGHT SIDE: laundry supplies ===

    # SOAP bottle
    sbx, sby = 456, 342
    draw.rectangle([sbx, sby, sbx + 42, sby + 70], fill=BLUE, outline=BLACK, width=2)
    draw.rectangle([sbx + 13, sby - 18, sbx + 29, sby + 2], fill=BLUE, outline=BLACK, width=2)
    draw.ellipse([sbx + 15, sby - 26, sbx + 27, sby - 14], fill=LIGHT_GRAY, outline=BLACK, width=1)
    draw.text((sbx + 4, sby + 24), "SOAP", fill=WHITE, font=FONT)

    # LAUNDRY BASKET with REDS
    bkx, bky = 508, 318
    draw.polygon([
        (bkx, bky), (bkx + 80, bky),
        (bkx + 72, bky + 96), (bkx + 8, bky + 96)
    ], fill=LIGHT_BROWN, outline=BLACK, width=2)
    for ly in range(bky + 14, bky + 96, 16):
        draw.line([(bkx + 10, ly), (bkx + 70, ly)], fill=BROWN, width=1)
    # Red clothes peeking out top
    draw.ellipse([bkx + 2, bky - 28, bkx + 44, bky + 6], fill=(215, 48, 48), outline=BLACK, width=2)
    draw.ellipse([bkx + 36, bky - 32, bkx + 78, bky + 4], fill=RED, outline=BLACK, width=2)
    draw.text((bkx + 14, bky - 20), "REDS", fill=WHITE, font=FONT)

    # MOP BUCKET — far right corner
    mbx, mby = 595, 350
    draw.polygon([
        (mbx, mby), (mbx + 38, mby),
        (mbx + 30, mby + 62), (mbx + 8, mby + 62)
    ], fill=YELLOW, outline=BLACK, width=2)
    # Water in bucket
    draw.ellipse([mbx + 4, mby + 4, mbx + 34, mby + 16], fill=(160, 210, 235), outline=None)
    # Handle
    draw.arc([mbx + 6, mby - 12, mbx + 32, mby + 12], start=200, end=340, fill=DARK_GRAY, width=2)
    # Mop handle
    draw.line([(mbx + 19, mby - 62), (mbx + 19, mby + 4)], fill=BROWN, width=3)
    # Mop strings
    for fi in range(-12, 16, 5):
        draw.line([(mbx + 19, mby - 62), (mbx + 19 + fi, mby - 40)], fill=LIGHT_GRAY, width=2)


def _scene_dentist(draw, post):
    # Pale yellow walls, white tile floor
    draw_room(draw, wall_color=(240, 238, 215), floor_color=WHITE, floor_y=400)
    draw_tile_floor(draw, y=400, color1=WHITE, color2=(220, 220, 220), size=36)
    # Walls are flat color — no speckle (matches original MS Paint style)

    # === FRAMED TOOTH POSTER - top right, clear and charming ===
    px, py, pw, ph = 490, 30, 120, 105
    draw.rectangle([px, py, px + pw, py + ph], fill=WHITE, outline=BLACK, width=4)
    draw.rectangle([px + 6, py + 6, px + pw - 6, py + ph - 6], fill=(248, 248, 235), outline=LIGHT_GRAY, width=1)
    tcx = px + pw // 2
    tcy = py + 38
    # Tooth shape - simple and readable
    draw.rounded_rectangle([tcx - 20, tcy - 22, tcx + 20, tcy + 4], radius=10, fill=WHITE, outline=BLACK, width=2)
    draw.rounded_rectangle([tcx - 16, tcy + 2, tcx - 5, tcy + 20], radius=4, fill=WHITE, outline=BLACK, width=2)
    draw.rounded_rectangle([tcx + 5, tcy + 2, tcx + 16, tcy + 20], radius=4, fill=WHITE, outline=BLACK, width=2)
    # Tooth face
    draw.ellipse([tcx - 9, tcy - 14, tcx - 5, tcy - 10], fill=BLACK)
    draw.ellipse([tcx + 5, tcy - 14, tcx + 9, tcy - 10], fill=BLACK)
    draw.arc([tcx - 7, tcy - 8, tcx + 7, tcy - 2], start=0, end=180, fill=BLACK, width=2)
    draw.text((tcx - 14, py + ph - 18), "SMILE!", fill=(0, 160, 0), font=FONT)

    # === RELAX sign - top left, big and legible ===
    draw.rectangle([20, 44, 135, 115], fill=WHITE, outline=BLACK, width=3)
    draw.rectangle([26, 50, 129, 109], fill=(252, 252, 242), outline=LIGHT_GRAY, width=1)
    draw.text((34, 58), "RELAX!", fill=BLACK, font=FONT)
    draw.text((34, 76), ":  )", fill=(0, 160, 0), font=FONT)

    # === OVERHEAD DENTAL LAMP - clearly anchored ===
    draw.line([(310, 0), (310, 50)], fill=DARK_GRAY, width=6)
    draw.line([(310, 50), (268, 82)], fill=DARK_GRAY, width=6)
    # Lamp housing - clearly a lamp shape
    draw.ellipse([218, 78, 298, 106], fill=(190, 190, 190), outline=BLACK, width=3)
    draw.ellipse([228, 84, 288, 100], fill=YELLOW, outline=BLACK, width=2)
    # Light beam
    for i in range(-2, 3):
        draw.line([(258 + i * 5, 104), (230 + i * 8, 148)], fill=(255, 255, 180, 120), width=1)

    # =============================================
    # === DENTIST CHAIR - clear, iconic shape ===
    # =============================================
    # Chair centered around x=240
    # Seat horizontal bar, backrest vertical on left
    chair_cx = 240

    back_left   = 130
    back_right  = 190
    back_top    = 165
    back_bottom = 355

    seat_left   = back_right
    seat_right  = chair_cx + 120
    seat_top    = 300
    seat_bottom = 350

    # Pedestal
    draw.rectangle([chair_cx - 14, seat_bottom, chair_cx + 14, seat_bottom + 50],
                   fill=DARK_GRAY, outline=BLACK, width=2)
    draw.ellipse([chair_cx - 42, seat_bottom + 44, chair_cx + 42, seat_bottom + 58],
                 fill=DARK_GRAY, outline=BLACK, width=2)

    # Seat
    draw.rectangle([seat_left, seat_top, seat_right, seat_bottom],
                   fill=TEAL, outline=BLACK, width=3)

    # Backrest
    draw.rectangle([back_left, back_top, back_right, back_bottom],
                   fill=TEAL, outline=BLACK, width=3)

    # Headrest
    draw.rounded_rectangle([back_left - 10, back_top - 28, back_right + 10, back_top + 10],
                            radius=12, fill=TEAL, outline=BLACK, width=3)

    # Armrests
    draw.rectangle([back_right, seat_top - 18, back_right + 30, seat_top - 6],
                   fill=(0, 135, 135), outline=BLACK, width=2)
    draw.rectangle([seat_right - 32, seat_top - 18, seat_right, seat_top - 6],
                   fill=(0, 135, 135), outline=BLACK, width=2)

    # Footrest
    draw.rectangle([seat_right - 2, seat_top + 10, seat_right + 42, seat_top + 32],
                   fill=TEAL, outline=BLACK, width=2)

    # =============================================
    # === SPIDEY - clearly IN chair, head on headrest ===
    # Placed against WHITE background for contrast
    # =============================================
    spider_cx = (back_left + back_right) // 2  # ~160
    spider_cy = back_top - 14  # head on headrest ~151

    # White circle behind spider for contrast against teal headrest
    draw.ellipse([spider_cx - 28, spider_cy - 28, spider_cx + 28, spider_cy + 28],
                 fill=WHITE, outline=None)

    # Draw Spidey - dead expression, reclining
    draw_spidey(draw, spider_cx, spider_cy, size=20, expression="dead")

    # Limp legs - drooping naturally downward (gravity)
    lc = BLACK
    # Left side legs drooping down-left
    draw.line([(spider_cx - 15, spider_cy + 6),  (spider_cx - 36, spider_cy + 28)], fill=lc, width=2)
    draw.line([(spider_cx - 15, spider_cy + 0),  (spider_cx - 38, spider_cy + 14)], fill=lc, width=2)
    draw.line([(spider_cx - 14, spider_cy - 7),  (spider_cx - 36, spider_cy - 4)], fill=lc, width=2)
    draw.line([(spider_cx - 12, spider_cy - 14), (spider_cx - 30, spider_cy - 20)], fill=lc, width=2)
    # Right side legs sprawling onto seat
    draw.line([(spider_cx + 15, spider_cy + 6),  (spider_cx + 42, spider_cy + 30)], fill=lc, width=2)
    draw.line([(spider_cx + 15, spider_cy + 0),  (spider_cx + 44, spider_cy + 12)], fill=lc, width=2)
    draw.line([(spider_cx + 14, spider_cy - 7),  (spider_cx + 42, spider_cy - 2)], fill=lc, width=2)
    draw.line([(spider_cx + 12, spider_cy - 14), (spider_cx + 36, spider_cy - 22)], fill=lc, width=2)

    # =============================================
    # === GAS MASK - large, clearly on face ===
    # =============================================
    mx, my = spider_cx, spider_cy
    mask_fill = (165, 175, 175)
    mask_dark = (100, 112, 112)

    # Main mask body - big gray oval over lower face
    draw.ellipse([mx - 24, my - 10, mx + 24, my + 22],
                 fill=mask_fill, outline=BLACK, width=3)

    # Two green goggle lenses
    draw.ellipse([mx - 20, my - 8,  mx - 7,  my + 2],  fill=(20, 80, 20), outline=BLACK, width=2)
    draw.ellipse([mx + 7,  my - 8,  mx + 20, my + 2],  fill=(20, 80, 20), outline=BLACK, width=2)
    # Lens reflections
    draw.ellipse([mx - 18, my - 7, mx - 15, my - 4], fill=(60, 180, 60))
    draw.ellipse([mx + 9,  my - 7, mx + 12, my - 4], fill=(60, 180, 60))

    # Hose fitting at bottom of mask
    draw.rounded_rectangle([mx - 10, my + 18, mx + 10, my + 34],
                            radius=4, fill=mask_dark, outline=BLACK, width=2)

    # Strap across head
    draw.line([(mx - 24, my + 4), (mx - 34, my + 4)], fill=DARK_GRAY, width=3)
    draw.line([(mx + 24, my + 4), (mx + 34, my + 4)], fill=DARK_GRAY, width=3)

    # =============================================
    # === PAPER BIB on spider's torso ===
    # Placed on seat, clearly labeled PATIENT
    # =============================================
    bib_cx = spider_cx + 4
    bib_top = spider_cy + 18
    draw.polygon([
        (bib_cx - 26, bib_top),
        (bib_cx + 26, bib_top),
        (bib_cx + 20, bib_top + 50),
        (bib_cx - 20, bib_top + 50),
    ], fill=WHITE, outline=(80, 140, 210), width=2)
    # Clip neckline
    draw.line([(bib_cx - 22, bib_top), (bib_cx - 28, bib_top - 8)], fill=(80, 140, 210), width=2)
    draw.line([(bib_cx + 22, bib_top), (bib_cx + 28, bib_top - 8)], fill=(80, 140, 210), width=2)
    draw.text((bib_cx - 20, bib_top + 16), "PATIENT", fill=(60, 110, 200), font=FONT)

    # =============================================
    # === N2O TANK - right side, large and clear ===
    # =============================================
    tx, ty = 440, 140
    tw, th = 62, 195

    draw.rounded_rectangle([tx - tw // 2, ty, tx + tw // 2, ty + th],
                            radius=22, fill=(205, 210, 215), outline=BLACK, width=3)
    # Tank is flat fill — no spray (clean MS Paint style)

    # Label
    draw.rectangle([tx - 25, ty + 48, tx + 25, ty + 112], fill=WHITE, outline=BLACK, width=2)
    draw.text((tx - 14, ty + 52), "N2O",     fill=BLACK, font=FONT)
    draw.text((tx - 20, ty + 68), "NITROUS", fill=RED,   font=FONT)
    draw.text((tx - 15, ty + 84), "OXIDE",   fill=RED,   font=FONT)

    # Valve on top - RED dome, horizontal bar = wide open
    draw.ellipse([tx - 16, ty - 24, tx + 16, ty + 4], fill=RED, outline=BLACK, width=3)
    draw.line([(tx - 22, ty - 10), (tx + 22, ty - 10)], fill=DARK_GRAY, width=8)
    draw.text((tx + 22, ty - 30), "MAX!", fill=RED, font=FONT)
    draw.line([(tx + 21, ty - 18), (tx + 12, ty - 12)], fill=RED, width=2)

    # Pressure gauge - needle in red zone
    gx, gy = tx, ty + 148
    draw.ellipse([gx - 18, gy - 18, gx + 18, gy + 18], fill=WHITE, outline=BLACK, width=2)
    draw.arc([gx - 13, gy - 13, gx + 13, gy + 13], start=200, end=360, fill=RED, width=3)
    draw.arc([gx - 13, gy - 13, gx + 13, gy + 13], start=170, end=200, fill=(0, 180, 0), width=3)
    draw.line([(gx, gy), (gx + 12, gy - 2)], fill=RED, width=2)
    draw.ellipse([gx - 3, gy - 3, gx + 3, gy + 3], fill=BLACK)

    # Hose connector on tank left side
    hose_ox = tx - tw // 2
    hose_oy = ty + 115
    draw.rectangle([hose_ox - 18, hose_oy - 8, hose_ox, hose_oy + 8],
                   fill=DARK_GRAY, outline=BLACK, width=2)

    # =============================================
    # === HOSE - simple thick curve, mask to tank ===
    # =============================================
    hose_color = (40, 168, 60)
    hx0, hy0 = mx,            my + 34    # mask filter bottom
    hx3, hy3 = hose_ox - 9,   hose_oy   # tank connector

    # Two control points for a readable arc
    hx1, hy1 = hx0 + 30,  hy0 + 80
    hx2, hy2 = hx3 - 40,  hy3 - 30

    pts = [(hx0, hy0), (hx1, hy1), (hx2, hy2), (hx3, hy3)]

    draw.line(pts, fill=BLACK,      width=14)
    draw.line(pts, fill=hose_color, width=10)

    # Corrugation rings
    for i in range(1, 11):
        t = i / 11.0
        bx = int((1-t)**3 * hx0 + 3*(1-t)**2*t*hx1 + 3*(1-t)*t**2*hx2 + t**3*hx3)
        by = int((1-t)**3 * hy0 + 3*(1-t)**2*t*hy1 + 3*(1-t)*t**2*hy2 + t**3*hy3)
        draw.ellipse([bx - 6, by - 6, bx + 6, by + 6], outline=(20, 110, 40), width=2)

    # =============================================
    # === GAS PUFFS - laughing gas clouds near spider ===
    # =============================================
    spray_cloud(draw, mx - 8,  my - 48, size=22)
    spray_cloud(draw, mx + 18, my - 55, size=15)
    spray_cloud(draw, mx,      my - 66, size=13)

    # Stars drifting upward
    for sx, sy in [(mx - 22, my - 60), (mx + 22, my - 64), (mx + 4, my - 76)]:
        draw.text((sx, sy), "★", fill=YELLOW, font=FONT)

    # Small gas wisps from open valve (not a fog bank)
    spray_cloud(draw, tx,      ty - 34, size=0.6)
    spray_cloud(draw, tx + 12, ty - 44, size=0.4)

    # =============================================
    # === DENTAL INSTRUMENT TRAY ===
    # =============================================
    tray_x = seat_right - 10
    tray_y = seat_top + 8
    draw.line([(tray_x, tray_y), (tray_x + 28, tray_y - 12)], fill=DARK_GRAY, width=3)
    draw.rounded_rectangle([tray_x + 20, tray_y - 24, tray_x + 90, tray_y - 8],
                            radius=4, fill=LIGHT_GRAY, outline=BLACK, width=2)
    for xi in [tray_x + 30, tray_x + 44, tray_x + 58, tray_x + 72]:
        draw.line([(xi, tray_y - 22), (xi, tray_y - 9)], fill=DARK_GRAY, width=2)

    # === POTTED PLANT - charming corner detail ===
    draw_potted_plant(draw, 582, 360, size=0.7)


def _scene_post_office(draw, post):
    import math

    # ── WALL AND FLOOR ─────────────────────────────────────────────────────
    draw.rectangle([0, 0, 640, 480], fill=(240, 225, 200))
    draw.rectangle([0, 390, 640, 480], fill=FLOOR_TAN)

    # ── COUNTER ────────────────────────────────────────────────────────────
    draw.rectangle([0, 300, 640, 330], fill=BROWN, outline=DARK_BROWN, width=3)
    draw.rectangle([0, 330, 640, 390], fill=DARK_BROWN, outline=BLACK, width=2)

    # ── THE BOX (center, hero of the scene) ────────────────────────────────
    bx, by = 210, 100
    bw, bh = 210, 200

    # Box body
    draw.rectangle([bx, by, bx + bw, by + bh], fill=(210, 168, 98), outline=BLACK, width=3)

    # Top flap area — darker to read as sealed
    flap_h = 55
    draw.rectangle([bx, by, bx + bw, by + flap_h], fill=(185, 142, 68), outline=BLACK, width=2)

    # Flap center seam
    draw.line([(bx + bw // 2, by), (bx + bw // 2, by + flap_h)], fill=BLACK, width=2)

    # Packing tape — bright yellow, unmistakably tape
    tape_y = by + flap_h - 10
    draw.rectangle([bx, tape_y, bx + bw, tape_y + 16],
                   fill=(255, 240, 80), outline=(160, 140, 30), width=2)
    draw.text((bx + bw // 2 - 20, tape_y + 3), "TAPE", fill=(130, 110, 20), font=FONT)

    # ── SPIDEY VISIBLE THROUGH A GAP IN THE FLAP ──────────────────────────
    # Large dark opening — clearly the inside of the box
    gap_cx = bx + bw // 2
    gap_cy = by + flap_h + 38
    gap_w = 70
    gap_h = 54

    # Dark box interior
    draw.rectangle([gap_cx - gap_w // 2, gap_cy - gap_h // 2,
                    gap_cx + gap_w // 2, gap_cy + gap_h // 2],
                   fill=(25, 12, 2), outline=BLACK, width=2)

    # Spidey — drawn with draw_spidey for brand consistency
    # Use a light background patch behind him for contrast
    draw.ellipse([gap_cx - 20, gap_cy - 17, gap_cx + 20, gap_cy + 17],
                 fill=(80, 60, 40))  # slightly lighter dark for contrast

    # Draw spidey manually large and visible — sad expression
    fc = gap_cx
    fy = gap_cy

    # Gray body oval
    draw.ellipse([fc - 18, fy - 14, fc + 18, fy + 14],
                 fill=(200, 200, 200), outline=BLACK, width=2)

    # Big panicked eyes — white sclera with black pupils
    draw.ellipse([fc - 13, fy - 10, fc - 3, fy + 1], fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([fc + 3, fy - 10, fc + 13, fy + 1], fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([fc - 11, fy - 8, fc - 5, fy - 2], fill=BLACK)
    draw.ellipse([fc + 5, fy - 8, fc + 11, fy - 2], fill=BLACK)

    # Worried open mouth
    draw.arc([fc - 8, fy + 2, fc + 8, fy + 12], start=200, end=340, fill=BLACK, width=2)

    # Tiny sweat drop for distress
    draw.polygon([(fc + 16, fy - 12), (fc + 14, fy - 6), (fc + 18, fy - 6)],
                 fill=(100, 180, 255))

    # Legs poking from sides of gap
    for dx, dy, ex, ey in [
        (gap_cx - gap_w // 2, gap_cy - 6, gap_cx - gap_w // 2 - 14, gap_cy - 16),
        (gap_cx - gap_w // 2, gap_cy + 4, gap_cx - gap_w // 2 - 14, gap_cy + 14),
        (gap_cx + gap_w // 2, gap_cy - 6, gap_cx + gap_w // 2 + 14, gap_cy - 16),
        (gap_cx + gap_w // 2, gap_cy + 4, gap_cx + gap_w // 2 + 14, gap_cy + 14),
    ]:
        draw.line([(dx, dy), (ex, ey)], fill=BLACK, width=2)

    # Small "NO AIR" label — charming cruel detail
    draw.rectangle([bx + bw - 72, by + 62, bx + bw - 4, by + 80],
                   fill=WHITE, outline=RED, width=1)
    draw.text((bx + bw - 68, by + 65), "NO AIR HOLES", fill=RED, font=FONT)

    # ── SHIPPING LABEL on box front ────────────────────────────────────────
    lx, ly = bx + 12, by + 115
    draw.rectangle([lx, ly, lx + 160, ly + 72],
                   fill=(255, 252, 235), outline=BLACK, width=2)
    draw.text((lx + 4, ly + 4), "TO:", fill=BLACK, font=FONT)
    draw.text((lx + 4, ly + 18), "NOWHERE, NV", fill=BLACK, font=FONT)
    # FRAGILE stamp
    draw.rectangle([lx + 4, ly + 38, lx + 110, ly + 58],
                   fill=RED, outline=DARK_BROWN, width=2)
    draw.text((lx + 20, ly + 41), "FRAGILE", fill=WHITE, font=FONT)

    # ── POSTAL WORKER (right, cheerfully oblivious) ────────────────────────
    pw_x = 530
    pw_y = 185

    # Waving arm
    draw.line([(pw_x + 14, pw_y + 40), (pw_x + 46, pw_y + 10)], fill=SKIN, width=5)
    draw.ellipse([pw_x + 40, pw_y + 4, pw_x + 58, pw_y + 22],
                 fill=SKIN, outline=BLACK, width=2)

    # Body — blue uniform
    draw.rectangle([pw_x - 22, pw_y + 32, pw_x + 22, pw_y + 88],
                   fill=(55, 85, 185), outline=BLACK, width=2)

    # Left arm down
    draw.line([(pw_x - 18, pw_y + 42), (pw_x - 32, pw_y + 68)], fill=SKIN, width=4)

    # Head
    draw.ellipse([pw_x - 18, pw_y, pw_x + 18, pw_y + 34],
                 fill=SKIN, outline=BLACK, width=2)

    # Postal hat
    draw.rectangle([pw_x - 23, pw_y - 4, pw_x + 23, pw_y + 6],
                   fill=(35, 60, 150), outline=BLACK, width=1)
    draw.rectangle([pw_x - 16, pw_y - 24, pw_x + 16, pw_y + 1],
                   fill=(35, 60, 150), outline=BLACK, width=2)
    draw.rectangle([pw_x - 7, pw_y - 18, pw_x + 7, pw_y - 6],
                   fill=YELLOW, outline=BLACK, width=1)

    # Happy face
    draw.ellipse([pw_x - 9, pw_y + 8, pw_x - 3, pw_y + 15], fill=BLACK)
    draw.ellipse([pw_x + 3, pw_y + 8, pw_x + 9, pw_y + 15], fill=BLACK)
    draw.arc([pw_x - 10, pw_y + 16, pw_x + 10, pw_y + 30],
             start=10, end=170, fill=BLACK, width=2)

    # Cheek blushes — extra cheerful
    draw.ellipse([pw_x - 16, pw_y + 20, pw_x - 8, pw_y + 28], fill=(255, 180, 160))
    draw.ellipse([pw_x + 8, pw_y + 20, pw_x + 16, pw_y + 28], fill=(255, 180, 160))

    # ── SIGNS ON WALL ─────────────────────────────────────────────────────
    # TAKE A NUMBER sign
    draw_framed_text(draw, 50, 40, "TAKE A\nNUMBER", w=110, h=58)

    # NOW SERVING display
    draw.rectangle([490, 40, 580, 95], fill=RED, outline=BLACK, width=2)
    draw.text((498, 48), "NOW", fill=WHITE, font=FONT)
    draw.text((494, 62), "SERVING", fill=WHITE, font=FONT)
    draw.text((510, 76), "#47", fill=YELLOW, font=FONT)

    # Clock
    draw_clock(draw, 320, 65)

    # ── POSTAL SCALE (left counter) ────────────────────────────────────────
    draw.rectangle([60, 260, 135, 300], fill=LIGHT_GRAY, outline=BLACK, width=2)
    draw.rectangle([74, 244, 121, 262], fill=GRAY, outline=BLACK, width=2)
    draw.text((82, 247), "LBS", fill=BLACK, font=FONT)

    # PAID stamp on counter
    draw.rectangle([160, 272, 208, 292], fill=RED, outline=DARK_BROWN, width=2)
    draw.text((165, 275), "PAID", fill=WHITE, font=FONT)

    # ── NUMBER TICKET on floor ─────────────────────────────────────────────
    draw.rectangle([85, 418, 120, 434], fill=WHITE, outline=GRAY, width=1)
    draw.text((90, 420), "#47", fill=BLACK, font=FONT)


def _scene_freezer(draw, post):
    """Freezer interior: shelves, ice cube, frozen food, frost texture."""
    # Dark gray freezer walls
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(80, 85, 95))
    # Light frost patches on walls (sparse, not a blanket)
    spray_rect(draw, 0, 0, WIDTH, HEIGHT, (150, 160, 175), density=400)
    spray_rect(draw, 0, 0, WIDTH, 40, (200, 210, 220), density=150)

    # Two main shelves with perspective
    shelf_y1, shelf_y2 = 190, 320
    for sy in [shelf_y1, shelf_y2]:
        draw.rectangle([30, sy, 610, sy + 6], fill=(180, 185, 195), outline=(120, 125, 135), width=1)
        # Shelf supports
        draw.line([(30, sy + 6), (20, sy + 30)], fill=DARK_GRAY, width=2)
        draw.line([(610, sy + 6), (620, sy + 30)], fill=DARK_GRAY, width=2)

    # ICE CUBES stacked in back left (like original)
    for ix in range(50, 200, 25):
        for iy in range(100, shelf_y1, 25):
            c = random.choice([ICE_BLUE, LIGHT_ICE, (160, 210, 240)])
            draw.rectangle([ix, iy, ix + 22, iy + 22], fill=c, outline=(100, 150, 200), width=1)

    # SPIDER IN ICE CUBE — the main event, big and center
    ice_x, ice_y = 260, 90
    ice_w, ice_h = 120, 100
    # 3D ice cube effect
    draw.rectangle([ice_x, ice_y, ice_x + ice_w, ice_y + ice_h], fill=LIGHT_ICE, outline=BLUE, width=3)
    # Highlight edge
    draw.line([(ice_x, ice_y), (ice_x + 20, ice_y - 15)], fill=BLUE, width=2)
    draw.line([(ice_x + ice_w, ice_y), (ice_x + ice_w + 20, ice_y - 15)], fill=BLUE, width=2)
    draw.line([(ice_x + 20, ice_y - 15), (ice_x + ice_w + 20, ice_y - 15)], fill=BLUE, width=2)
    draw.line([(ice_x + ice_w, ice_y), (ice_x + ice_w, ice_y + ice_h)], fill=(130, 180, 220), width=2)
    draw.line([(ice_x + ice_w, ice_y + ice_h), (ice_x + ice_w + 20, ice_y + ice_h - 15)], fill=BLUE, width=2)
    draw.line([(ice_x + ice_w + 20, ice_y - 15), (ice_x + ice_w + 20, ice_y + ice_h - 15)], fill=BLUE, width=2)
    # Spider frozen inside
    draw_spidey(draw, ice_x + ice_w // 2, ice_y + ice_h // 2, size=18, expression="alarmed")

    # Frozen veggies bag (top shelf right)
    vx, vy = 450, shelf_y1 - 65
    draw.rectangle([vx, vy, vx + 80, vy + 60], fill=(50, 120, 200), outline=BLACK, width=2)
    draw.text((vx + 8, vy + 10), "FROZEN", fill=WHITE, font=FONT)
    draw.text((vx + 8, vy + 24), "VEGGIES", fill=LIGHT_GREEN, font=FONT)
    # Tiny pea shapes
    for _ in range(5):
        px = random.randint(vx + 10, vx + 70)
        py = random.randint(vy + 35, vy + 55)
        draw.ellipse([px, py, px + 5, py + 5], fill=GRASS_GREEN, outline=DARK_GREEN)

    # Brown box labeled "BURGERS" (top shelf)
    draw_labeled_box(draw, 560, shelf_y1 - 45, 45, 40, "BRGR", (160, 120, 70))

    # STEAK on lower shelf (like original — speckled texture)
    sx, sy = 400, shelf_y2 - 70
    draw.ellipse([sx, sy, sx + 100, sy + 60], fill=(200, 80, 60), outline=DARK_BROWN, width=2)
    spray_rect(draw, sx + 10, sy + 10, sx + 90, sy + 50, WHITE, density=80)
    spray_rect(draw, sx + 10, sy + 10, sx + 90, sy + 50, (180, 60, 40), density=60)
    # Bone
    draw.rectangle([sx + 60, sy + 20, sx + 85, sy + 30], fill=WHITE, outline=GRAY, width=1)

    # ICE CREAM TUB (lower shelf left)
    icx, icy = 50, shelf_y2 - 55
    draw.rectangle([icx, icy, icx + 55, icy + 50], fill=(230, 220, 200), outline=BLACK, width=2)
    draw.text((icx + 5, icy + 5), "ICE", fill=BROWN, font=FONT)
    draw.text((icx + 5, icy + 18), "CREAM", fill=BROWN, font=FONT)
    draw.ellipse([icx + 15, icy + 32, icx + 40, icy + 45], fill=PINK, outline=BROWN, width=1)

    # Frozen pizza box on bottom
    draw.rectangle([200, shelf_y2 + 10, 350, shelf_y2 + 40], fill=RED, outline=BLACK, width=2)
    draw.text((215, shelf_y2 + 17), "FROZEN PIZZA", fill=YELLOW, font=FONT)

    # Popsicle
    draw.rectangle([160, shelf_y2 - 40, 175, shelf_y2 - 5], fill=PURPLE, outline=BLACK, width=1)
    draw.rectangle([164, shelf_y2 - 5, 171, shelf_y2 + 10], fill=LIGHT_BROWN, outline=BLACK, width=1)

    # Thermometer on wall
    draw.rectangle([10, 50, 22, 130], fill=WHITE, outline=BLACK, width=1)
    draw.rectangle([13, 100, 19, 125], fill=BLUE)
    draw.ellipse([10, 120, 22, 135], fill=BLUE, outline=BLACK, width=1)
    draw.text((5, 40), "-20F", fill=WHITE, font=FONT)


def _scene_circus(draw, post):
    """Circus: cannon fires spidey into brick wall inside big top tent."""
    import math
    import random

    # ── FLAT VERTICAL STRIPES — clean MS Paint style ──────────────────────
    stripe_w = 48
    for i in range(0, WIDTH, stripe_w):
        color = RED if (i // stripe_w) % 2 == 0 else YELLOW
        draw.rectangle([i, 0, min(i + stripe_w, WIDTH), 395], fill=color)

    # ── DIRT FLOOR ────────────────────────────────────────────────────────
    floor_y = 395
    draw.rectangle([0, floor_y, WIDTH, 460], fill=(200, 170, 100))
    for _ in range(80):
        fx = random.randint(0, WIDTH)
        fy = random.randint(floor_y + 2, 458)
        draw.ellipse([fx, fy, fx + 3, fy + 2], fill=(160, 130, 70))

    # ── TENT CEILING / TOP BAR ────────────────────────────────────────────
    draw.rectangle([0, 0, WIDTH, 50], fill=(170, 25, 25))
    # Center pole flag
    draw.line([(WIDTH // 2, 0), (WIDTH // 2, 50)], fill=DARK_BROWN, width=7)
    draw.polygon([(WIDTH // 2, 4), (WIDTH // 2 + 30, 16), (WIDTH // 2, 30)],
                 fill=YELLOW, outline=BLACK, width=1)

    # ── PENNANT BUNTING ───────────────────────────────────────────────────
    bunting_y = 52
    draw.line([(0, bunting_y), (WIDTH, bunting_y)], fill=DARK_BROWN, width=2)
    bunting_colors = [RED, BLUE, YELLOW, GRASS_GREEN, PURPLE, ORANGE, WHITE]
    for idx, bpx in enumerate(range(6, WIDTH - 6, 30)):
        bc = bunting_colors[idx % len(bunting_colors)]
        draw.polygon([(bpx, bunting_y), (bpx + 15, bunting_y),
                      (bpx + 7, bunting_y + 18)], fill=bc, outline=BLACK, width=1)

    # ── BRICK WALL LEFT ────────────────────────────────────────────────────
    wall_x1, wall_y1 = 18, 62
    wall_x2, wall_y2 = 170, floor_y
    draw.rectangle([wall_x1, wall_y1, wall_x2, wall_y2],
                   fill=(185, 112, 78), outline=BLACK, width=3)
    brick_h = 20
    for row, wy in enumerate(range(wall_y1 + 4, wall_y2, brick_h)):
        draw.line([(wall_x1, wy), (wall_x2, wy)], fill=(140, 70, 40), width=1)
        offset = 20 if row % 2 == 0 else 0
        for vx in range(wall_x1 + offset, wall_x2, 40):
            draw.line([(vx, wy), (vx, min(wy + brick_h, wall_y2))],
                      fill=(140, 70, 40), width=1)

    # ── IMPACT SPLAT on wall — unmistakably a squished spider ──────────────
    impact_x, impact_y = 94, 210

    # Yellow starburst rays behind splat
    for angle_deg in range(0, 360, 30):
        ang = math.radians(angle_deg)
        ex = impact_x + int(44 * math.cos(ang))
        ey = impact_y + int(44 * math.sin(ang))
        draw.line([(impact_x, impact_y), (ex, ey)], fill=YELLOW, width=5)

    # Orange inner glow
    spray_paint(draw, impact_x, impact_y, 28, ORANGE, density=400)

    # Spider body — wide flat gray oval (squished against wall)
    draw.ellipse([impact_x - 28, impact_y - 10, impact_x + 28, impact_y + 10],
                 fill=LIGHT_GRAY, outline=BLACK, width=3)

    # X eyes (dead)
    for ex_off in [-10, 10]:
        draw.line([(impact_x + ex_off - 5, impact_y - 5),
                   (impact_x + ex_off + 5, impact_y + 5)], fill=BLACK, width=2)
        draw.line([(impact_x + ex_off + 5, impact_y - 5),
                   (impact_x + ex_off - 5, impact_y + 5)], fill=BLACK, width=2)

    # Wavy dead mouth
    draw.arc([impact_x - 8, impact_y + 1, impact_x + 8, impact_y + 9],
             start=0, end=180, fill=BLACK, width=2)

    # 8 legs splayed dramatically outward from squished body
    splat_leg_angles = [150, 130, 210, 230, 320, 340, 30, 50]
    for la in splat_leg_angles:
        ang = math.radians(la)
        lx = impact_x + int(40 * math.cos(ang))
        ly = impact_y + int(30 * math.sin(ang))
        # Kinked leg for cartoon squish effect
        mid_x = impact_x + int(20 * math.cos(ang)) + random.randint(-4, 4)
        mid_y = impact_y + int(15 * math.sin(ang)) + random.randint(-4, 4)
        draw.line([(impact_x, impact_y), (mid_x, mid_y)], fill=BLACK, width=2)
        draw.line([(mid_x, mid_y), (lx, ly)], fill=BLACK, width=2)

    # Small stars around splat
    for star_ang in [75, 165, 255, 345]:
        sa = math.radians(star_ang)
        ssx = impact_x + int(50 * math.cos(sa))
        ssy = impact_y + int(40 * math.sin(sa))
        pts = []
        for pt in range(5):
            outer = math.radians(pt * 72 - 90)
            inner = math.radians(pt * 72 - 90 + 36)
            pts.append((ssx + int(7 * math.cos(outer)), ssy + int(7 * math.sin(outer))))
            pts.append((ssx + int(3 * math.cos(inner)), ssy + int(3 * math.sin(inner))))
        draw.polygon(pts, fill=YELLOW, outline=BLACK, width=1)

    # ── CANNON on RIGHT, pointing LEFT ────────────────────────────────────
    cnx, cny = 490, 285

    # Carriage base
    draw.rectangle([cnx - 55, cny + 20, cnx + 50, cny + 38],
                   fill=DARK_BROWN, outline=BLACK, width=2)

    # Two wheels
    for wx_off in [-32, 32]:
        draw.ellipse([cnx + wx_off - 20, cny + 12,
                      cnx + wx_off + 20, cny + 52],
                     fill=DARK_GRAY, outline=BLACK, width=2)
        for sp in range(4):
            sa = math.radians(sp * 45)
            draw.line([(cnx + wx_off + int(5 * math.cos(sa)),
                        cny + 32 + int(5 * math.sin(sa))),
                       (cnx + wx_off + int(17 * math.cos(sa)),
                        cny + 32 + int(17 * math.sin(sa)))],
                      fill=LIGHT_BROWN, width=1)

    # Barrel pointing LEFT with slight upward angle
    brl_angle = math.pi + 0.1
    brl_len = 115
    brl_thick = 17
    dx_b = math.cos(brl_angle)
    dy_b = math.sin(brl_angle)
    brl_sx, brl_sy = cnx, cny + 8
    brl_ex = brl_sx + brl_len * dx_b
    brl_ey = brl_sy + brl_len * dy_b
    perp_x = -dy_b * brl_thick
    perp_y = dx_b * brl_thick
    barrel_poly = [
        (brl_sx + perp_x, brl_sy + perp_y),
        (brl_ex + perp_x * 0.65, brl_ey + perp_y * 0.65),
        (brl_ex - perp_x * 0.65, brl_ey - perp_y * 0.65),
        (brl_sx - perp_x, brl_sy - perp_y),
    ]
    draw.polygon(barrel_poly, fill=(80, 80, 80), outline=BLACK, width=2)

    # Barrel bands
    for t_band in [0.25, 0.6, 0.88]:
        bx1 = int(brl_sx + t_band * (brl_ex - brl_sx))
        by1 = int(brl_sy + t_band * (brl_ey - brl_sy))
        bp = 12
        draw.ellipse([bx1 - bp // 2, by1 - bp + 2,
                      bx1 + bp // 2, by1 + bp - 2],
                     fill=(50, 50, 50), outline=BLACK, width=1)

    # Muzzle opening
    draw.ellipse([int(brl_ex) - 13, int(brl_ey) - 13,
                  int(brl_ex) + 13, int(brl_ey) + 13],
                 fill=(30, 30, 30), outline=BLACK, width=2)

    # Messy smoke puffs from barrel mouth
    smk_x = int(brl_ex)
    smk_y = int(brl_ey)
    spray_paint(draw, smk_x - 20, smk_y, 28, LIGHT_GRAY, density=600)
    spray_paint(draw, smk_x - 36, smk_y - 10, 20, WHITE, density=450)
    spray_paint(draw, smk_x - 10, smk_y + 8, 16, LIGHT_GRAY, density=350)
    spray_cloud(draw, smk_x - 24, smk_y - 4, 22)

    # Fuse sparks on top of cannon
    draw.line([(cnx + 6, cny), (cnx + 16, cny - 18)], fill=DARK_BROWN, width=2)
    spray_paint(draw, cnx + 18, cny - 20, 10, YELLOW, density=200)
    spray_paint(draw, cnx + 17, cny - 18, 6, ORANGE, density=150)

    # ── DOTTED TRAJECTORY ARC: cannon → wall ──────────────────────────────
    # Arc from cannon muzzle to impact point on wall
    traj_sx = float(smk_x - 30)
    traj_sy = float(smk_y - 6)
    traj_ex = float(impact_x + 30)
    traj_ey = float(impact_y)
    for step in range(0, 105, 9):
        t = step / 100.0
        tx = int(traj_sx + t * (traj_ex - traj_sx))
        ty = int(traj_sy + t * (traj_ey - traj_sy) - 55 * math.sin(math.pi * t))
        # Skip if inside wall
        if tx < wall_x2 + 4:
            continue
        draw.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=LIGHT_GRAY)
        draw.ellipse([tx - 2, ty - 2, tx + 2, ty + 2], fill=WHITE)

    # ── SPIDEY MID-FLIGHT between cannon and wall ─────────────────────────
    fly_x, fly_y = 310, 200
    # White halo for contrast against striped background
    draw.ellipse([fly_x - 30, fly_y - 30, fly_x + 30, fly_y + 30],
                 fill=WHITE, outline=None)
    draw_spidey(draw, fly_x, fly_y, size=20, expression="alarmed")

    # Motion lines behind spidey (trailing right to show he's flying left)
    for li, ly_off in enumerate([-8, 0, 8]):
        lx_start = fly_x + 32 + li * 4
        draw.line([(lx_start, fly_y + ly_off),
                   (lx_start + 22, fly_y + ly_off)],
                  fill=DARK_GRAY, width=2)

    # ── "THE AMAZING SPIDEY!" BANNER — hung from ceiling ─────────────────
    bw, bh = 210, 28
    bx_ban = 195
    by_ban = 68
    # Ropes from ceiling
    draw.line([(bx_ban + 18, 50), (bx_ban + 18, by_ban)], fill=DARK_BROWN, width=2)
    draw.line([(bx_ban + bw - 18, 50), (bx_ban + bw - 18, by_ban)], fill=DARK_BROWN, width=2)
    # Banner body
    draw.rectangle([bx_ban, by_ban, bx_ban + bw, by_ban + bh],
                   fill=WHITE, outline=RED, width=3)
    draw.text((bx_ban + 8, by_ban + 8), "THE AMAZING SPIDEY!", fill=RED, font=FONT)

    # ── STICK FIGURE AUDIENCE (varied reactions) ───────────────────────────
    audience_y = floor_y - 2
    skin_opts = [SKIN, (210, 170, 130), (155, 110, 70)]
    for idx, ax in enumerate(range(178, 475, 44)):
        sc = skin_opts[idx % len(skin_opts)]
        # Legs
        draw.line([(ax, audience_y), (ax - 7, audience_y + 22)], fill=BLACK, width=2)
        draw.line([(ax, audience_y), (ax + 7, audience_y + 22)], fill=BLACK, width=2)
        # Body
        draw.line([(ax, audience_y), (ax, audience_y - 24)], fill=BLACK, width=2)
        # Varied arm poses
        if idx == 1:
            # Covering eyes
            draw.line([(ax, audience_y - 13), (ax - 14, audience_y - 20)], fill=BLACK, width=2)
            draw.line([(ax, audience_y - 13), (ax + 14, audience_y - 20)], fill=BLACK, width=2)
        elif idx == 3:
            # Arms down in shock
            draw.line([(ax, audience_y - 13), (ax - 10, audience_y - 5)], fill=BLACK, width=2)
            draw.line([(ax, audience_y - 13), (ax + 10, audience_y - 5)], fill=BLACK, width=2)
        else:
            # Arms raised
            draw.line([(ax, audience_y - 13), (ax - 14, audience_y - 28)], fill=BLACK, width=2)
            draw.line([(ax, audience_y - 13), (ax + 14, audience_y - 28)], fill=BLACK, width=2)
        # Head
        draw.ellipse([ax - 9, audience_y - 42, ax + 9, audience_y - 24],
                     fill=sc, outline=BLACK, width=2)
        # O-shaped shocked mouth
        draw.ellipse([ax - 4, audience_y - 36, ax + 4, audience_y - 28],
                     fill=BLACK, outline=BLACK, width=1)
        draw.ellipse([ax - 2, audience_y - 34, ax + 2, audience_y - 30],
                     fill=WHITE)

    # ── POPCORN BUCKET right side ──────────────────────────────────────────
    pk_x, pk_y = 566, floor_y - 66
    draw.polygon([(pk_x, pk_y), (pk_x + 38, pk_y),
                  (pk_x + 32, pk_y + 56), (pk_x + 6, pk_y + 56)],
                 fill=RED, outline=BLACK, width=2)
    draw.line([(pk_x + 10, pk_y), (pk_x + 8, pk_y + 56)], fill=WHITE, width=3)
    draw.line([(pk_x + 24, pk_y), (pk_x + 22, pk_y + 56)], fill=WHITE, width=3)
    draw.text((pk_x + 4, pk_y + 12), "POP", fill=YELLOW, font=FONT)
    draw.text((pk_x + 2, pk_y + 26), "CORN", fill=YELLOW, font=FONT)
    # Popcorn kernels
    for kx, ky in [(pk_x + 2, pk_y - 10), (pk_x + 12, pk_y - 16),
                   (pk_x + 22, pk_y - 11), (pk_x + 32, pk_y - 8)]:
        draw.ellipse([kx - 6, ky - 6, kx + 6, ky + 6],
                     fill=YELLOW, outline=BLACK, width=1)

    # ── CAPTION ────────────────────────────────────────────────────────────
    cap_y = floor_y + 68
    draw.rectangle([0, cap_y, WIDTH, HEIGHT], fill=(240, 240, 240))
    draw.text((10, cap_y + 8), post.get("caption", ""), fill=BLACK, font=FONT)
    draw.text((10, cap_y + 24), post.get("hashtags", ""), fill=DARK_GRAY, font=FONT)


def _scene_construction(draw, post):
    import math

    # Sky and background
    draw_sky(draw)
    draw_sun(draw, x=WIDTH - 55, y=45)
    spray_cloud(draw, 150, 70, 90)
    spray_cloud(draw, 420, 50, 70)

    # Ground — dirt construction site
    ground_y = 360
    draw.rectangle([0, ground_y, WIDTH, HEIGHT], fill=(170, 145, 100))
    spray_rect(draw, 0, ground_y, WIDTH, HEIGHT, DARK_BROWN, density=350)
    spray_rect(draw, 0, ground_y, WIDTH, HEIGHT, (155, 130, 90), density=250)

    # === WET CEMENT SIDEWALK SLAB — lower left, large and prominent ===
    slab_x1, slab_y1 = 20, 368
    slab_x2, slab_y2 = 270, 465
    draw.rectangle([slab_x1, slab_y1, slab_x2, slab_y2], fill=(190, 190, 190), outline=BLACK, width=3)
    # Expansion joint dividing into two squares
    slab_mid_x = (slab_x1 + slab_x2) // 2
    draw.line([(slab_mid_x, slab_y1), (slab_mid_x, slab_y2)], fill=(140, 140, 140), width=2)

    # "WET" flag staked into slab
    draw.line([(slab_x1 + 18, slab_y1 - 35), (slab_x1 + 18, slab_y1 + 12)], fill=DARK_GRAY, width=2)
    draw.rectangle([slab_x1 + 19, slab_y1 - 35, slab_x1 + 58, slab_y1 - 20], fill=BRIGHT_ORANGE, outline=BLACK, width=1)
    draw.text((slab_x1 + 23, slab_y1 - 33), "WET", fill=WHITE, font=FONT)

    # Spider leg-print impressions — LEFT panel, bold and clear
    # Body impression (darker oval in cement)
    imp_cx, imp_cy = 100, 410
    draw.ellipse([imp_cx - 16, imp_cy - 10, imp_cx + 16, imp_cy + 10],
                 fill=(160, 160, 160), outline=(80, 80, 80), width=2)
    # 8 leg impressions radiating clearly — arranged like real spider legs
    leg_data = [
        (-16, -6,  -42, -20),
        (-14, -8,  -36, -30),
        (-12, -9,  -28, -38),
        ( -8, -10, -16, -42),
        ( 16, -6,   42, -20),
        ( 14, -8,   36, -30),
        ( 12, -9,   28, -38),
        (  8, -10,  16, -42),
    ]
    for lx1, ly1, lx2, ly2 in leg_data:
        draw.line([(imp_cx + lx1, imp_cy + ly1), (imp_cx + lx2, imp_cy + ly2)],
                  fill=(80, 80, 80), width=4)
    # tiny dot eyes impression
    draw.ellipse([imp_cx - 7, imp_cy - 5, imp_cx - 3, imp_cy - 1], fill=(80, 80, 80))
    draw.ellipse([imp_cx + 3,  imp_cy - 5, imp_cx + 7, imp_cy - 1], fill=(80, 80, 80))

    # === CEMENT MIXER — large, centered, YELLOW ===
    mx, my = 400, 210

    # Stand legs
    draw.rectangle([mx - 55, my + 72, mx - 34, my + 128], fill=(55, 55, 55), outline=BLACK, width=2)
    draw.rectangle([mx + 34, my + 72, mx + 55, my + 128], fill=(55, 55, 55), outline=BLACK, width=2)
    # Axle crossbar
    draw.rectangle([mx - 66, my + 108, mx + 66, my + 126], fill=(55, 55, 55), outline=BLACK, width=2)

    # Wheels
    draw.ellipse([mx - 82, my + 106, mx - 44, my + 144], fill=BLACK, outline=DARK_GRAY, width=3)
    draw.ellipse([mx - 70, my + 118, mx - 56, my + 132], fill=DARK_GRAY)
    draw.ellipse([mx + 44, my + 106, mx + 82, my + 144], fill=BLACK, outline=DARK_GRAY, width=3)
    draw.ellipse([mx + 56, my + 118, mx + 70, my + 132], fill=DARK_GRAY)

    # Drum body — large YELLOW oval
    draw.ellipse([mx - 92, my - 88, mx + 92, my + 84], fill=YELLOW, outline=BLACK, width=4)
    # Orange horizontal band stripes
    draw.line([(mx - 80, my - 10), (mx + 80, my - 10)], fill=BRIGHT_ORANGE, width=12)
    draw.line([(mx - 72, my + 16), (mx + 72, my + 16)], fill=BRIGHT_ORANGE, width=6)

    # Chute/spout — angled down-left toward the slab
    chute_base_x = mx - 58
    chute_base_y = my + 58
    chute_pts = [
        (chute_base_x,       chute_base_y),
        (chute_base_x - 14,  chute_base_y + 40),
        (chute_base_x - 115, chute_base_y + 52),
        (chute_base_x - 100, chute_base_y + 12),
    ]
    draw.polygon(chute_pts, fill=GRAY, outline=BLACK, width=2)

    # Cement dripping from chute tip — chunky gray splat, not dots
    tip_x = chute_base_x - 118
    tip_y = chute_base_y + 56
    # Pour stream
    draw.rectangle([tip_x - 8, tip_y, tip_x + 8, tip_y + 40], fill=(160, 160, 160))
    spray_paint(draw, tip_x, tip_y + 40, 18, (170, 170, 170), density=60)
    draw.ellipse([tip_x - 14, tip_y + 34, tip_x + 14, tip_y + 54],
                 fill=(160, 160, 160), outline=(120, 120, 120), width=1)

    # === DRUM OPENING — large dark oval at top ===
    opening_cx = mx
    opening_cy = my - 84

    # Outer rim (thick black)
    draw.ellipse([opening_cx - 62, opening_cy - 28,
                  opening_cx + 62, opening_cy + 28],
                 fill=(15, 15, 15), outline=BLACK, width=4)
    # Inner depth
    draw.ellipse([opening_cx - 48, opening_cy - 19,
                  opening_cx + 48, opening_cy + 19],
                 fill=(35, 35, 35))
    # Wet cement pool visible inside bottom of drum
    draw.ellipse([opening_cx - 32, opening_cy + 6,
                  opening_cx + 32, opening_cy + 20],
                 fill=(155, 155, 155))

    # === SPIDEY — SMALL, clearly FALLING HEAD-FIRST INTO drum ===
    # Positioned just ABOVE the opening, body tilted nose-down
    spider_cx = opening_cx + 5
    spider_cy = opening_cy - 38

    # Tilt: draw body as slightly rotated — head toward drum
    # Gray oval body (small — size ~16)
    body_w, body_h = 14, 10
    draw.ellipse([spider_cx - body_w, spider_cy - body_h,
                  spider_cx + body_w, spider_cy + body_h],
                 fill=LIGHT_GRAY, outline=BLACK, width=2)

    # 8 legs flailing UPWARD — tumbling posture, legs waving above
    flail_legs = [
        # left legs flung up-left
        (-13, -6,  -42, -30),
        (-10, -8,  -30, -44),
        ( -5, -10,  -8, -50),
        (  2, -10,   4, -52),
        # right legs flung up-right
        ( 13, -6,   42, -30),
        ( 10, -8,   30, -44),
        (  5, -10,   8, -50),
        ( -2, -10,  -4, -52),
    ]
    for lx1, ly1, lx2, ly2 in flail_legs:
        draw.line([(spider_cx + lx1, spider_cy + ly1),
                   (spider_cx + lx2, spider_cy + ly2)],
                  fill=BLACK, width=2)

    # White sclera eyes (alarmed) — high contrast on dark drum
    draw.ellipse([spider_cx - 9, spider_cy - 7, spider_cx - 2, spider_cy + 1],
                 fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([spider_cx + 2,  spider_cy - 7, spider_cx + 9, spider_cy + 1],
                 fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([spider_cx - 8,  spider_cy - 6, spider_cx - 3, spider_cy - 1],
                 fill=BLACK)
    draw.ellipse([spider_cx + 3,  spider_cy - 6, spider_cx + 8, spider_cy - 1],
                 fill=BLACK)
    # Open horrified mouth
    draw.arc([spider_cx - 5, spider_cy + 1, spider_cx + 5, spider_cy + 8],
             start=0, end=180, fill=BLACK, width=2)

    # Motion lines showing downward fall
    for i in range(3):
        lx = spider_cx - 4 + i * 4
        draw.line([(lx, spider_cy - 52), (lx, spider_cy - 30)],
                  fill=(100, 100, 100), width=2)

    # === HARDHAT — sitting on ground beside mixer, clearly a hardhat ===
    hx, hy = mx + 108, ground_y - 2
    # Brim
    draw.ellipse([hx - 24, hy - 6, hx + 24, hy + 8], fill=YELLOW, outline=BLACK, width=2)
    # Dome
    draw.ellipse([hx - 16, hy - 28, hx + 16, hy + 4], fill=YELLOW, outline=BLACK, width=2)
    draw.rectangle([hx - 15, hy - 2, hx + 15, hy + 6], fill=YELLOW)
    # Orange stripe
    draw.line([(hx - 11, hy - 14), (hx + 11, hy - 14)], fill=BRIGHT_ORANGE, width=3)

    # === RIGHT SIDE — traffic cone + warning sign ===
    draw_traffic_cone(draw, 548, 310, size=1.0)

    # Warning sign post + triangle
    draw.line([(558, 268), (558, ground_y)], fill=DARK_GRAY, width=3)
    draw.polygon([(526, 270), (590, 270), (558, 232)],
                 fill=YELLOW, outline=BLACK, width=2)
    draw.text((543, 253), "WET", fill=BLACK, font=FONT)

    # Lunch box — small hidden charm tucked near cone
    draw_labeled_box(draw, 488, ground_y + 2, 38, 24, "LUNCH", RED)

    # Caption
    draw.text((10, 10), post.get("caption", ""), fill=BLACK, font=FONT)


def _scene_volcano(draw, post):
    """Volcano: erupting mountain, lava, debris, flying spider, palm trees."""
    draw_sky(draw)
    # Smoky sky near volcano
    spray_rect(draw, 150, 0, 500, 120, (130, 130, 150), density=600)

    # VOLCANO — massive, fills center
    draw.polygon([(80, HEIGHT), (560, HEIGHT), (320, 80)],
                  fill=DARK_BROWN, outline=BROWN, width=3)
    # Lava streaks down sides
    for _ in range(8):
        sx = random.randint(250, 390)
        ex = sx + random.randint(-60, 60)
        draw.line([(sx, 140), (ex, random.randint(300, 440))], fill=LAVA_ORANGE, width=3)
        draw.line([(sx + 3, 145), (ex + 5, random.randint(300, 440))], fill=LAVA_RED, width=2)

    # Lava pool at top
    draw.ellipse([250, 70, 390, 160], fill=LAVA_RED)
    spray_rect(draw, 260, 80, 380, 150, LAVA_ORANGE, density=400)
    spray_rect(draw, 270, 90, 370, 140, YELLOW, density=200)

    # Rock texture on mountain
    spray_rect(draw, 180, 200, 460, 450, BROWN, density=400)
    spray_rect(draw, 200, 250, 440, 400, (120, 80, 40), density=200)

    # DEBRIS flying everywhere
    for _ in range(15):
        dx = random.randint(180, 460)
        dy = random.randint(30, 160)
        length = random.randint(8, 18)
        angle = random.uniform(0, 2 * math.pi)
        ex = dx + int(length * math.cos(angle))
        ey = dy + int(length * math.sin(angle))
        color = random.choice([RED, YELLOW, LAVA_ORANGE, BRIGHT_RED])
        draw.line([(dx, dy), (ex, ey)], fill=color, width=2)

    # SPIDEY being flung!
    draw_spidey(draw, 200, 100, size=16, expression="alarmed")
    # Motion lines
    for ml in range(5):
        draw.line([(220 + ml * 3, 90 + ml * 5), (240 + ml * 3, 100 + ml * 5)],
                   fill=BLACK, width=1)

    # Palm trees at base
    draw_palm_tree(draw, 50, HEIGHT - 30, height=100)
    draw_palm_tree(draw, 600, HEIGHT - 30, height=80)

    # Seagulls fleeing
    draw_seagulls(draw, count=4)

    # Ground at base
    draw.rectangle([0, HEIGHT - 40, WIDTH, HEIGHT], fill=DARK_GREEN)
    spray_rect(draw, 0, HEIGHT - 40, WIDTH, HEIGHT, GRASS_GREEN, density=300)

    # Tiny sign: "DANGER: ACTIVE VOLCANO"
    draw.rectangle([10, HEIGHT - 80, 120, HEIGHT - 55], fill=YELLOW, outline=BLACK, width=2)
    draw.text((15, HEIGHT - 76), "DANGER!", fill=RED, font=FONT)


def _scene_kitchen(draw, post):
    """Kitchen: oven, counter, utensils, fridge, spider on plate."""
    draw_room(draw, wall_color=WALL_TEAL, floor_color=FLOOR_TAN, floor_y=400)

    # OVEN — big, center-left
    ox, oy = 120, 200
    ow, oh = 180, 200
    draw.rectangle([ox, oy, ox + ow, oy + oh], fill=BLACK, outline=BLACK, width=3)
    # Oven door
    draw.rectangle([ox + 10, oy + 60, ox + ow - 10, oy + oh - 10], fill=DARK_GRAY, outline=BLACK, width=2)
    # Window in door
    draw.rectangle([ox + 30, oy + 80, ox + ow - 30, oy + 140], fill=(255, 200, 100), outline=BLACK, width=2)
    # Orange glow inside
    spray_rect(draw, ox + 35, oy + 85, ox + ow - 35, 335, ORANGE, density=200)
    spray_rect(draw, ox + 40, oy + 100, ox + ow - 40, 320, YELLOW, density=100)
    # Burner knobs
    for kx in range(ox + 30, ox + ow - 20, 40):
        draw.ellipse([kx, oy + 15, kx + 20, oy + 35], fill=BLACK, outline=GRAY, width=1)
    # Temperature display
    draw.rectangle([ox + ow - 45, oy + 15, ox + ow - 10, oy + 40], fill=BLACK, outline=GRAY)
    draw.text((ox + ow - 42, oy + 20), "450F", fill=RED, font=FONT)

    # Counter to the right
    draw.rectangle([340, 280, 600, 310], fill=BROWN, outline=DARK_BROWN, width=2)
    draw.rectangle([340, 310, 600, 400], fill=DARK_BROWN, outline=BLACK, width=1)

    # Spider on a serving plate on counter
    plate_x, plate_y = 420, 260
    draw.ellipse([plate_x, plate_y, plate_x + 70, plate_y + 25], fill=WHITE, outline=GRAY, width=2)
    draw_spidey(draw, plate_x + 35, plate_y + 5, size=12, expression="alarmed")

    # Knife and fork on counter
    draw.line([(380, 270), (380, 305)], fill=GRAY, width=2)
    draw.rectangle([377, 265, 383, 275], fill=GRAY, outline=DARK_GRAY)
    draw.line([(510, 270), (510, 305)], fill=GRAY, width=2)
    # Fork tines
    for fx in range(507, 514, 2):
        draw.line([(fx, 265), (fx, 275)], fill=GRAY, width=1)

    # Cookbook on counter
    draw.rectangle([530, 260, 580, 295], fill=RED, outline=BLACK, width=2)
    draw.text((535, 270), "COOK\nBOOK", fill=WHITE, font=FONT)

    # Framed painting on wall (happy spider in garden, like original)
    draw_framed_picture(draw, 350, 80, w=120, h=90, content="landscape")

    # Ceiling light
    draw.rectangle([230, 5, 330, 15], fill=YELLOW, outline=GRAY, width=1)

    # Salt and pepper on counter
    for sx_off, label in [(350, "S"), (365, "P")]:
        draw.rectangle([sx_off, 268, sx_off + 12, 280], fill=WHITE, outline=BLACK, width=1)
        draw.text((sx_off + 3, 270), label, fill=BLACK, font=FONT)

    # Fridge in background right
    draw.rectangle([560, 80, 630, 400], fill=LIGHT_GRAY, outline=BLACK, width=2)
    draw.rectangle([565, 85, 625, 230], fill=WHITE, outline=GRAY, width=1)
    draw.rectangle([565, 240, 625, 395], fill=WHITE, outline=GRAY, width=1)
    draw.ellipse([567, 150, 575, 162], fill=DARK_GRAY)  # handle
    draw.ellipse([567, 310, 575, 322], fill=DARK_GRAY)  # handle
    # Fridge magnet
    draw.rectangle([580, 100, 610, 115], fill=RED)
    draw.text((583, 102), "PIZZA", fill=WHITE, font=FONT)

    # Pot on stove
    draw.ellipse([ox + 20, oy - 5, ox + 70, oy + 15], fill=DARK_GRAY, outline=BLACK, width=2)
    # Steam
    for _ in range(3):
        sx = random.randint(ox + 30, ox + 60)
        draw.line([(sx, oy - 5), (sx + random.randint(-5, 5), oy - 20)], fill=LIGHT_GRAY, width=1)

    # Clock
    draw_clock(draw, 500, 50)


def _scene_bathroom(draw, post):
    """Bathroom: bathtub, shower, toaster, checkered floor, wall art."""
    draw_room(draw, wall_color=WALL_YELLOW, floor_y=420)
    draw_checkered_floor(draw, y=420, size=45)

    # BATHTUB — big and central like the original
    tub_x, tub_y = 120, 260
    tub_w, tub_h = 350, 130
    # Tub body
    draw.ellipse([tub_x, tub_y, tub_x + tub_w, tub_y + tub_h + 30],
                  fill=GRAY, outline=BLACK, width=3)
    # Water in tub
    draw.ellipse([tub_x + 15, tub_y + 15, tub_x + tub_w - 15, tub_y + tub_h + 10],
                  fill=LIGHT_BLUE, outline=BLUE, width=2)
    # Tub feet
    for fx in [tub_x + 30, tub_x + tub_w - 30]:
        draw.ellipse([fx - 8, tub_y + tub_h + 15, fx + 8, tub_y + tub_h + 30],
                      fill=GRAY, outline=BLACK, width=2)

    # Showerhead
    sh_x = tub_x - 20
    draw.line([(sh_x, 150), (sh_x, 270)], fill=GRAY, width=4)
    draw.line([(sh_x, 150), (sh_x + 50, 150)], fill=GRAY, width=4)
    # Showerhead shape
    draw.ellipse([sh_x + 35, 145, sh_x + 70, 165], fill=GRAY, outline=BLACK, width=2)
    # Water drops
    for _ in range(6):
        dx = random.randint(sh_x + 40, sh_x + 65)
        dy = random.randint(170, 250)
        draw.line([(dx, dy), (dx, dy + 8)], fill=BLUE, width=1)

    # Rubber duck
    draw_rubber_duck(draw, tub_x + 50, tub_y + 30, size=18)

    # Spider in the tub
    draw_spidey(draw, tub_x + tub_w // 2 - 20, tub_y + 50, size=16, expression="surprised")

    # Toaster in the tub!
    toast_x = tub_x + tub_w // 2 + 40
    toast_y = tub_y + 35
    draw.rectangle([toast_x, toast_y, toast_x + 50, toast_y + 40],
                    fill=GRAY, outline=BLACK, width=2)
    draw.rectangle([toast_x + 10, toast_y + 3, toast_x + 40, toast_y + 12],
                    fill=DARK_GRAY)  # slots
    # Cord going to outlet
    draw.line([(toast_x + 50, toast_y + 30), (540, toast_y + 30),
               (540, 320)], fill=BLACK, width=2)

    # Lightning bolts!
    draw_lightning_bolts(draw, toast_x + 25, toast_y - 15, count=3)
    draw_lightning_bolts(draw, toast_x - 10, toast_y + 20, count=2)

    # Wall outlet
    draw_electrical_outlet(draw, 530, 315)

    # "Home is where the heart is" spider web art
    draw_framed_picture(draw, 500, 100, w=110, h=85, content="spider_web")
    draw.text((505, 170), "Home is where\nthe heart is", fill=BLACK, font=FONT)

    # Soap bottle on tub edge
    draw.rectangle([tub_x + tub_w - 40, tub_y - 15, tub_x + tub_w - 20, tub_y + 10],
                    fill=GRASS_GREEN, outline=BLACK, width=1)

    # Bath mat on floor
    draw.rectangle([tub_x + 80, 420, tub_x + 200, 450],
                    fill=PINK, outline=(200, 120, 140), width=2)


def _scene_island(draw, post):
    """Desert island: ocean, palm tree, spider, tiny drink, sun, seagulls."""
    draw_sky(draw)
    draw_sun(draw, x=50, y=45)
    draw_water(draw, y=280)

    # ISLAND — sandy mound in center
    island_cx = 310
    draw.ellipse([island_cx - 120, 310, island_cx + 120, 410],
                  fill=SAND_YELLOW, outline=DARK_BROWN, width=2)
    # Sand texture
    spray_rect(draw, island_cx - 100, 320, island_cx + 100, 400, (240, 230, 150), density=300)
    spray_rect(draw, island_cx - 80, 330, island_cx + 80, 390, (210, 200, 120), density=150)

    # Palm tree
    draw_palm_tree(draw, island_cx - 30, 340, height=140)

    # Coconuts at base of tree
    for cx_off in [-40, -25]:
        draw.ellipse([island_cx + cx_off, 335, island_cx + cx_off + 10, 345],
                      fill=BROWN, outline=DARK_BROWN, width=1)

    # Spidey on the island, looking sad
    draw_spidey(draw, island_cx + 40, 345, size=16, expression="sad")

    # Tiny drink with straw and umbrella
    drink_x = island_cx - 60
    # Glass
    draw.polygon([(drink_x, 340), (drink_x + 15, 340), (drink_x + 12, 360), (drink_x + 3, 360)],
                  fill=RED, outline=BLACK, width=1)
    # Straw
    draw.line([(drink_x + 7, 325), (drink_x + 10, 345)], fill=YELLOW, width=2)
    # Tiny umbrella
    draw.arc([drink_x, 320, drink_x + 15, 335], start=180, end=0, fill=PINK, width=2)

    # Seagulls
    draw_seagulls(draw, count=4)

    # Message in a bottle floating in water
    bottle_x = 100
    draw.ellipse([bottle_x, 310, bottle_x + 25, 325], fill=GRASS_GREEN, outline=BLACK, width=1)
    draw.rectangle([bottle_x + 9, 305, bottle_x + 16, 312], fill=BROWN, outline=BLACK, width=1)
    # Paper sticking out
    draw.rectangle([bottle_x + 10, 298, bottle_x + 15, 306], fill=WHITE, outline=BLACK, width=1)

    # "HELP" written in sand
    draw.text((island_cx + 20, 370), "HELP", fill=DARK_BROWN, font=FONT)

    # Tiny crab on island
    crab_x = island_cx + 80
    draw.ellipse([crab_x, 355, crab_x + 10, 362], fill=RED, outline=BLACK, width=1)
    draw.line([(crab_x, 358), (crab_x - 6, 353)], fill=RED, width=1)
    draw.line([(crab_x + 10, 358), (crab_x + 16, 353)], fill=RED, width=1)


def _scene_garden(draw, post):
    """Garden: flowers, trees, fence, watering can, spider amid greenery."""
    draw_sky(draw)
    draw_sun(draw, x=WIDTH - 55, y=40)
    draw_ground(draw, y=320)

    # Trees in background
    draw_tree(draw, 80, 220)
    draw_tree(draw, 550, 240)

    # White picket fence
    for fx in range(0, WIDTH, 30):
        draw.rectangle([fx, 280, fx + 10, 330], fill=WHITE, outline=GRAY, width=1)
        # Pointed top
        draw.polygon([(fx, 280), (fx + 10, 280), (fx + 5, 270)], fill=WHITE, outline=GRAY, width=1)
    draw.line([(0, 295), (WIDTH, 295)], fill=WHITE, width=4)
    draw.line([(0, 315), (WIDTH, 315)], fill=WHITE, width=4)

    # Flowers everywhere
    for fx in range(100, 550, 45):
        fy = random.randint(335, 360)
        draw_flower(draw, fx + random.randint(-10, 10), fy,
                     color=random.choice([PINK, YELLOW, RED, ORANGE, PURPLE]))

    # Watering can
    wc_x, wc_y = 200, 360
    draw.rectangle([wc_x, wc_y, wc_x + 35, wc_y + 30], fill=TEAL, outline=BLACK, width=2)
    draw.line([(wc_x + 35, wc_y + 5), (wc_x + 55, wc_y - 10)], fill=TEAL, width=3)
    # Handle
    draw.arc([wc_x + 5, wc_y - 15, wc_x + 30, wc_y + 5], start=180, end=0, fill=TEAL, width=3)

    # Spidey among the flowers
    draw_spidey(draw, 350, 350, size=16, expression="surprised")

    # Butterfly
    bfx, bfy = 420, 250
    draw.ellipse([bfx - 8, bfy - 5, bfx, bfy + 5], fill=YELLOW, outline=BLACK, width=1)
    draw.ellipse([bfx, bfy - 5, bfx + 8, bfy + 5], fill=ORANGE, outline=BLACK, width=1)
    draw.ellipse([bfx - 2, bfy - 2, bfx + 2, bfy + 2], fill=BLACK)

    # Bird on fence
    bird_x = 350
    draw.ellipse([bird_x, 265, bird_x + 12, 278], fill=RED, outline=BLACK, width=1)
    draw.polygon([(bird_x + 12, 270), (bird_x + 18, 271), (bird_x + 12, 273)], fill=ORANGE)
    draw.ellipse([bird_x + 7, 267, bird_x + 10, 270], fill=BLACK)

    # Potted plant
    draw_potted_plant(draw, 480, 340)

    draw_seagulls(draw, count=2)


def _scene_sky(draw, post):
    """Sky scene: balloons, clouds, spider floating up, sun, birds, airplane."""
    draw_sky(draw)
    draw_sun(draw, x=WIDTH - 50, y=50)

    # Extra big fluffy clouds
    for _ in range(6):
        cx = random.randint(50, WIDTH - 50)
        cy = random.randint(100, 400)
        spray_cloud(draw, cx, cy, random.uniform(0.8, 1.5))

    # BALLOONS tied to spider
    spider_x, spider_y = 200, 220
    balloon_colors = [RED, BLUE, YELLOW, BRIGHT_RED, GRASS_GREEN, PURPLE, ORANGE]
    random.shuffle(balloon_colors)
    for i, color in enumerate(balloon_colors[:5]):
        bx = spider_x - 40 + i * 20
        by = spider_y - 80 - random.randint(0, 20)
        draw_balloon(draw, bx, by, color, size=25)
        # String to spider
        draw.line([(bx, by + 4), (spider_x, spider_y - 15)], fill=BLACK, width=1)

    # Spidey being lifted
    draw_spidey(draw, spider_x, spider_y, size=18, expression="alarmed")

    # An airplane in the distance
    plane_x, plane_y = 500, 100
    draw.rectangle([plane_x, plane_y, plane_x + 40, plane_y + 10], fill=WHITE, outline=BLACK, width=1)
    # Wings
    draw.polygon([(plane_x + 15, plane_y), (plane_x + 25, plane_y - 15),
                   (plane_x + 30, plane_y)], fill=WHITE, outline=BLACK, width=1)
    # Tail
    draw.polygon([(plane_x, plane_y), (plane_x - 5, plane_y - 10),
                   (plane_x + 5, plane_y)], fill=WHITE, outline=BLACK, width=1)
    # Contrail
    draw.line([(plane_x + 40, plane_y + 5), (plane_x + 80, plane_y + 5)], fill=WHITE, width=2)

    # Birds in distance
    draw_seagulls(draw, count=3)

    # Ground far below
    draw.rectangle([0, HEIGHT - 50, WIDTH, HEIGHT], fill=GRASS_GREEN)
    spray_rect(draw, 0, HEIGHT - 50, WIDTH, HEIGHT, DARK_GREEN, density=200)
    # Tiny houses on ground
    for hx in range(50, WIDTH - 50, 80):
        hy = HEIGHT - 40
        draw.rectangle([hx, hy, hx + 15, hy + 12], fill=random.choice([RED, BLUE, YELLOW, WHITE]), outline=BLACK, width=1)
        draw.polygon([(hx - 2, hy), (hx + 17, hy), (hx + 7, hy - 8)], fill=BROWN, outline=BLACK, width=1)


def _scene_elevator(draw, post):
    """Elevator scene."""
    _scene_generic_indoor(draw, post)


def _scene_gym(draw, post):
    """Gym scene."""
    _scene_generic_indoor(draw, post)


def _scene_movie_theater(draw, post):
    import math

    # Dark theater background
    draw.rectangle([0, 0, 640, 480], fill=(30, 8, 8))

    # Side wall panels
    draw.rectangle([0, 0, 70, 480], fill=(55, 12, 12))
    draw.rectangle([570, 0, 640, 480], fill=(55, 12, 12))

    # Wall sconces (left and right)
    for wx in [45, 595]:
        draw.ellipse([wx-13, 115, wx+13, 143], fill=(220, 200, 70), outline=(140, 110, 30), width=2)
        draw.rectangle([wx-4, 143, wx+4, 162], fill=(160, 130, 50))

    # Movie screen
    draw.rectangle([80, 18, 550, 210], fill=(235, 228, 188), outline=(150, 130, 70), width=5)
    draw.rectangle([88, 26, 542, 202], fill=(215, 208, 170))
    draw.text((160, 100), "NOW SHOWING:", fill=(190, 183, 150), font=FONT)
    draw.text((165, 116), "CHARLOTTE'S WEB", fill=(190, 183, 150), font=FONT)

    # Curtains left and right
    draw.polygon([(80, 18), (118, 18), (102, 210), (80, 210)], fill=(110, 15, 22))
    draw.polygon([(550, 18), (512, 18), (526, 210), (550, 210)], fill=(110, 15, 22))

    # Lobby window top right — Charlotte's Web marquee
    draw.rectangle([572, 8, 638, 105], fill=(75, 155, 195), outline=(65, 45, 25), width=3)
    draw.line([(605, 8), (605, 105)], fill=(65, 45, 25), width=2)
    draw.line([(572, 52), (638, 52)], fill=(65, 45, 25), width=2)
    draw.rectangle([574, 54, 636, 103], fill=(10, 10, 10))
    for mx in range(577, 634, 7):
        draw.ellipse([mx-3, 57, mx+3, 63], fill=YELLOW)
    draw.text((577, 66), "CHARLOTTE'S", fill=YELLOW, font=FONT)
    draw.text((590, 80), "WEB", fill=YELLOW, font=FONT)
    draw.text((578, 0), "LOBBY", fill=LIGHT_GRAY, font=FONT)

    # Seat rows — back row
    seat_col = (140, 18, 28)
    seat_dk = (90, 10, 16)
    seat_ol = (60, 6, 10)
    for sx in range(100, 530, 52):
        draw.rectangle([sx, 222, sx+36, 248], fill=seat_col, outline=seat_ol, width=2)
        draw.rectangle([sx, 212, sx+36, 226], fill=seat_dk, outline=seat_ol, width=2)

    # Middle row
    for sx in range(88, 548, 62):
        draw.rectangle([sx, 262, sx+44, 292], fill=seat_col, outline=seat_ol, width=2)
        draw.rectangle([sx, 249, sx+44, 266], fill=seat_dk, outline=seat_ol, width=2)

    # Front row — Spidey sits center
    front_y = 348
    seat_w = 58
    seat_gap = 76
    seats_start = 82
    for i in range(7):
        sx = seats_start + i * seat_gap
        draw.rectangle([sx, front_y, sx+seat_w, front_y+52], fill=seat_col, outline=seat_ol, width=2)
        draw.rectangle([sx, front_y-17, sx+seat_w, front_y+5], fill=seat_dk, outline=seat_ol, width=2)

    # Spidey in center seat (index 3)
    spidey_i = 3
    spidey_sx = seats_start + spidey_i * seat_gap
    spidey_cx = spidey_sx + seat_w // 2
    spidey_cy = front_y + 18

    # Armrests for Spidey's seat
    draw.rectangle([spidey_sx - 7, front_y, spidey_sx + 3, front_y + 40], fill=(70, 10, 16), outline=seat_ol, width=1)
    draw.rectangle([spidey_sx + seat_w - 3, front_y, spidey_sx + seat_w + 9, front_y + 40], fill=(70, 10, 16), outline=seat_ol, width=1)

    # Junior Mints on right armrest — bigger, higher contrast
    jm_x = spidey_sx + seat_w + 10
    jm_y = front_y - 10
    draw.rectangle([jm_x, jm_y, jm_x + 30, jm_y + 42], fill=(10, 50, 15), outline=WHITE, width=2)
    draw.rectangle([jm_x + 2, jm_y + 2, jm_x + 28, jm_y + 14], fill=(180, 20, 20))
    draw.text((jm_x + 4, jm_y + 16), "JR.", fill=WHITE, font=FONT)
    draw.text((jm_x + 2, jm_y + 28), "MINTS", fill=WHITE, font=FONT)

    # Popcorn bucket in Spidey's legs (left side)
    pop_x = spidey_cx - 52
    pop_y = front_y - 8
    draw.polygon([(pop_x, pop_y), (pop_x + 28, pop_y), (pop_x + 23, pop_y + 34), (pop_x + 5, pop_y + 34)], fill=RED, outline=BLACK, width=2)
    draw.line([(pop_x + 10, pop_y), (pop_x + 8, pop_y + 34)], fill=WHITE, width=2)
    draw.line([(pop_x + 18, pop_y), (pop_x + 16, pop_y + 34)], fill=WHITE, width=2)
    spray_paint(draw, pop_x + 14, pop_y - 8, 14, WHITE, density=28)
    spray_paint(draw, pop_x + 14, pop_y - 8, 9, YELLOW, density=18)
    draw.text((pop_x + 5, pop_y + 12), "POP", fill=WHITE, font=FONT)

    # Light beam — wide, bright trapezoid
    beam_top_cx = spidey_cx + 10
    beam_pts = [
        (beam_top_cx - 45, 55),
        (beam_top_cx + 45, 55),
        (spidey_cx + 50, spidey_cy - 5),
        (spidey_cx - 50, spidey_cy - 5),
    ]
    draw.polygon(beam_pts, fill=(255, 255, 200))
    spray_rect(draw, spidey_cx - 50, 55, spidey_cx + 50, spidey_cy - 5, (255, 255, 160), density=6)

    # Projector — large, heavy, rotated, FALLING down beam toward Spidey
    # Position it partway down — clearly falling, not at top
    proj_cx = spidey_cx + 8
    proj_cy = 168
    pw, ph = 96, 56
    a = math.radians(18)
    corners = []
    for dx, dy in [(-pw//2, -ph//2), (pw//2, -ph//2), (pw//2, ph//2), (-pw//2, ph//2)]:
        rx = dx * math.cos(a) - dy * math.sin(a)
        ry = dx * math.sin(a) + dy * math.cos(a)
        corners.append((proj_cx + rx, proj_cy + ry))
    draw.polygon(corners, fill=(50, 48, 44))
    draw.polygon(corners, outline=(210, 190, 140), width=3)

    # Reels on top of projector
    for roff in [(-20, -30), (20, -30)]:
        rcx = int(proj_cx + roff[0] * math.cos(a) - roff[1] * math.sin(a))
        rcy = int(proj_cy + roff[0] * math.sin(a) + roff[1] * math.cos(a))
        draw.ellipse([rcx - 14, rcy - 14, rcx + 14, rcy + 14], fill=(30, 26, 22), outline=(180, 155, 110), width=2)
        draw.ellipse([rcx - 6, rcy - 6, rcx + 6, rcy + 6], fill=(55, 50, 42))

    # Lens (front of projector)
    lx = int(proj_cx - 38 * math.cos(a) + 6 * math.sin(a))
    ly = int(proj_cy - 38 * math.sin(a) - 6 * math.cos(a) + 8)
    draw.ellipse([lx - 13, ly - 13, lx + 13, ly + 13], fill=(18, 18, 32), outline=(210, 195, 155), width=3)
    draw.ellipse([lx - 6, ly - 6, lx + 6, ly + 6], fill=(45, 45, 115))
    draw.text((proj_cx - 22, proj_cy - 6), "PROJECTOR", fill=LIGHT_GRAY, font=FONT)

    # Motion/speed lines above projector (falling indicator)
    for i in range(7):
        lmx = proj_cx - 32 + i * 11
        draw.line([(lmx, proj_cy - 44), (lmx - 4, proj_cy - 70)], fill=LIGHT_GRAY, width=2)

    # Panic burst around Spidey — yellow star lines
    for i in range(10):
        ang = math.radians(i * 36)
        ex = int(spidey_cx + math.cos(ang) * 38)
        ey = int(spidey_cy - 6 + math.sin(ang) * 22)
        draw.line([(spidey_cx, spidey_cy - 6), (ex, ey)], fill=YELLOW, width=3)

    # Floor
    draw.rectangle([0, 403, 640, 422], fill=(38, 10, 10))
    draw.rectangle([0, 420, 640, 480], fill=(22, 5, 5))

    # Spidey — alarmed, in the seat, looking up
    draw_spidey(draw, spidey_cx, spidey_cy, size=22, expression="alarmed")


def _scene_ski_resort(draw, post):
    # Sky - flat ICE_BLUE
    draw.rectangle([0, 0, 640, 480], fill=ICE_BLUE)

    # Clouds
    spray_cloud(draw, 80, 60, 0.8)
    spray_cloud(draw, 200, 45, 0.7)
    spray_cloud(draw, 530, 55, 0.6)

    # Mountain - large flat white triangle on right
    draw.polygon([(280, 480), (640, 480), (640, 300), (520, 60), (320, 200)], fill=WHITE, outline=LIGHT_BLUE)

    # Ski slope / run (light blue channel down the mountain)
    draw.polygon([(420, 100), (460, 100), (580, 420), (530, 420)], fill=LIGHT_BLUE)

    # BUNNY SLOPE flag at top
    flag_x, flag_y = 432, 68
    draw.line([flag_x, flag_y, flag_x, flag_y + 32], fill=DARK_GRAY, width=3)
    draw.polygon([(flag_x, flag_y), (flag_x + 52, flag_y + 10), (flag_x, flag_y + 20)], fill=BRIGHT_ORANGE, outline=DARK_BROWN, width=1)
    draw.text((flag_x + 3, flag_y + 5), "BUNNY SLOPE", font=FONT, fill=WHITE)

    # SKI LODGE on the left
    lodge_x, lodge_y = 30, 270
    draw.rectangle([lodge_x, lodge_y, lodge_x + 120, lodge_y + 90], fill=LIGHT_BROWN, outline=DARK_BROWN, width=3)
    draw.polygon([(lodge_x - 8, lodge_y), (lodge_x + 60, lodge_y - 38), (lodge_x + 128, lodge_y)], fill=BROWN, outline=DARK_BROWN, width=3)
    # Snow on roof
    draw.polygon([(lodge_x - 8, lodge_y), (lodge_x + 60, lodge_y - 38), (lodge_x + 128, lodge_y),
                  (lodge_x + 112, lodge_y - 5), (lodge_x + 60, lodge_y - 30), (lodge_x + 12, lodge_y - 5)], fill=WHITE)
    # Sign
    draw.rectangle([lodge_x + 15, lodge_y - 55, lodge_x + 105, lodge_y - 40], fill=LIGHT_BROWN, outline=DARK_BROWN, width=2)
    draw.text((lodge_x + 17, lodge_y - 53), "SKI LODGE", font=FONT, fill=DARK_BROWN)
    # Window (glowing yellow)
    draw.rectangle([lodge_x + 12, lodge_y + 15, lodge_x + 52, lodge_y + 50], fill=YELLOW, outline=DARK_BROWN, width=2)
    draw.line([lodge_x + 32, lodge_y + 15, lodge_x + 32, lodge_y + 50], fill=DARK_BROWN, width=1)
    draw.line([lodge_x + 12, lodge_y + 32, lodge_x + 52, lodge_y + 32], fill=DARK_BROWN, width=1)
    # Door
    draw.rectangle([lodge_x + 72, lodge_y + 52, lodge_x + 100, lodge_y + 90], fill=DARK_BROWN, outline=BLACK, width=2)
    # HOT COCOA MUG on windowsill
    mx, my = lodge_x + 56, lodge_y + 46
    draw.rectangle([mx, my, mx + 12, my + 12], fill=RED, outline=DARK_BROWN, width=2)
    draw.arc([mx + 9, my + 2, mx + 16, my + 9], start=270, end=90, fill=DARK_BROWN, width=2)
    draw.line([mx + 3, my - 4, mx + 2, my - 8], fill=LIGHT_GRAY, width=2)
    draw.line([mx + 7, my - 4, mx + 8, my - 9], fill=LIGHT_GRAY, width=2)

    # Ground snow
    draw.rectangle([0, 400, 640, 480], fill=WHITE)
    draw.line([0, 400, 640, 400], fill=LIGHT_BLUE, width=2)
    spray_paint(draw, 200, 412, 60, LIGHT_ICE, density=0.2)
    spray_paint(draw, 450, 415, 50, LIGHT_ICE, density=0.2)

    # Small trees on left for resort feel
    draw.rectangle([175, 330, 185, 400], fill=DARK_BROWN, width=2)
    spray_paint(draw, 180, 315, 22, DARK_GREEN, density=0.95)
    draw.rectangle([215, 340, 223, 400], fill=DARK_BROWN, width=2)
    spray_paint(draw, 219, 326, 18, DARK_GREEN, density=0.95)

    # ---- AVALANCHE rolling down slope toward Spidey ----
    # Shadow behind to separate from white mountain
    draw.polygon([(390, 150), (460, 130), (580, 420), (530, 420), (440, 200)], fill=LIGHT_BLUE)

    # Avalanche mass - chunky spray clouds tumbling diagonally
    for cx, cy in [(445, 148), (415, 178), (470, 162), (388, 210), (430, 200),
                   (362, 245), (400, 238), (338, 280), (372, 270), (315, 318),
                   (350, 305), (292, 355), (325, 342)]:
        spray_paint(draw, cx, cy, 55, WHITE, density=0.98)

    # ICE_BLUE depth tint on avalanche edges
    for cx, cy in [(450, 155), (415, 195), (375, 240), (340, 280), (310, 325)]:
        spray_paint(draw, cx, cy, 28, ICE_BLUE, density=0.28)

    # Flying snow dust ahead of the wave (reaching toward Spidey)
    spray_paint(draw, 272, 365, 25, WHITE, density=0.75)
    spray_paint(draw, 258, 385, 18, WHITE, density=0.65)

    # Spray clouds billowing above the avalanche
    spray_cloud(draw, 455, 118, 0.9)
    spray_cloud(draw, 490, 108, 0.75)
    spray_cloud(draw, 420, 135, 0.7)

    # AVALANCHE label
    draw.text((355, 225), "AVALANCHE", font=FONT, fill=DARK_GRAY)

    # ---- SPIDEY at bottom, in path of avalanche ----
    spidey_x, spidey_y = 195, 378

    # Skis
    draw.rectangle([spidey_x - 34, spidey_y + 14, spidey_x + 2, spidey_y + 18], fill=BRIGHT_ORANGE, outline=DARK_BROWN, width=2)
    draw.polygon([(spidey_x - 34, spidey_y + 14), (spidey_x - 41, spidey_y + 11), (spidey_x - 34, spidey_y + 18)], fill=BRIGHT_ORANGE)
    draw.rectangle([spidey_x + 2, spidey_y + 14, spidey_x + 36, spidey_y + 18], fill=BRIGHT_ORANGE, outline=DARK_BROWN, width=2)
    draw.polygon([(spidey_x + 36, spidey_y + 14), (spidey_x + 43, spidey_y + 11), (spidey_x + 36, spidey_y + 18)], fill=BRIGHT_ORANGE)

    # Ski poles
    draw.line([spidey_x - 18, spidey_y - 2, spidey_x - 40, spidey_y + 15], fill=DARK_GRAY, width=2)
    draw.ellipse([spidey_x - 44, spidey_y + 12, spidey_x - 36, spidey_y + 18], fill=BLACK)
    draw.line([spidey_x + 18, spidey_y - 2, spidey_x + 40, spidey_y + 15], fill=DARK_GRAY, width=2)
    draw.ellipse([spidey_x + 36, spidey_y + 12, spidey_x + 44, spidey_y + 18], fill=BLACK)

    # Red scarf
    draw.rectangle([spidey_x - 14, spidey_y - 10, spidey_x + 14, spidey_y - 3], fill=RED, outline=DARK_BROWN, width=1)
    draw.rectangle([spidey_x + 8, spidey_y - 10, spidey_x + 17, spidey_y + 5], fill=RED, outline=DARK_BROWN, width=1)

    # Spidey - bigger (size=26), happy/oblivious
    draw_spidey(draw, spidey_x, spidey_y, size=26, expression="happy")

    # Goggles on forehead
    draw.ellipse([spidey_x - 22, spidey_y - 40, spidey_x - 8, spidey_y - 27], fill=LIGHT_BLUE, outline=BLACK, width=2)
    draw.ellipse([spidey_x + 8, spidey_y - 40, spidey_x + 22, spidey_y - 27], fill=LIGHT_BLUE, outline=BLACK, width=2)
    draw.line([spidey_x - 22, spidey_y - 33, spidey_x - 29, spidey_y - 33], fill=BLACK, width=2)
    draw.line([spidey_x + 22, spidey_y - 33, spidey_x + 29, spidey_y - 33], fill=BLACK, width=2)
    draw.line([spidey_x - 8, spidey_y - 33, spidey_x + 8, spidey_y - 33], fill=DARK_GRAY, width=2)


def _scene_golf_course(draw, post):
    # Sky background
    draw_sky(draw)

    # Green fairway ground
    draw.rectangle([0, 300, 640, 480], fill=(75, 170, 50))
    # Lighter fairway strip
    draw.rectangle([0, 300, 640, 320], fill=(95, 195, 65))

    # Hand-painted messy clouds
    spray_cloud(draw, 140, 80, 1.1)
    spray_cloud(draw, 400, 60, 0.85)

    # Smiley sun top-right corner
    draw_sun(draw, x=590, y=45)

    # ---- FLAG + HOLE (right side) ----
    flag_x = 520
    draw.ellipse([flag_x - 18, 293, flag_x + 18, 303], fill=(50, 130, 35), outline=BLACK, width=2)
    draw.ellipse([flag_x - 7, 296, flag_x + 7, 302], fill=(30, 90, 20))
    draw.line([flag_x, 296, flag_x, 215], fill=DARK_GRAY, width=3)
    # Striped flag (red/white)
    for i in range(4):
        fc = RED if i % 2 == 0 else WHITE
        draw.rectangle([flag_x + 2, 215 + i * 8, flag_x + 32, 223 + i * 8], fill=fc)
    draw.rectangle([flag_x + 2, 215, flag_x + 32, 247], outline=BLACK, width=2)

    # ---- GOLF CART with striped umbrella ----
    cx, cy = 420, 305
    # Umbrella pole
    draw.line([cx + 32, cy + 8, cx + 32, cy - 28], fill=DARK_BROWN, width=2)
    # Umbrella canopy striped
    for i in range(5):
        sc = YELLOW if i % 2 == 0 else WHITE
        draw.pieslice([cx + 4, cy - 42, cx + 60, cy - 14],
                      start=180 + i * 36, end=180 + (i + 1) * 36, fill=sc, outline=BLACK)
    draw.arc([cx + 4, cy - 42, cx + 60, cy - 14], start=180, end=360, fill=BLACK, width=2)
    # Cart body
    draw.rectangle([cx, cy + 8, cx + 65, cy + 35], fill=WHITE, outline=BLACK, width=2)
    draw.rectangle([cx + 5, cy - 2, cx + 60, cy + 10], fill=LIGHT_BLUE, outline=BLACK, width=2)
    # Wheels
    draw.ellipse([cx + 4, cy + 28, cx + 22, cy + 46], fill=DARK_GRAY, outline=BLACK, width=2)
    draw.ellipse([cx + 44, cy + 28, cx + 62, cy + 46], fill=DARK_GRAY, outline=BLACK, width=2)
    draw.ellipse([cx + 8, cy + 32, cx + 18, cy + 42], fill=LIGHT_GRAY)
    draw.ellipse([cx + 48, cy + 32, cx + 58, cy + 42], fill=LIGHT_GRAY)

    # ---- SCORECARD on ground ----
    sc_x, sc_y = 30, 355
    draw.rectangle([sc_x, sc_y, sc_x + 110, sc_y + 65], fill=WHITE, outline=DARK_GRAY, width=2)
    draw.rectangle([sc_x, sc_y, sc_x + 110, sc_y + 14], fill=(190, 210, 255), outline=DARK_GRAY, width=1)
    draw.text((sc_x + 18, sc_y + 2), "SCORECARD", fill=BLACK, font=FONT)
    draw.text((sc_x + 4, sc_y + 17), "HOLE: 1 2 3 4 5 6 7 8 9", fill=DARK_GRAY, font=FONT)
    draw.text((sc_x + 4, sc_y + 30), "SCR:", fill=BLACK, font=FONT)
    for i in range(9):
        draw.text((sc_x + 34 + i * 9, sc_y + 30), "0", fill=RED, font=FONT)
    draw.text((sc_x + 20, sc_y + 47), "HOLE IN NONE", fill=DARK_GRAY, font=FONT)

    # ---- TEE in center ----
    tee_x, tee_y = 300, 308
    draw.polygon([
        (tee_x - 3, tee_y), (tee_x + 3, tee_y),
        (tee_x + 1, tee_y + 20), (tee_x - 1, tee_y + 20)
    ], fill=BRIGHT_ORANGE, outline=DARK_BROWN, width=1)
    draw.ellipse([tee_x - 9, tee_y - 9, tee_x + 9, tee_y + 1], fill=BRIGHT_ORANGE, outline=DARK_BROWN, width=1)

    # ---- SPIDEY squished under ball ----
    draw_spidey(draw, tee_x, tee_y - 2, size=16, expression="alarmed")

    # ---- GOLF BALL on top of Spidey ----
    ball_cx, ball_cy = tee_x, tee_y - 18
    draw.ellipse([ball_cx - 15, ball_cy - 15, ball_cx + 15, ball_cy + 15], fill=WHITE, outline=DARK_GRAY, width=2)
    for dx, dy in [(-5, -5), (5, -5), (0, 2), (-7, 2), (7, 2), (0, -10)]:
        draw.ellipse([ball_cx + dx - 2, ball_cy + dy - 2, ball_cx + dx + 2, ball_cy + dy + 2],
                     fill=LIGHT_GRAY, outline=GRAY, width=1)
    # Shadow under ball for weight
    draw.ellipse([ball_cx - 14, tee_y - 4, ball_cx + 14, tee_y + 2], fill=(50, 130, 30))

    # ---- GOLF CLUB swinging from upper-left ----
    shaft_start = (55, 55)
    shaft_end = (tee_x - 10, tee_y - 16)
    draw.line([shaft_start, shaft_end], fill=DARK_BROWN, width=7)
    draw.line([shaft_start, shaft_end], fill=BROWN, width=4)

    # Club head at impact point
    ang = math.atan2(shaft_end[1] - shaft_start[1], shaft_end[0] - shaft_start[0])
    hx, hy = shaft_end[0] - 4, shaft_end[1] + 5
    hw, hh = 24, 10
    corners = []
    for sx, sy in [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]:
        rx = hx + sx * math.cos(ang) - sy * math.sin(ang)
        ry = hy + sx * math.sin(ang) + sy * math.cos(ang)
        corners.append((rx, ry))
    draw.polygon(corners, fill=DARK_GRAY, outline=BLACK, width=2)

    # Grip wrapping at top of shaft
    for i in range(5):
        gx1 = shaft_start[0] - 5
        gy1 = shaft_start[1] + i * 7
        gx2 = shaft_start[0] + 6
        gy2 = shaft_start[1] + i * 7 + 4
        draw.line([(gx1, gy1), (gx2, gy2)], fill=BLACK, width=2)

    # Swing motion arcs (yellow, energetic)
    for radius, start_a, end_a in [(55, 15, 60), (70, 20, 55), (42, 25, 65)]:
        draw.arc([shaft_start[0] - radius, shaft_start[1] - radius // 2,
                  shaft_start[0] + radius, shaft_start[1] + radius // 2],
                 start=start_a, end=end_a, fill=YELLOW, width=3)

    # Impact burst lines around ball
    for i in range(6):
        a = math.radians(i * 60 + 10)
        lx1 = int(ball_cx + 17 * math.cos(a))
        ly1 = int(ball_cy + 17 * math.sin(a))
        lx2 = int(ball_cx + 28 * math.cos(a))
        ly2 = int(ball_cy + 28 * math.sin(a))
        draw.line([lx1, ly1, lx2, ly2], fill=YELLOW, width=2)


def _scene_hair_salon(draw, post):
    import math

    # Room: pink walls, checkered floor
    draw_room(draw, WALL_PINK, FLOOR_TAN, 320)
    draw_checkered_floor(draw, 320, 40)

    # === MIRROR (left wall) ===
    draw.rectangle([20, 20, 200, 200], fill=(180, 225, 255), outline=BLACK, width=3)
    draw.line([40, 40, 65, 75], fill=WHITE, width=3)
    draw.text((85, 28), "MIRROR", fill=DARK_GRAY, font=FONT)

    # Counter shelf
    draw.rectangle([10, 200, 270, 238], fill=LIGHT_BROWN, outline=BLACK, width=2)
    draw.rectangle([10, 233, 270, 242], fill=BROWN, outline=None)

    # Scissors
    draw.line([30, 208, 44, 228], fill=DARK_GRAY, width=2)
    draw.line([42, 208, 28, 228], fill=DARK_GRAY, width=2)
    draw.ellipse([29, 205, 37, 213], fill=None, outline=DARK_GRAY, width=2)
    draw.ellipse([37, 205, 45, 213], fill=None, outline=DARK_GRAY, width=2)

    # Hair dryer
    draw.rectangle([62, 208, 102, 230], fill=RED, outline=BLACK, width=2)
    draw.rectangle([96, 214, 114, 226], fill=RED, outline=BLACK, width=2)
    draw.text((66, 213), "DRYER", fill=WHITE, font=FONT)

    # TIPS jar with single coin
    draw.rectangle([128, 204, 163, 238], fill=(200, 235, 255), outline=BLACK, width=2)
    draw.text((135, 206), "TIPS", fill=BLACK, font=FONT)
    draw.ellipse([138, 220, 152, 232], fill=YELLOW, outline=BROWN, width=2)

    # Comb
    draw.rectangle([175, 214, 215, 220], fill=PURPLE, outline=BLACK, width=1)
    for i in range(6):
        draw.line([178 + i*6, 220, 178 + i*6, 230], fill=PURPLE, width=2)

    # === BLOWOUT POSTER (upper right) ===
    draw.rectangle([390, 15, 560, 180], fill=WHITE, outline=BLACK, width=3)
    draw.rectangle([396, 21, 554, 174], fill=(255, 248, 252), outline=None)
    # Poster spider legs
    for ang in [170, 145, 120, 95, 75, 50, 25, 5]:
        a = math.radians(ang)
        lx = int(472 + 30 * math.cos(a))
        ly = int(120 + 20 * math.sin(a))
        draw.line([472, 120, lx, ly], fill=BLACK, width=2)
    # Poster spider body
    draw.ellipse([455, 108, 490, 133], fill=GRAY, outline=BLACK, width=2)
    draw.ellipse([459, 111, 465, 117], fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([469, 111, 475, 117], fill=WHITE, outline=BLACK, width=1)
    draw.ellipse([461, 113, 463, 115], fill=BLACK)
    draw.ellipse([471, 113, 473, 115], fill=BLACK)
    # Big fluffy blowout
    spray_paint(draw, 472, 88, 30, PINK, density=120)
    spray_paint(draw, 472, 82, 22, (255, 155, 195), density=90)
    spray_paint(draw, 450, 98, 18, PINK, density=70)
    spray_paint(draw, 494, 98, 18, PINK, density=70)
    # Poster text
    draw.text((405, 148), "STYLE INSPO", fill=BLACK, font=FONT)
    draw.text((407, 160), "GET THE LOOK", fill=DARK_GRAY, font=FONT)

    # OPEN sign
    draw.rectangle([570, 45, 630, 70], fill=(0, 160, 0), outline=BLACK, width=2)
    draw.text((578, 52), "OPEN", fill=WHITE, font=FONT)

    # Salon name banner
    draw.rectangle([200, 452, 440, 472], fill=(240, 200, 210), outline=DARK_GRAY, width=1)
    draw.text((212, 457), "CURL UP & DYE SALON", fill=DARK_GRAY, font=FONT)

    # === STYLING CHAIR — center ===
    chair_cx = 360
    # Pedestal
    draw.rectangle([340, 370, 380, 395], fill=DARK_GRAY, outline=BLACK, width=2)
    draw.rectangle([325, 393, 395, 408], fill=DARK_GRAY, outline=BLACK, width=2)
    # Seat
    draw.rounded_rectangle([318, 338, 402, 374], radius=8, fill=RED, outline=BLACK, width=2)
    # Back
    draw.rounded_rectangle([314, 248, 406, 344], radius=12, fill=RED, outline=BLACK, width=3)
    # Armrests
    draw.rounded_rectangle([306, 320, 322, 354], radius=5, fill=RED, outline=BLACK, width=2)
    draw.rounded_rectangle([398, 320, 414, 354], radius=5, fill=RED, outline=BLACK, width=2)
    # Headrest
    draw.rounded_rectangle([334, 250, 386, 272], radius=6, fill=(200, 30, 30), outline=BLACK, width=2)

    # Cape (white striped bib)
    draw.polygon([(328, 295), (392, 295), (396, 365), (324, 365)], fill=WHITE, outline=BLACK, width=2)
    for y in [308, 324, 340, 356]:
        draw.line([328, y, 392, y], fill=LIGHT_GRAY, width=1)

    # === VAC-O-MATIC — big, red, left side ===
    draw.ellipse([30, 305, 220, 398], fill=RED, outline=BLACK, width=3)
    draw.text((72, 340), "VAC-O-MATIC", fill=WHITE, font=FONT)
    # Wheels
    draw.ellipse([42, 388, 82, 428], fill=DARK_GRAY, outline=BLACK, width=3)
    draw.ellipse([160, 388, 200, 428], fill=DARK_GRAY, outline=BLACK, width=3)
    # Power cord & outlet
    draw.line([50, 418, 18, 420], fill=BLACK, width=3)
    draw_electrical_outlet(draw, 10, 392)

    # === HOSE — thick, snaking from vacuum toward Spidey ===
    hose_pts = [(218, 330), (245, 315), (268, 304), (292, 296), (312, 286)]
    for i in range(len(hose_pts) - 1):
        draw.line([hose_pts[i], hose_pts[i+1]], fill=DARK_GRAY, width=11)
    for i in range(len(hose_pts) - 1):
        draw.line([hose_pts[i], hose_pts[i+1]], fill=GRAY, width=5)
    for i in range(len(hose_pts) - 1):
        mx = (hose_pts[i][0] + hose_pts[i+1][0]) // 2
        my = (hose_pts[i][1] + hose_pts[i+1][1]) // 2
        draw.ellipse([mx-5, my-4, mx+5, my+4], fill=None, outline=BLACK, width=1)

    # NOZZLE — gaping mouth pointed right at spidey
    draw.polygon([(303, 268), (326, 264), (330, 306), (307, 310)], fill=DARK_GRAY, outline=BLACK, width=2)
    draw.rectangle([324, 262, 344, 312], fill=BLACK, outline=DARK_GRAY, width=2)

    # Suction lines pulling Spidey left toward nozzle
    for offset in [-12, 0, 12]:
        draw.line([chair_cx - 20, 290 + offset, 346, 287 + offset], fill=LIGHT_BLUE, width=2)
    # Hair clippings being sucked too
    for hx, hy in [(290, 360), (330, 375), (370, 365), (410, 355), (260, 350)]:
        draw.arc([hx-7, hy-3, hx+7, hy+3], start=0, end=200, fill=GRAY, width=2)

    # Suction arcs around nozzle
    for r in [8, 16, 24]:
        draw.arc([342 - r, 287 - r, 342 + r, 287 + r], start=130, end=230, fill=LIGHT_BLUE, width=2)

    # === SPIDEY — alarmed, leaning toward vacuum ===
    draw_spidey(draw, chair_cx - 10, 288, size=20, expression="alarmed")


def _scene_aquarium(draw, post):
    # Dark aquarium hall background
    draw.rectangle([0, 0, 640, 480], fill=(18, 28, 58))
    draw.rectangle([0, 430, 640, 480], fill=(30, 40, 72))
    draw.rectangle([0, 0, 640, 28], fill=(12, 20, 45))

    # Ceiling lights
    for lx in [160, 480]:
        draw.polygon([lx-22, 4, lx+22, 4, lx+14, 28, lx-14, 28], fill=(225, 220, 175))
        draw.polygon([lx-22, 4, lx+22, 4, lx+14, 28, lx-14, 28], outline=BLACK, width=2)

    # Gift shop sign - bigger, bolder, top left
    draw.rectangle([8, 38, 230, 105], fill=(185, 25, 25))
    draw.rectangle([8, 38, 230, 105], outline=(235, 195, 45), width=3)
    draw.text((20, 46), "GIFT SHOP", fill=(255, 225, 45), font=FONT)
    draw.text((16, 62), "SPIDER MAGNETS", fill=(255, 255, 255), font=FONT)
    draw.text((65, 78), "$4.99", fill=(255, 225, 45), font=FONT)
    draw.polygon([232, 62, 248, 68, 232, 74], fill=(235, 195, 45))

    # Tank dimensions
    tx1, ty1, tx2, ty2 = 75, 110, 585, 385

    # Tank outer frame
    draw.rectangle([tx1-14, ty1-14, tx2+14, ty2+14], fill=(50, 65, 88))
    draw.rectangle([tx1-14, ty1-14, tx2+14, ty2+14], outline=(85, 105, 130), width=4)

    # Water
    draw.rectangle([tx1, ty1, tx2, ty2], fill=(0, 95, 140))

    # Sandy bottom
    draw.rectangle([tx1, ty2-40, tx2, ty2], fill=(180, 150, 75))
    for sx in range(tx1+10, tx2, 20):
        draw.ellipse([sx, ty2-38, sx+16, ty2-24], fill=(200, 170, 88))

    # Seaweed
    for wx, wh in [(150, 55), (230, 42), (400, 60), (500, 48)]:
        for i in range(wh, 0, -10):
            off = int(9 * math.sin(i * 0.28))
            draw.ellipse([wx+off-7, ty2-40-i-10, wx+off+7, ty2-40-i+10], fill=(0, 140, 55))

    # Bubbles - trail leading toward open mouth (fish at left of center)
    for bx, by in [(275, 300), (255, 268), (245, 240), (300, 320), (420, 275), (480, 300), (370, 250)]:
        draw.ellipse([bx-4, by-4, bx+4, by+4], outline=(130, 210, 230), width=2)

    # Small fish
    for (fx, fy, fc) in [(430, 270, (65, 115, 200)), (490, 295, (65, 115, 200)),
                          (350, 315, (65, 115, 200)), (280, 310, (225, 190, 28)),
                          (390, 248, (225, 190, 28))]:
        draw.ellipse([fx-18, fy-8, fx+18, fy+8], fill=fc)
        draw.polygon([fx+18, fy, fx+28, fy-8, fx+28, fy+8], fill=fc)
        draw.ellipse([fx-10, fy-4, fx-3, fy+4], fill=WHITE)
        draw.ellipse([fx-9, fy-3, fx-4, fy+3], fill=BLACK)

    # BIG orange fish — center-left, near surface, mouth wide open facing RIGHT (up)
    fish_cx = 290
    fish_cy = ty1 + 70

    # Body
    draw.ellipse([fish_cx-75, fish_cy-35, fish_cx+75, fish_cy+35], fill=(230, 95, 18))
    draw.ellipse([fish_cx-75, fish_cy-35, fish_cx+75, fish_cy+35], outline=(165, 60, 8), width=2)

    # Tail
    draw.polygon([fish_cx+75, fish_cy, fish_cx+108, fish_cy-30, fish_cx+108, fish_cy+30],
                 fill=(195, 70, 12), outline=(155, 50, 6), width=2)

    # Dorsal fin
    draw.polygon([fish_cx-10, fish_cy-35, fish_cx+15, fish_cy-62, fish_cx+40, fish_cy-35],
                 fill=(195, 70, 12), outline=(155, 50, 6), width=2)

    # Open mouth facing UP (upper jaw left, gaping toward surface)
    # Upper jaw
    draw.polygon([fish_cx-75, fish_cy-12, fish_cx-42, fish_cy-45, fish_cx-10, fish_cy-18],
                 fill=(230, 95, 18), outline=(165, 60, 8), width=2)
    # Lower jaw
    draw.polygon([fish_cx-75, fish_cy+12, fish_cx-42, fish_cy+42, fish_cx-10, fish_cy+15],
                 fill=(230, 95, 18), outline=(165, 60, 8), width=2)
    # Mouth interior
    draw.polygon([fish_cx-72, fish_cy-10, fish_cx-43, fish_cy-42,
                  fish_cx-12, fish_cy-16, fish_cx-12, fish_cy+13,
                  fish_cx-43, fish_cy+39, fish_cx-72, fish_cy+10],
                 fill=(155, 25, 18))
    # Tongue
    draw.ellipse([fish_cx-62, fish_cy-5, fish_cx-28, fish_cy+14], fill=(195, 55, 55))

    # Fish eye
    draw.ellipse([fish_cx-42, fish_cy-26, fish_cx-16, fish_cy+2], fill=WHITE)
    draw.ellipse([fish_cx-42, fish_cy-26, fish_cx-16, fish_cy+2], outline=(155, 50, 6), width=2)
    draw.ellipse([fish_cx-36, fish_cy-20, fish_cx-22, fish_cy-6], fill=BLACK)
    draw.ellipse([fish_cx-33, fish_cy-17, fish_cx-28, fish_cy-12], fill=WHITE)

    # Water surface wavy line
    for wx in range(tx1, tx2, 22):
        draw.arc([wx, ty1-7, wx+22, ty1+10], start=0, end=180, fill=(95, 200, 220), width=3)

    # Splash at spidey entry point
    spidey_x = fish_cx - 42
    spidey_y = ty1 + 40
    spl = [(spidey_x-18, ty1+8), (spidey_x-8, ty1-18), (spidey_x, ty1-6),
           (spidey_x+8, ty1-20), (spidey_x+16, ty1-10), (spidey_x+22, ty1+8)]
    draw.polygon(spl, fill=(145, 220, 238))
    draw.polygon(spl, outline=(70, 165, 198), width=2)

    # Railing above tank
    rail_y = ty1 - 16
    draw.rectangle([tx1-20, rail_y-10, tx2+20, rail_y], fill=(90, 110, 135))
    draw.rectangle([tx1-20, rail_y-10, tx2+20, rail_y], outline=(125, 148, 168), width=2)
    for px in range(tx1+10, tx2, 88):
        draw.rectangle([px-5, rail_y, px+5, rail_y+42], fill=(72, 90, 112))
        draw.rectangle([px-5, rail_y, px+5, rail_y+42], outline=(105, 128, 148), width=1)

    # Motion lines showing fall
    for i in range(4):
        lx = spidey_x - 16 + i*10
        draw.line([lx, spidey_y-32, lx-1, spidey_y-8], fill=(175, 205, 228), width=2)

    # SPIDEY - clearly falling, bigger, high contrast (inside tank near fish mouth)
    draw_spidey(draw, spidey_x, spidey_y, size=26, expression="alarmed")

    # Plaques below tank
    draw.rectangle([tx1+12, ty2+16, tx1+210, ty2+38], fill=(182, 150, 48))
    draw.rectangle([tx1+12, ty2+16, tx1+210, ty2+38], outline=(135, 108, 28), width=2)
    draw.text((tx1+22, ty2+22), "DO NOT TAP GLASS", fill=(22, 14, 6), font=FONT)

    draw.rectangle([tx2-182, ty2+16, tx2+12, ty2+38], fill=(25, 42, 78))
    draw.rectangle([tx2-182, ty2+16, tx2+12, ty2+38], outline=(78, 108, 138), width=2)
    draw.text((tx2-172, ty2+22), "EXHIBIT 4 - OPEN TANK", fill=(165, 210, 252), font=FONT)


def _scene_backyard_barbecue(draw, post):
    # Sky and ground
    draw_sky(draw)
    draw_sun(draw, x=580, y=50)
    draw_ground(draw, y=360, color=GRASS_GREEN, grass=True)

    # White picket fence in background
    for fx in range(0, 640, 32):
        draw.rectangle([fx+4, 280, fx+18, 360], fill=WHITE, outline=BLACK, width=1)
        draw.polygon([fx+4, 280, fx+11, 260, fx+18, 280], fill=WHITE, outline=BLACK, width=1)
    draw.rectangle([0, 310, 640, 330], fill=WHITE, outline=BLACK, width=1)

    # Clouds
    spray_cloud(draw, 150, 100, 60)
    spray_cloud(draw, 380, 120, 50)

    # Table on right with red checkered cloth
    draw.rectangle([430, 295, 620, 355], fill=DARK_BROWN, outline=BLACK, width=2)
    cell = 16
    for row in range(4):
        for col in range(12):
            x0 = 430 + col * cell
            y0 = 270 + row * cell
            fill = RED if (row + col) % 2 == 0 else WHITE
            draw.rectangle([x0, min(x0+cell, 620), y0, y0+cell], fill=fill)
    # redraw tablecloth properly
    for row in range(4):
        for col in range(12):
            x0 = 430 + col * cell
            y0 = 270 + row * cell
            fill = RED if (row + col) % 2 == 0 else WHITE
            draw.rectangle([x0, y0, x0+cell, y0+cell], fill=fill)
    draw.rectangle([430, 270, 622, 298], outline=BLACK, width=2)

    # Paper plate with smiley
    draw.ellipse([445, 273, 490, 296], fill=WHITE, outline=BLACK, width=2)
    draw.arc([455, 280, 480, 292], start=0, end=180, fill=BLACK, width=2)
    draw.ellipse([458, 276, 463, 281], fill=BLACK)
    draw.ellipse([472, 276, 477, 281], fill=BLACK)

    # Cup
    draw.polygon([500, 274, 512, 274, 510, 296, 502, 296], fill=LIGHT_BLUE, outline=BLACK, width=2)

    # Sign: SPIDEY'S FIRST BBQ leaning on table
    draw.rectangle([432, 248, 618, 268], fill=YELLOW, outline=BLACK, width=2)
    draw.text((436, 252), "SPIDEY'S FIRST BBQ", fill=BLACK, font=FONT)

    # GRILL — center-left, big and readable
    grill_cx = 240
    grill_top = 210
    grill_bot = 310

    # Grill legs
    draw.line([grill_cx - 60, grill_bot, grill_cx - 75, 370], fill=DARK_GRAY, width=5)
    draw.line([grill_cx + 60, grill_bot, grill_cx + 75, 370], fill=DARK_GRAY, width=5)

    # Grill bowl (half-circle shape using ellipse)
    draw.ellipse([grill_cx-100, grill_top, grill_cx+100, grill_bot+20], fill=DARK_GRAY, outline=BLACK, width=3)

    # Coals and flames inside bowl
    spray_paint(draw, grill_cx-30, grill_bot-10, 30, LAVA_RED, density=60)
    spray_paint(draw, grill_cx+20, grill_bot-10, 30, BRIGHT_ORANGE, density=60)
    spray_paint(draw, grill_cx, grill_bot-20, 25, YELLOW, density=40)
    # Flame wisps rising
    spray_paint(draw, grill_cx-20, grill_top+60, 18, BRIGHT_ORANGE, density=35)
    spray_paint(draw, grill_cx+20, grill_top+55, 18, YELLOW, density=30)

    # Grill grate
    for gx in range(grill_cx-90, grill_cx+95, 20):
        draw.line([gx, grill_top+40, gx, grill_bot], fill=BLACK, width=2)
    for gy in range(grill_top+40, grill_bot, 18):
        draw.line([grill_cx-90, gy, grill_cx+90, gy], fill=BLACK, width=2)

    # Lid hint (top arc outline)
    draw.arc([grill_cx-100, grill_top, grill_cx+100, grill_top+80], start=200, end=340, fill=BLACK, width=3)

    # SKEWER across grill — the star of the scene
    skewer_y = grill_top + 48
    draw.line([grill_cx - 115, skewer_y, grill_cx + 115, skewer_y], fill=LIGHT_GRAY, width=5)
    draw.line([grill_cx - 115, skewer_y, grill_cx + 115, skewer_y], fill=WHITE, width=2)

    # Tomato left
    draw.ellipse([grill_cx-80, skewer_y-13, grill_cx-50, skewer_y+13], fill=RED, outline=BLACK, width=2)
    draw.line([grill_cx-65, skewer_y-13, grill_cx-62, skewer_y-20], fill=DARK_GREEN, width=2)

    # SPIDEY on skewer — centered, high contrast bright background behind him
    draw.ellipse([grill_cx-22, skewer_y-22, grill_cx+22, skewer_y+22], fill=BRIGHT_ORANGE)
    draw_spidey(draw, grill_cx, skewer_y, size=20, expression="surprised")

    # Bell pepper right
    draw.rectangle([grill_cx+48, skewer_y-12, grill_cx+82, skewer_y+12], fill=LIGHT_GREEN, outline=BLACK, width=2)

    # Flowers in foreground
    draw_flower(draw, 60, 355, RED)
    draw_flower(draw, 370, 358, YELLOW)
    draw_flower(draw, 560, 352, PINK)


def _scene_car_wash(draw, post):
    # Yellow tunnel walls
    draw.rectangle([0, 0, 640, 480], fill=(235, 210, 80))

    # Add some grime streaks to walls for texture
    for x in [60, 140, 500, 580]:
        draw.rectangle([x, 100, x+4, 360], fill=(200, 180, 60))
    for x in [90, 170, 470, 550]:
        draw.rectangle([x, 150, x+2, 300], fill=(210, 190, 65))

    # Blue ceiling
    draw.rectangle([0, 0, 640, 100], fill=LIGHT_BLUE)

    # Floor with soapy water color
    floor_y = 360
    draw.rectangle([0, floor_y, 640, 480], fill=(190, 215, 235))

    # Horizontal dividers
    draw.line([0, 100, 640, 100], fill=DARK_GRAY, width=3)
    draw.line([0, floor_y, 640, floor_y], fill=DARK_GRAY, width=3)

    # Soap suds on floor - chunky spray blobs
    for cx, cy in [(80, 385), (180, 400), (440, 395), (560, 410)]:
        spray_paint(draw, cx, cy, 32, WHITE, density=70)

    # Smiley face drawn in soap suds near center-bottom - deliberate and charming
    sx, sy = 320, 410
    spray_paint(draw, sx, sy, 30, WHITE, density=55)
    draw.ellipse([sx-20, sy-14, sx+20, sy+14], outline=(170, 195, 215), width=2)
    draw.ellipse([sx-10, sy-6, sx-5, sy-1], fill=(170, 195, 215))
    draw.ellipse([sx+5, sy-6, sx+10, sy-1], fill=(170, 195, 215))
    draw.arc([sx-9, sy+2, sx+9, sy+11], start=0, end=180, fill=(170, 195, 215), width=2)

    # Ceiling soap suds
    for cx, cy in [(70, 92), (220, 80), (430, 86), (570, 90)]:
        spray_paint(draw, cx, cy, 24, WHITE, density=55)

    # DELUXE WASH sign
    draw.rectangle([175, 15, 465, 60], fill=GRASS_GREEN)
    draw.rectangle([175, 15, 465, 60], outline=DARK_GREEN, width=3)
    draw.text((205, 30), "DELUXE WASH", fill=WHITE, font=FONT)

    # Pine tree air freshener hanging from sign - bigger and clearer
    fx = 450
    draw.line([fx, 60, fx, 82], fill=DARK_BROWN, width=2)
    # Card top
    draw.rectangle([fx-8, 82, fx+8, 88], fill=(220, 220, 200))
    # Tree shape - three stacked triangles
    draw.polygon([fx, 66, fx-9, 84, fx+9, 84], fill=DARK_GREEN)
    draw.polygon([fx, 74, fx-11, 94, fx+11, 94], fill=DARK_GREEN)
    draw.polygon([fx, 82, fx-13, 104, fx+13, 104], fill=DARK_GREEN)
    draw.rectangle([fx-4, 103, fx+4, 112], fill=BROWN)

    # LEFT brush - wider, closer to center, with frayed edge feel
    bx1 = 195
    bw = 38
    draw.rectangle([bx1-bw, 103, bx1+bw, floor_y], fill=PINK)
    for i, y in enumerate(range(110, floor_y, 26)):
        col = RED if i % 2 == 0 else (230, 80, 120)
        draw.rectangle([bx1-bw, y, bx1+bw, y+14], fill=col)
    draw.ellipse([bx1-bw, 98, bx1+bw, 126], fill=(220, 100, 140))
    draw.ellipse([bx1-bw, floor_y-18, bx1+bw, floor_y+8], fill=(220, 100, 140))
    draw.rectangle([bx1-bw, 98, bx1+bw, 100], outline=DARK_GRAY, width=2)
    # Frayed bristle lines on right side of left brush
    for y in range(120, floor_y, 18):
        draw.line([bx1+bw, y, bx1+bw+10, y+5], fill=(200, 60, 100), width=2)
        draw.line([bx1+bw, y+6, bx1+bw+8, y+2], fill=(220, 80, 120), width=1)
    # Motion arcs
    for y_m in [155, 215, 275, 315]:
        draw.arc([bx1-bw-8, y_m, bx1+bw+8, y_m+22], start=190, end=350, fill=DARK_GRAY, width=2)

    # RIGHT brush - wider, closer to center
    bx2 = 445
    draw.rectangle([bx2-bw, 103, bx2+bw, floor_y], fill=PINK)
    for i, y in enumerate(range(115, floor_y, 26)):
        col = RED if i % 2 == 0 else (230, 80, 120)
        draw.rectangle([bx2-bw, y, bx2+bw, y+14], fill=col)
    draw.ellipse([bx2-bw, 98, bx2+bw, 126], fill=(220, 100, 140))
    draw.ellipse([bx2-bw, floor_y-18, bx2+bw, floor_y+8], fill=(220, 100, 140))
    # Frayed bristle lines on left side of right brush
    for y in range(120, floor_y, 18):
        draw.line([bx2-bw, y, bx2-bw-10, y+5], fill=(200, 60, 100), width=2)
        draw.line([bx2-bw, y+6, bx2-bw-8, y+2], fill=(220, 80, 120), width=1)
    for y_m in [155, 215, 275, 315]:
        draw.arc([bx2-bw-8, y_m, bx2+bw+8, y_m+22], start=190, end=350, fill=DARK_GRAY, width=2)

    # Spidey caught between brushes - bright background patch so he pops
    draw.ellipse([290, 205, 350, 265], fill=WHITE)
    draw.ellipse([290, 205, 350, 265], outline=LIGHT_GRAY, width=1)

    # Radiating shred lines from brushes toward Spidey
    cx_s, cy_s = 320, 238
    for angle_deg in [170, 185, 195, 10, 355, 345]:
        a = angle_deg * 3.14159 / 180
        x2 = cx_s + int(55 * math.cos(a))
        y2 = cy_s + int(55 * math.sin(a))
        draw.line([cx_s, cy_s, x2, y2], fill=RED, width=2)

    draw_spidey(draw, cx_s, cy_s, size=16, expression="surprised")


def _scene_library(draw, post):
    """Library scene — Spidey crushed under a stack of encyclopedias."""
    # Walls and floor
    draw_room(draw, wall_color=BEIGE, floor_color=DARK_BROWN, floor_y=400)

    # Back wall shelves — full height bookshelves on both sides
    for shelf_x, shelf_w in [(0, 150), (490, 150)]:
        draw.rectangle([shelf_x, 30, shelf_x + shelf_w, 400], fill=BROWN, outline=DARK_BROWN, width=2)
        for sy in range(45, 390, 45):
            draw.line([(shelf_x + 5, sy), (shelf_x + shelf_w - 5, sy)], fill=DARK_BROWN, width=2)
            for bx in range(shelf_x + 8, shelf_x + shelf_w - 8, 12):
                c = random.choice([RED, BLUE, DARK_GREEN, PURPLE, BROWN, MAROON, NAVY, ORANGE])
                bh = random.randint(25, 38)
                draw.rectangle([bx, sy + 3, bx + 9, sy + bh], fill=c, outline=BLACK, width=1)

    # Reading table in center
    draw.rectangle([200, 310, 440, 335], fill=LIGHT_BROWN, outline=DARK_BROWN, width=2)
    draw.rectangle([215, 335, 235, 400], fill=LIGHT_BROWN, outline=DARK_BROWN, width=1)
    draw.rectangle([405, 335, 425, 400], fill=LIGHT_BROWN, outline=DARK_BROWN, width=1)

    # Tiny open book on table
    draw.rectangle([280, 300, 310, 310], fill=WHITE, outline=DARK_GRAY, width=1)
    draw.rectangle([310, 300, 340, 310], fill=WHITE, outline=DARK_GRAY, width=1)
    draw.line([(310, 300), (310, 310)], fill=BLACK, width=1)

    # Spidey at the table with tiny reading glasses
    draw_spidey(draw, 320, 290, size=16, expression="alarmed")
    # Glasses
    draw.ellipse([312, 286, 320, 292], fill=None, outline=BLACK, width=1)
    draw.ellipse([322, 286, 330, 292], fill=None, outline=BLACK, width=1)

    # Teetering stack of encyclopedias falling onto Spidey
    stack_x = 300
    colors_list = [RED, BLUE, DARK_GREEN, PURPLE, MAROON, NAVY, ORANGE, BROWN]
    for j in range(8):
        y = 220 - j * 22
        tilt = j * 2  # increasing tilt as stack goes up
        c = colors_list[j % len(colors_list)]
        draw.polygon([
            (stack_x - 30 + tilt, y),
            (stack_x + 30 + tilt, y),
            (stack_x + 30 + tilt - 2, y + 18),
            (stack_x - 30 + tilt - 2, y + 18),
        ], fill=c, outline=BLACK, width=1)
        # Volume label
        vol = f"Vol.{j + 1}"
        draw.text((stack_x - 20 + tilt, y + 4), vol, font=FONT, fill=WHITE)

    # OVERDUE library card on floor
    draw.rectangle([180, 380, 240, 395], fill=WHITE, outline=BLACK, width=1)
    draw.text((185, 383), "OVERDUE", font=FONT, fill=RED)

    # "QUIET PLEASE" sign on wall
    draw_framed_text(draw, 310, 60, "QUIET\nPLEASE", w=80, h=50)

    # Clock on wall
    draw_clock(draw, 240, 60)


def _scene_rocket_launchpad(draw, post):
    """Rocket launchpad scene — Spidey strapped to a shuttle nose cone."""
    # Night sky
    draw.rectangle([0, 0, 640, 480], fill=(15, 15, 40))

    # Stars
    for _ in range(60):
        sx = random.randint(0, 640)
        sy = random.randint(0, 300)
        sr = random.randint(1, 3)
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=WHITE)

    # Earth curve at bottom
    draw.ellipse([50, 380, 590, 600], fill=(40, 120, 80), outline=(30, 100, 60), width=3)
    # Ocean patches
    draw.ellipse([150, 400, 300, 480], fill=(40, 80, 180))
    draw.ellipse([350, 390, 500, 470], fill=(40, 80, 180))

    # Launch pad — flat gray platform
    draw.rectangle([220, 360, 420, 385], fill=GRAY, outline=DARK_GRAY, width=2)
    # Support structure
    draw.rectangle([230, 200, 260, 360], fill=DARK_GRAY, outline=BLACK, width=2)
    for gy in range(210, 360, 20):
        draw.line([(230, gy), (290, gy)], fill=GRAY, width=1)

    # Rocket body
    rx, ry = 330, 120
    rw, rh = 40, 240
    draw.rectangle([rx - rw//2, ry, rx + rw//2, ry + rh], fill=WHITE, outline=DARK_GRAY, width=2)
    # Red stripe
    draw.rectangle([rx - rw//2, ry + 60, rx + rw//2, ry + 80], fill=RED)
    # Blue stripe
    draw.rectangle([rx - rw//2, ry + 100, rx + rw//2, ry + 120], fill=BLUE)
    # USA text
    draw.text((rx - 12, ry + 140), "USA", font=FONT, fill=BLUE)
    # Nose cone
    draw.polygon([(rx - rw//2, ry), (rx, ry - 50), (rx + rw//2, ry)],
                 fill=RED, outline=DARK_GRAY, width=2)
    # Fins at bottom
    draw.polygon([(rx - rw//2, ry + rh - 30), (rx - rw//2 - 20, ry + rh), (rx - rw//2, ry + rh)],
                 fill=RED, outline=BLACK, width=1)
    draw.polygon([(rx + rw//2, ry + rh - 30), (rx + rw//2 + 20, ry + rh), (rx + rw//2, ry + rh)],
                 fill=RED, outline=BLACK, width=1)
    # Window
    draw.ellipse([rx - 8, ry + 30, rx + 8, ry + 46], fill=LIGHT_BLUE, outline=DARK_GRAY, width=2)

    # Spidey strapped to nose cone tip
    draw_spidey(draw, rx, ry - 35, size=14, expression="alarmed")
    # Tiny helmet
    draw.arc([rx - 10, ry - 48, rx + 10, ry - 32], start=180, end=0, fill=WHITE, width=2)

    # Flames coming from bottom
    for _ in range(25):
        fx = random.randint(rx - 25, rx + 25)
        fy = random.randint(ry + rh, ry + rh + 80)
        fr = random.randint(5, 15)
        fc = random.choice([BRIGHT_ORANGE, YELLOW, RED, LAVA_ORANGE])
        spray_paint(draw, fx, fy, fr, fc, density=0.5)

    # American flag planted near launchpad
    flag_x = 180
    draw.line([(flag_x, 340), (flag_x, 375)], fill=DARK_GRAY, width=2)
    draw.rectangle([flag_x, 340, flag_x + 22, 352], fill=RED)
    draw.rectangle([flag_x, 346, flag_x + 8, 352], fill=BLUE)
    # Stripes
    draw.line([(flag_x, 344), (flag_x + 22, 344)], fill=WHITE, width=1)
    draw.line([(flag_x, 348), (flag_x + 22, 348)], fill=WHITE, width=1)

    # Countdown chalkboard
    draw.rectangle([440, 300, 530, 350], fill=(30, 50, 30), outline=BROWN, width=2)
    draw.text((460, 310), "T - 0", font=FONT, fill=WHITE)
    draw.text((450, 330), "LAUNCH!", font=FONT, fill=YELLOW)


def _scene_bowling_alley(draw, post):
    """Bowling alley scene — Spidey rolled over by a bowling ball."""
    # Dark walls
    draw.rectangle([0, 0, 640, 480], fill=(30, 30, 80))

    # Neon-lit ceiling strip
    draw.rectangle([0, 0, 640, 30], fill=NAVY)
    for nx in range(0, 640, 40):
        c = random.choice([RED, BLUE, PURPLE, PINK])
        draw.rectangle([nx, 5, nx + 30, 25], fill=c, outline=None)

    # Lane — long tan rectangle stretching into distance
    lane_left = 200
    lane_right = 440
    draw.rectangle([lane_left, 50, lane_right, 480], fill=FLOOR_TAN, outline=DARK_BROWN, width=2)
    # Lane lines
    draw.line([(lane_left + 10, 50), (lane_left + 10, 480)], fill=DARK_BROWN, width=1)
    draw.line([(lane_right - 10, 50), (lane_right - 10, 480)], fill=DARK_BROWN, width=1)
    # Lane arrows
    for ay in range(300, 380, 25):
        draw.polygon([(320, ay), (315, ay + 15), (325, ay + 15)], fill=RED)

    # Gutters
    draw.rectangle([lane_left - 20, 50, lane_left, 480], fill=DARK_GRAY, outline=BLACK, width=1)
    draw.rectangle([lane_right, 50, lane_right + 20, 480], fill=DARK_GRAY, outline=BLACK, width=1)

    # Pins at far end — triangle formation
    pin_y = 80
    pin_positions = [
        (320, pin_y),
        (310, pin_y + 20), (330, pin_y + 20),
        (300, pin_y + 40), (320, pin_y + 40), (340, pin_y + 40),
        (290, pin_y + 60), (310, pin_y + 60), (330, pin_y + 60), (350, pin_y + 60),
    ]
    for px, py in pin_positions:
        # Pin body
        draw.ellipse([px - 5, py - 3, px + 5, py + 10], fill=WHITE, outline=BLACK, width=1)
        # Red stripe
        draw.line([(px - 4, py + 2), (px + 4, py + 2)], fill=RED, width=2)

    # Spidey in the middle of the lane, facing pins
    draw_spidey(draw, 320, 260, size=18, expression="surprised")

    # Bowling ball rolling toward Spidey from foreground
    ball_y = 400
    draw.ellipse([300, ball_y - 20, 340, ball_y + 20], fill=BLACK, outline=DARK_GRAY, width=3)
    # Finger holes
    draw.ellipse([312, ball_y - 10, 318, ball_y - 4], fill=DARK_GRAY)
    draw.ellipse([322, ball_y - 10, 328, ball_y - 4], fill=DARK_GRAY)
    draw.ellipse([317, ball_y - 2, 323, ball_y + 4], fill=DARK_GRAY)

    # Motion lines behind ball
    for ml in range(3):
        my = ball_y + 25 + ml * 8
        draw.line([(305, my), (335, my)], fill=LIGHT_GRAY, width=2)

    # Scoreboard above
    draw.rectangle([220, 35, 420, 60], fill=BLACK, outline=DARK_GRAY, width=2)
    draw.text((240, 40), "300 - SPIDEY", font=FONT, fill=GREEN)

    # Shoe rack in corner
    draw.rectangle([30, 300, 130, 400], fill=BROWN, outline=DARK_BROWN, width=2)
    for sy in range(310, 390, 20):
        draw.line([(35, sy), (125, sy)], fill=DARK_BROWN, width=1)
    # Tiny shoe
    draw.rectangle([50, 365, 75, 380], fill=RED, outline=BLACK, width=1)
    draw.text((52, 367), "1/2", font=FONT, fill=WHITE)


def _scene_generic_indoor(draw, post):
    """Fallback indoor scene with decent detail."""
    draw_room(draw, wall_color=WALL_YELLOW, floor_color=FLOOR_TAN, floor_y=390)

    # Table
    draw.rectangle([180, 300, 460, 325], fill=BROWN, outline=DARK_BROWN, width=2)
    draw.rectangle([195, 325, 215, 390], fill=BROWN)
    draw.rectangle([425, 325, 445, 390], fill=BROWN)

    # Window on wall
    draw.rectangle([400, 60, 540, 180], fill=SKY_BLUE, outline=BLACK, width=3)
    draw.line([(470, 60), (470, 180)], fill=BLACK, width=2)
    draw.line([(400, 120), (540, 120)], fill=BLACK, width=2)

    # Potted plant
    draw_potted_plant(draw, 100, 340)

    # Clock
    draw_clock(draw, 300, 80)

    # Picture on wall
    draw_framed_picture(draw, 120, 80, w=100, h=80, content="landscape")

    # Spider on table
    draw_spidey(draw, 320, 285, size=16, expression="surprised")

    # Bookshelf
    draw.rectangle([20, 120, 80, 280], fill=DARK_BROWN, outline=BLACK, width=2)
    for sy in range(130, 270, 35):
        draw.line([(25, sy), (75, sy)], fill=BROWN, width=2)
        # Books
        for bx in range(27, 73, 10):
            c = random.choice([RED, BLUE, DARK_GREEN, PURPLE, BROWN])
            draw.rectangle([bx, sy + 3, bx + 8, sy + 30], fill=c, outline=BLACK, width=1)

    draw_framed_text(draw, 250, 150, "LIVE\nLAUGH\nLOVE", w=80, h=55)


def _scene_generic_outdoor(draw, post):
    """Generic outdoor fallback — simple park/field scene."""
    draw_sky(draw)
    draw_sun(draw, x=560, y=60)
    draw_ground(draw, y=340, grass=True)

    # A tree
    draw_tree(draw, 100, 340)

    # A path
    draw.polygon([(280, 340), (360, 340), (400, 480), (240, 480)],
                 fill=SAND_YELLOW, outline=DARK_BROWN, width=1)

    # Bench
    draw.rectangle([420, 310, 550, 325], fill=BROWN, outline=DARK_BROWN, width=2)
    draw.rectangle([430, 325, 445, 340], fill=BROWN)
    draw.rectangle([535, 325, 550, 340], fill=BROWN)

    # Flowers
    for fx in [460, 500, 540]:
        draw_flower(draw, fx, 335, color=random.choice([RED, PINK, YELLOW, PURPLE]))

    # Spidey on the path
    draw_spidey(draw, 320, 360, size=20, expression="surprised")

    # Sign
    hidden = post.get("hidden_touch", "")
    sign_text = _extract_sign_text(hidden)
    draw_framed_text(draw, 180, 280, sign_text, w=80, h=45)


def _extract_sign_text(hidden_touch):
    """Try to pull a short sign text from the hidden touch description."""
    match = re.search(r"['\"]([^'\"]+)['\"]", hidden_touch)
    if match:
        text = match.group(1)
        if len(text) > 15:
            words = text.split()
            mid = len(words) // 2
            return " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
        return text
    match = re.search(r"(?:says|reads)\s+['\"]?(.+?)(?:['\"]|$|,)", hidden_touch)
    if match:
        return match.group(1).strip()
    return "Home Sweet\nHome"


# ===========================================================================
# Main
# ===========================================================================

def render_batch(batch_path, index=None):
    """Render images for a batch of drafts."""
    with open(batch_path) as f:
        posts = json.load(f)

    output_dir = Path(batch_path).parent
    rendered = []

    items = [(index, posts[index])] if index is not None else enumerate(posts)

    for i, post in items:
        random.seed(hash(json.dumps(post, sort_keys=True)))  # deterministic per post
        img = render_scene(post)
        filename = f"draft_{i + 1}_{post.get('setting', 'scene').replace(' ', '_')}.png"
        filepath = output_dir / filename
        img.save(filepath)
        rendered.append(filepath)
        print(f"  Rendered: {filepath}")

    return rendered


def main():
    parser = argparse.ArgumentParser(description="Render Spider Death Blog illustrations")
    parser.add_argument("batch_file", help="Path to a batch JSON file in drafts/")
    parser.add_argument("--index", type=int, default=None, help="Render only the draft at this index (0-based)")
    args = parser.parse_args()

    if not os.path.exists(args.batch_file):
        print(f"Error: {args.batch_file} not found")
        sys.exit(1)

    print("Rendering illustrations...")
    rendered = render_batch(args.batch_file, index=args.index)
    print(f"\nDone! Rendered {len(rendered)} image(s).")


if __name__ == "__main__":
    main()
