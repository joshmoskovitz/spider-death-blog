#!/usr/bin/env python3
"""
Spider Death Blog — Static Site Generator

Builds a lightweight static website from archive posts and new drafts.
Navigation works exactly like xkcd: first / prev / random / next / last.

Usage:
    python3 build_site.py          # build to site/
    python3 build_site.py --serve  # build and start local server
"""

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
SITE_DIR = PROJECT_DIR / "site"
ARCHIVE_PATH = PROJECT_DIR / "archive" / "posts.json"
ARCHIVE_IMAGES = PROJECT_DIR / "archive" / "images"
DRAFTS_DIR = PROJECT_DIR / "drafts"

API_URL = os.environ.get("API_URL", "http://localhost:8888")


def load_all_posts():
    """Load archive posts + new drafts into a unified numbered list."""
    posts = []

    # Archive posts (originals from Tumblr)
    with open(ARCHIVE_PATH) as f:
        archive = json.load(f)
    for p in archive:
        posts.append({
            "id": p["id"],
            "date": p.get("date", "2012-02-14"),
            "setting": p["setting"],
            "mechanism": p["mechanism"],
            "intro": p.get("intro", ""),
            "caption": p["caption"],
            "hashtags": p.get("hashtags", ""),
            "hidden_touch": p.get("hidden_touch", ""),
            "image_src": p["image"],
            "image_origin": "archive",
            "era": "classic",
        })

    # New drafts — use only the latest batch file (most recent generation)
    # Skip any drafts already in the archive (by setting name)
    archived_settings = {p["setting"].lower() for p in posts}
    next_id = max(p["id"] for p in posts) + 1
    batch_files = sorted(DRAFTS_DIR.glob("batch_*.json"))
    if batch_files:
        batch_file = batch_files[-1]  # latest
        with open(batch_file) as f:
            drafts = json.load(f)
        for i, d in enumerate(drafts):
            setting_slug = d.get("setting", "scene").replace(" ", "_")
            # Skip already-archived posts
            if d.get("setting", "").lower() in archived_settings:
                continue
            # Find matching rendered image
            draft_num = i + 1
            png_name = f"draft_{draft_num}_{setting_slug}.png"
            png_path = DRAFTS_DIR / png_name
            if not png_path.exists():
                continue  # skip drafts without rendered images

            posts.append({
                "id": next_id,
                "date": batch_file.stem.replace("batch_", "")[:8],  # YYYYMMDD
                "setting": d.get("setting", "?"),
                "mechanism": d.get("mechanism", "?"),
                "intro": d.get("intro", ""),
                "caption": d.get("caption", ""),
                "hashtags": d.get("hashtags", ""),
                "hidden_touch": d.get("hidden_touch", ""),
                "image_src": png_name,
                "image_origin": "drafts",
                "era": "new",
            })
            next_id += 1

    # Sort by id
    posts.sort(key=lambda p: p["id"])
    return posts


def format_date(date_str):
    """Format date string for display."""
    try:
        if len(date_str) == 8 and date_str.isdigit():
            dt = datetime.strptime(date_str, "%Y%m%d")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except ValueError:
        return date_str


def make_title(post):
    """Generate a title from the setting."""
    setting = post["setting"]
    return setting.title()


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: "Lucida Console", "Courier New", monospace;
    background: #fff;
    color: #333;
    max-width: 780px;
    margin: 0 auto;
    padding: 10px 20px;
}

/* Header */
#header {
    text-align: center;
    padding: 15px 0 5px;
    border-bottom: 1px solid #ccc;
    margin-bottom: 10px;
}
#header h1 {
    font-size: 22px;
    letter-spacing: 1px;
    margin-bottom: 2px;
}
#header h1 a {
    color: #333;
    text-decoration: none;
}
#header .tagline {
    font-size: 11px;
    color: #888;
    font-style: italic;
}

/* Top nav links */
#topnav {
    text-align: center;
    padding: 6px 0;
    font-size: 13px;
    border-bottom: 1px solid #eee;
    margin-bottom: 15px;
}
#topnav a {
    color: #666;
    text-decoration: none;
    margin: 0 12px;
}
#topnav a:hover { color: #000; text-decoration: underline; }

/* Comic display */
#comic {
    text-align: center;
    padding: 10px 0;
}
#comic .intro {
    font-size: 14px;
    color: #555;
    margin-bottom: 12px;
    font-style: italic;
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.5;
}
#comic img {
    max-width: 100%;
    border: 1px solid #ddd;
    image-rendering: pixelated;
}
#comic .caption {
    font-size: 14px;
    color: #333;
    margin-top: 12px;
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.5;
}
#comic .hashtags {
    font-size: 11px;
    color: #999;
    margin-top: 6px;
}
#comic .date {
    font-size: 11px;
    color: #aaa;
    margin-top: 4px;
}
#comic .post-number {
    font-size: 11px;
    color: #bbb;
    margin-top: 2px;
}

/* Comic navigation */
#comicnav {
    text-align: center;
    padding: 12px 0;
    font-size: 14px;
}
#comicnav a, #comicnav span {
    display: inline-block;
    margin: 0 8px;
    padding: 4px 12px;
    border: 1px solid #ccc;
    color: #666;
    text-decoration: none;
    min-width: 70px;
}
#comicnav a:hover {
    background: #f0f0f0;
    color: #000;
}
#comicnav span.disabled {
    color: #ccc;
    border-color: #eee;
}

/* Archive page */
#archive {
    padding: 10px 0;
}
#archive h2 {
    font-size: 18px;
    margin-bottom: 15px;
    text-align: center;
}
#archive .era-label {
    font-size: 13px;
    color: #999;
    margin: 15px 0 5px;
    border-bottom: 1px solid #eee;
    padding-bottom: 3px;
}
#archive ul {
    list-style: none;
    padding: 0;
}
#archive li {
    padding: 3px 0;
    font-size: 13px;
}
#archive li a {
    color: #336;
    text-decoration: none;
}
#archive li a:hover { text-decoration: underline; }
#archive li .archive-date {
    color: #999;
    font-size: 11px;
    margin-left: 8px;
}

/* About page */
#about {
    padding: 10px 0;
    line-height: 1.7;
    font-size: 13px;
}
#about h2 {
    font-size: 18px;
    margin-bottom: 15px;
    text-align: center;
}

/* Footer */
#footer {
    text-align: center;
    padding: 15px 0;
    margin-top: 20px;
    border-top: 1px solid #ccc;
    font-size: 10px;
    color: #aaa;
}
"""

JS = """
function goToRandom() {
    var total = document.getElementById('comicnav').dataset.total;
    var num = Math.floor(Math.random() * total) + 1;
    window.location.href = '/' + num + '/';
}
"""


def render_page(title, body_html, posts_total=0):
    """Wrap body HTML in the full page template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Spider Death Blog</title>
<style>{CSS}</style>
<link rel="icon" href="/images/favicon.png" type="image/png">
</head>
<body>

<div id="header">
  <h1><a href="/">Spider Death Blog</a></h1>
  <div class="tagline">a small spider who dies in whimsical, theatrical ways</div>
</div>

<div id="topnav">
  <a href="/archive/">Archive</a>
  <a href="/create/">Create</a>
  <a href="/community/">Community</a>
  <a href="/about/">About</a>
</div>

{body_html}

<div id="footer">
  Spider Death Blog &middot; Est. 2012 &middot; Powered by MS Paint and cruelty<br>
  Best viewed with 8 legs or fewer
</div>

<script>{JS}</script>
</body>
</html>"""


def render_comic_page(post, posts, total):
    """Render a single comic page with xkcd-style navigation."""
    pid = post["id"]
    title = make_title(post)

    # Navigation links
    first_link = f'<a href="/1/">&lt;&lt; First</a>' if pid > 1 else '<span class="disabled">&lt;&lt; First</span>'
    prev_link = f'<a href="/{pid - 1}/">&lt; Prev</a>' if pid > 1 else '<span class="disabled">&lt; Prev</span>'
    random_link = '<a href="#" onclick="goToRandom(); return false;">Random</a>'
    next_link = f'<a href="/{pid + 1}/">Next &gt;</a>' if pid < total else '<span class="disabled">Next &gt;</span>'
    last_link = f'<a href="/{total}/">Last &gt;&gt;</a>' if pid < total else '<span class="disabled">Last &gt;&gt;</span>'

    # Intro (if available)
    intro_html = ""
    if post.get("intro"):
        intro_html = f'<div class="intro">{post["intro"]}</div>'

    # Image
    img_html = f'<img src="/images/{post["image_src"]}" alt="{title}" title="{post.get("hidden_touch", "")}">'

    body = f"""
<div id="comicnav" data-total="{total}">
  {first_link} {prev_link} {random_link} {next_link} {last_link}
</div>

<div id="comic">
  {intro_html}
  {img_html}
  <div class="caption">{post["caption"]}</div>
  <div class="hashtags">{post.get("hashtags", "")}</div>
  <div class="date">{format_date(post["date"])}</div>
  <div class="post-number">#{pid}</div>
</div>

<div id="comicnav" data-total="{total}">
  {first_link} {prev_link} {random_link} {next_link} {last_link}
</div>
"""
    return render_page(f"#{pid}: {title}", body, total)


def render_archive_page(posts):
    """Render the archive page — reverse chronological list."""
    classic = [p for p in posts if p["era"] == "classic"]
    new = [p for p in posts if p["era"] == "new"]

    items_html = ""

    if new:
        items_html += '<div class="era-label">New Episodes</div>\n<ul>\n'
        for p in reversed(new):
            items_html += f'<li><a href="/{p["id"]}/">#{p["id"]}: {make_title(p)}</a><span class="archive-date">{format_date(p["date"])}</span></li>\n'
        items_html += '</ul>\n'

    items_html += '<div class="era-label">Classic Archive (2012)</div>\n<ul>\n'
    for p in reversed(classic):
        items_html += f'<li><a href="/{p["id"]}/">#{p["id"]}: {make_title(p)}</a><span class="archive-date">{format_date(p["date"])}</span></li>\n'
    items_html += '</ul>\n'

    body = f"""
<div id="archive">
  <h2>Archive</h2>
  {items_html}
</div>
"""
    return render_page("Archive", body)


def render_about_page():
    """Render the about page."""
    body = """
<div id="about">
  <h2>About</h2>
  <p>
    <strong>Spider Death Blog</strong> is a blog about a small, sympathetic, slightly pathetic
    spider named Spidey who dies in whimsical, theatrical ways.
  </p>
  <p>
    Each post features a crude MS Paint illustration of Spidey's demise, accompanied by a
    deadpan first-person confession of how it happened. The humor lives in the contrast
    between the playful, punny setup and the matter-of-fact description of a very tiny murder.
  </p>
  <p>
    The blog started in February 2012 on Tumblr with 9 original posts. It has recently
    returned with new episodes, still drawn in the same lovingly crude MS Paint style
    on a 640x480 canvas.
  </p>
  <p>
    Spidey is not menacing. He is not monstrous. He is just a small gray oval with
    stick legs and dot eyes, caught mid-routine when doom strikes.
  </p>
  <p style="margin-top: 20px; color: #999; font-size: 11px;">
    Original blog: <a href="https://www.tumblr.com/spiderdeaths-blog" style="color:#669">spiderdeaths-blog.tumblr.com</a>
  </p>
</div>
"""
    return render_page("About", body)


def render_create_page():
    """Render the Create Your Own Spider Death page."""
    body = """
<div id="create">
  <h2>Create Your Own Spider Death</h2>
  <p class="create-intro">
    How should Spidey meet his end this time? Describe it in a few words and
    our MS Paint department will handle the rest.
  </p>

  <div class="create-form">
    <input type="text" id="phrase-input"
           placeholder="e.g. crushed by a piano, eaten by a roomba..."
           maxlength="120"
           autocomplete="off">
    <button id="generate-btn" onclick="generateDeath()">Generate</button>
  </div>
  <div class="char-count"><span id="char-count">0</span>/120</div>

  <div id="loading" style="display:none;">
    <div class="loading-spider">
      <canvas id="loading-canvas" width="500" height="200"></canvas>
      <p class="loading-text">Spidey is contemplating his fate...</p>
    </div>
  </div>

  <div id="error-msg" style="display:none;"></div>

  <div id="result" style="display:none;">
    <div id="comic">
      <div class="intro" id="result-intro"></div>
      <img id="result-image" alt="Your custom spider death" style="image-rendering: pixelated;">
      <div class="caption" id="result-caption"></div>
      <div class="hashtags" id="result-hashtags"></div>
    </div>
    <div class="create-actions">
      <button onclick="tryAgain()">Try Another</button>
      <button onclick="downloadImage()">Save Image</button>
      <button id="community-btn" onclick="addToCommunityBoard()">Add to Community Board</button>
    </div>
  </div>
</div>

<style>
#create { text-align: center; padding: 10px 0; }
#create h2 { font-size: 18px; margin-bottom: 10px; }
.create-intro {
  font-size: 13px; color: #666; max-width: 460px;
  margin: 0 auto 20px; line-height: 1.5;
}
.create-form {
  display: flex; justify-content: center; gap: 8px;
  max-width: 500px; margin: 0 auto;
}
.create-form input {
  flex: 1; padding: 8px 12px; font-size: 14px;
  font-family: "Lucida Console", "Courier New", monospace;
  border: 2px solid #ccc; outline: none;
}
.create-form input:focus { border-color: #888; }
.create-form button, .create-actions button {
  padding: 8px 18px; font-size: 13px;
  font-family: "Lucida Console", "Courier New", monospace;
  background: #333; color: #fff; border: none; cursor: pointer;
}
.create-form button:hover, .create-actions button:hover { background: #555; }
.create-form button:disabled { background: #aaa; cursor: not-allowed; }
.char-count {
  font-size: 10px; color: #bbb; margin-top: 4px;
  text-align: right; max-width: 500px; margin-left: auto; margin-right: auto;
}
.loading-spider { padding: 20px 0; }
#loading-canvas {
  display: block; margin: 0 auto;
  image-rendering: pixelated;
  max-width: 100%;
}
.loading-text {
  font-size: 13px; color: #888; font-style: italic;
  margin-top: 6px;
}
#error-msg {
  max-width: 460px; margin: 20px auto; padding: 10px;
  font-size: 13px; color: #c33; border: 1px solid #ecc;
  background: #fef0f0;
}
#result img { max-width: 100%; border: 1px solid #ddd; margin-top: 12px; }
.create-actions {
  display: flex; justify-content: center; gap: 10px;
  margin-top: 15px;
}
</style>

<script>
var API_URL = '{api_url}';
var animFrameId = null;
var lastResult = null;
var lastPhrase = null;

var phraseInput = document.getElementById('phrase-input');
phraseInput.addEventListener('input', function() {
  document.getElementById('char-count').textContent = this.value.length;
});
phraseInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') generateDeath();
});

/* =======================================================================
   Spidey-dodging-knives loading animation (canvas)
   ======================================================================= */

function startLoadingAnimation() {
  var canvas = document.getElementById('loading-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height;

  // Spidey state
  var spidey = { x: W / 2, targetX: W / 2, y: H - 40, legPhase: 0, expression: 0 };
  // Knives
  var knives = [];
  var knifeTimer = 0;
  // Puffs where knives land
  var puffs = [];

  function spawnKnife() {
    knives.push({
      x: 40 + Math.random() * (W - 80),
      y: -30,
      speed: 1.8 + Math.random() * 2.2,
      rotation: -0.3 + Math.random() * 0.6,
      wobble: Math.random() * Math.PI * 2
    });
  }

  function drawSpidey(ctx, cx, cy, size, legPhase, expr) {
    var bodyW = size;
    var bodyH = size * 0.75;
    var legLen = size * 2.0;
    var legW = Math.max(2, size / 5);
    var angles = [-55, -20, 18, 48];

    // Legs — animate with a walk cycle
    ctx.strokeStyle = '#000';
    ctx.lineWidth = legW;
    ctx.lineCap = 'round';
    for (var side = -1; side <= 1; side += 2) {
      for (var i = 0; i < angles.length; i++) {
        var swing = Math.sin(legPhase + i * 1.2 + (side > 0 ? Math.PI : 0)) * 12;
        var aRad = (angles[i] + swing) * Math.PI / 180;
        var ax = cx + side * (bodyW - 2);
        var ay = cy + bodyH * 0.3 * (i - 1.5) / 1.5;
        var tx = ax + side * legLen * Math.cos(aRad);
        var ty = ay + legLen * Math.sin(aRad);
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(tx, ty);
        ctx.stroke();
      }
    }

    // Body
    ctx.fillStyle = '#969696';
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(2, size / 7);
    ctx.beginPath();
    ctx.ellipse(cx, cy, bodyW, bodyH, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Eyes
    var eyeSize = Math.max(3, size / 3.2);
    var eyeY = cy - bodyH / 4;
    var lx = cx - bodyW / 3, rx = cx + bodyW / 3;
    for (var ei = 0; ei < 2; ei++) {
      var ex = ei === 0 ? lx : rx;
      ctx.fillStyle = '#fff';
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.ellipse(ex, eyeY, eyeSize, eyeSize, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      // Pupil — look toward nearest knife
      var pupilOff = expr * 1.5;
      ctx.fillStyle = '#000';
      ctx.beginPath();
      ctx.ellipse(ex + pupilOff, eyeY - 1, eyeSize / 2.2, eyeSize / 2.2, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    // Mouth — alarmed O
    var my = cy + bodyH / 3;
    var mw = Math.max(3, size / 4);
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.ellipse(cx, my, mw, mw * 0.6, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawKnife(ctx, x, y, rot) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rot);
    // Handle (on top)
    ctx.fillStyle = '#8B4513';
    ctx.strokeStyle = '#5a2d0c';
    ctx.lineWidth = 1.5;
    ctx.fillRect(-4, -20, 8, 14);
    ctx.strokeRect(-4, -20, 8, 14);
    // Handle rivets
    ctx.fillStyle = '#c8a84e';
    ctx.beginPath();
    ctx.arc(0, -16, 1.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(0, -10, 1.5, 0, Math.PI * 2);
    ctx.fill();
    // Blade (pointing down)
    ctx.fillStyle = '#ccc';
    ctx.strokeStyle = '#888';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(-5, -6);
    ctx.lineTo(5, -6);
    ctx.lineTo(0, 18);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    // Edge highlight
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(-3, -4);
    ctx.lineTo(-1, 14);
    ctx.stroke();
    ctx.restore();
  }

  function drawPuff(ctx, x, y, age) {
    var alpha = Math.max(0, 1 - age / 20);
    var r = 6 + age * 1.5;
    ctx.globalAlpha = alpha * 0.4;
    ctx.fillStyle = '#bbb';
    ctx.beginPath();
    ctx.ellipse(x - 5, y, r, r * 0.5, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(x + 5, y - 2, r * 0.8, r * 0.4, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function drawFloor(ctx) {
    var floorY = H - 18;
    ctx.fillStyle = '#e8dcc8';
    ctx.fillRect(0, floorY, W, H - floorY);
    ctx.strokeStyle = '#c8b8a0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, floorY);
    ctx.lineTo(W, floorY);
    ctx.stroke();
    // Floor tile lines
    ctx.strokeStyle = '#d8ccb8';
    for (var tx = 0; tx < W; tx += 50) {
      ctx.beginPath();
      ctx.moveTo(tx, floorY);
      ctx.lineTo(tx, H);
      ctx.stroke();
    }
  }

  function tick() {
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, W, H);
    drawFloor(ctx);

    // Spawn knives
    knifeTimer++;
    if (knifeTimer > 25 + Math.random() * 20) {
      spawnKnife();
      knifeTimer = 0;
    }

    // Find nearest knife for Spidey to dodge
    var nearestKnifeX = null;
    var nearestDist = 9999;
    for (var ki = 0; ki < knives.length; ki++) {
      var k = knives[ki];
      if (k.y > H * 0.25 && k.y < H - 50) {
        var d = Math.abs(k.x - spidey.x);
        if (d < nearestDist) {
          nearestDist = d;
          nearestKnifeX = k.x;
        }
      }
    }

    // Spidey dodges — pick a new target away from the nearest knife
    if (nearestKnifeX !== null && nearestDist < 80) {
      if (nearestKnifeX > spidey.x) {
        spidey.targetX = Math.max(30, nearestKnifeX - 60 - Math.random() * 40);
      } else {
        spidey.targetX = Math.min(W - 30, nearestKnifeX + 60 + Math.random() * 40);
      }
    } else if (Math.random() < 0.01) {
      spidey.targetX = 60 + Math.random() * (W - 120);
    }

    // Move toward target
    var dx = spidey.targetX - spidey.x;
    var speed = Math.min(Math.abs(dx), 3.5);
    if (Math.abs(dx) > 2) {
      spidey.x += (dx > 0 ? speed : -speed);
      spidey.legPhase += 0.25;
    }
    spidey.expression = (nearestKnifeX !== null && nearestDist < 80)
      ? (nearestKnifeX > spidey.x ? -2 : 2) : 0;

    // Update & draw knives
    for (var i = knives.length - 1; i >= 0; i--) {
      var k = knives[i];
      k.y += k.speed;
      k.wobble += 0.05;
      k.rotation = Math.sin(k.wobble) * 0.15;
      if (k.y >= H - 36) {
        // Stick in the floor
        drawKnife(ctx, k.x, H - 28, 0);
        puffs.push({ x: k.x, y: H - 20, age: 0 });
        knives.splice(i, 1);
      } else {
        drawKnife(ctx, k.x, k.y, k.rotation);
      }
    }

    // Draw & age puffs
    for (var p = puffs.length - 1; p >= 0; p--) {
      drawPuff(ctx, puffs[p].x, puffs[p].y, puffs[p].age);
      puffs[p].age++;
      if (puffs[p].age > 20) puffs.splice(p, 1);
    }

    // Clean up old stuck knives by fading (just limit the array)
    // The stuck knives drawn above get cleared each frame anyway

    // Draw Spidey on top
    drawSpidey(ctx, spidey.x, spidey.y, 16, spidey.legPhase, spidey.expression);

    animFrameId = requestAnimationFrame(tick);
  }

  // Reset state
  knives.length = 0;
  puffs.length = 0;
  knifeTimer = 0;
  spidey.x = W / 2;
  spidey.targetX = W / 2;
  tick();
}

function stopLoadingAnimation() {
  if (animFrameId) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }
}

/* =======================================================================
   Main app logic
   ======================================================================= */

function generateDeath() {
  var phrase = phraseInput.value.trim();
  if (!phrase) return;

  var btn = document.getElementById('generate-btn');
  btn.disabled = true;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('result').style.display = 'none';
  document.getElementById('error-msg').style.display = 'none';
  startLoadingAnimation();

  fetch(API_URL + '/api/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phrase: phrase })
  })
  .then(function(res) {
    if (!res.ok) {
      return res.json().then(function(data) {
        throw new Error(data.error || 'Something went wrong');
      });
    }
    return res.json();
  })
  .then(function(data) {
    lastPhrase = phrase;
    lastResult = data;
    document.getElementById('result-intro').textContent = data.intro;
    document.getElementById('result-image').src = 'data:image/png;base64,' + data.image_base64;
    document.getElementById('result-caption').textContent = data.caption;
    document.getElementById('result-hashtags').textContent = data.hashtags;
    document.getElementById('result').style.display = 'block';
    // Reset the community button for this new result
    var cbtn = document.getElementById('community-btn');
    cbtn.disabled = false;
    cbtn.textContent = 'Add to Community Board';
  })
  .catch(function(err) {
    var errorDiv = document.getElementById('error-msg');
    errorDiv.textContent = err.message;
    errorDiv.style.display = 'block';
  })
  .finally(function() {
    stopLoadingAnimation();
    btn.disabled = false;
    document.getElementById('loading').style.display = 'none';
  });
}

function tryAgain() {
  document.getElementById('result').style.display = 'none';
  phraseInput.value = '';
  phraseInput.focus();
  document.getElementById('char-count').textContent = '0';
}

function downloadImage() {
  var img = document.getElementById('result-image');
  var a = document.createElement('a');
  a.href = img.src;
  a.download = 'spider-death-custom.png';
  a.click();
}

function addToCommunityBoard() {
  if (!lastResult) return;
  var btn = document.getElementById('community-btn');
  btn.disabled = true;
  btn.textContent = 'Adding...';

  fetch(API_URL + '/api/community/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phrase: lastPhrase,
      intro: lastResult.intro,
      caption: lastResult.caption,
      hashtags: lastResult.hashtags,
      image_base64: lastResult.image_base64
    })
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    if (data.id) {
      btn.textContent = 'Added!';
    } else {
      btn.textContent = 'Error — try again';
      btn.disabled = false;
    }
  })
  .catch(function() {
    btn.textContent = 'Error — try again';
    btn.disabled = false;
  });
}
</script>
"""
    return render_page("Create Your Own", body.replace("{api_url}", API_URL))


def render_community_page():
    """Render the Community Board page."""
    body = """
<div id="community">
  <h2>Community Board</h2>
  <p class="community-intro">
    The finest spider deaths, as chosen by the people.
  </p>

  <div id="community-loading">
    <p class="loading-text">Loading the board...</p>
  </div>

  <div id="community-empty" style="display:none;">
    <p class="community-empty-text">
      No deaths yet. Be the first &mdash; <a href="/create/">create one</a> and
      add it to the board!
    </p>
  </div>

  <div id="community-entries"></div>
</div>

<div id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" src="" alt="Enlarged spider death">
</div>

<style>
#lightbox {
  display: none; position: fixed; top: 0; left: 0;
  width: 100%; height: 100%; background: rgba(0,0,0,0.8);
  z-index: 9999; cursor: pointer;
  justify-content: center; align-items: center;
}
#lightbox.active { display: flex; }
#lightbox-img {
  max-width: 90vw; max-height: 90vh;
  image-rendering: pixelated; border: 3px solid #fff;
}
#community { padding: 10px 0; }
#community h2 { font-size: 18px; margin-bottom: 8px; text-align: center; }
.community-intro {
  font-size: 13px; color: #666; text-align: center;
  margin-bottom: 20px;
}
.community-empty-text {
  font-size: 13px; color: #888; text-align: center;
  padding: 40px 0; font-style: italic;
}
.community-empty-text a { color: #336; }

.community-card {
  display: flex; gap: 15px; padding: 14px;
  border: 1px solid #ddd; margin-bottom: 12px;
  max-width: 640px; margin-left: auto; margin-right: auto;
}
.community-card .card-image {
  flex-shrink: 0; width: 140px;
}
.community-card .card-image img {
  width: 140px; border: 1px solid #eee;
  image-rendering: pixelated; cursor: pointer;
}
.community-card .card-image img:hover {
  border-color: #888; opacity: 0.9;
}
.community-card .card-content {
  flex: 1; min-width: 0;
}
.community-card .card-phrase {
  font-size: 13px; color: #999; margin-bottom: 4px;
  font-style: italic;
}
.community-card .card-intro {
  font-size: 13px; color: #555; margin-bottom: 6px;
  font-style: italic; line-height: 1.4;
}
.community-card .card-caption {
  font-size: 13px; color: #333; margin-bottom: 6px;
  line-height: 1.4;
}
.community-card .card-hashtags {
  font-size: 11px; color: #999; margin-bottom: 8px;
}
.community-card .card-votes {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px;
}
.community-card .vote-btn {
  background: none; border: 1px solid #ccc; cursor: pointer;
  padding: 3px 10px; font-size: 16px; line-height: 1;
  font-family: "Lucida Console", "Courier New", monospace;
}
.community-card .vote-btn:hover { background: #f0f0f0; }
.community-card .vote-btn.voted {
  border-color: #888; background: #eee; cursor: default;
}
.community-card .vote-score {
  font-size: 14px; font-weight: bold; color: #333;
  min-width: 30px; text-align: center;
}
.community-card .card-rank {
  font-size: 20px; color: #ccc; font-weight: bold;
  flex-shrink: 0; width: 28px; text-align: right;
  padding-top: 4px;
}
</style>

<script>
var API_URL = '{api_url}';

function loadBoard() {
  fetch(API_URL + '/api/community/board')
    .then(function(res) { return res.json(); })
    .then(function(data) {
      document.getElementById('community-loading').style.display = 'none';
      var entries = data.entries || [];
      if (entries.length === 0) {
        document.getElementById('community-empty').style.display = 'block';
        return;
      }
      var container = document.getElementById('community-entries');
      container.innerHTML = '';
      for (var i = 0; i < entries.length; i++) {
        container.appendChild(renderCard(entries[i], i + 1));
      }
    })
    .catch(function() {
      document.getElementById('community-loading').innerHTML =
        '<p class="loading-text">Could not load the board. Is the API server running?</p>';
    });
}

function renderCard(entry, rank) {
  var card = document.createElement('div');
  card.className = 'community-card';
  var voted = localStorage.getItem('voted_' + entry.id);
  var score = (entry.upvotes || 0) - (entry.downvotes || 0);

  card.innerHTML =
    '<div class="card-rank">' + rank + '</div>' +
    '<div class="card-image">' +
      '<img src="data:image/png;base64,' + entry.image_base64 + '" alt="' + (entry.phrase || '') + '" onclick="openLightbox(this.src, event)">' +
    '</div>' +
    '<div class="card-content">' +
      '<div class="card-phrase">&ldquo;' + escapeHtml(entry.phrase || '') + '&rdquo;</div>' +
      '<div class="card-intro">' + escapeHtml(entry.intro || '') + '</div>' +
      '<div class="card-caption">' + escapeHtml(entry.caption || '') + '</div>' +
      '<div class="card-hashtags">' + escapeHtml(entry.hashtags || '') + '</div>' +
      '<div class="card-votes">' +
        '<button class="vote-btn' + (voted === 'up' ? ' voted' : '') + '" ' +
          'onclick="vote(\\'' + entry.id + '\\', \\'up\\', this)">' +
          '&#x1F44D;' +
        '</button>' +
        '<span class="vote-score" id="score-' + entry.id + '">' + score + '</span>' +
        '<button class="vote-btn' + (voted === 'down' ? ' voted' : '') + '" ' +
          'onclick="vote(\\'' + entry.id + '\\', \\'down\\', this)">' +
          '&#x1F44E;' +
        '</button>' +
      '</div>' +
    '</div>';
  return card;
}

function escapeHtml(str) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function vote(entryId, direction, btn) {
  var previous = localStorage.getItem('voted_' + entryId) || null;
  var newDirection = (previous === direction) ? null : direction;

  fetch(API_URL + '/api/community/vote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entry_id: entryId, direction: newDirection, previous: previous })
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    if (data.score !== undefined) {
      document.getElementById('score-' + entryId).textContent = data.score;
      var card = btn.closest('.community-card');
      var buttons = card.querySelectorAll('.vote-btn');
      // Clear all voted states
      for (var i = 0; i < buttons.length; i++) {
        buttons[i].classList.remove('voted');
      }
      if (newDirection) {
        localStorage.setItem('voted_' + entryId, newDirection);
        btn.classList.add('voted');
      } else {
        localStorage.removeItem('voted_' + entryId);
      }
    }
  });
}

function openLightbox(src, event) {
  event.stopPropagation();
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('active');
}

function closeLightbox() {
  document.getElementById('lightbox').classList.remove('active');
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeLightbox();
});

loadBoard();
</script>
"""
    return render_page("Community Board", body.replace("{api_url}", API_URL))


def render_index_redirect(total):
    """The root index.html redirects to the latest comic."""
    return f"""<!DOCTYPE html>
<html><head>
<meta http-equiv="refresh" content="0;url=/{total}/">
<title>Spider Death Blog</title>
</head><body>
<a href="/{total}/">Latest comic</a>
</body></html>"""


def build_site():
    """Build the complete static site."""
    posts = load_all_posts()
    total = len(posts)
    print(f"Building site with {total} posts...")

    # Clean and create site directory
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir()

    # Create images directory and copy all images
    images_dir = SITE_DIR / "images"
    images_dir.mkdir()

    for post in posts:
        if post["image_origin"] == "archive":
            src = ARCHIVE_IMAGES / post["image_src"]
        else:
            src = DRAFTS_DIR / post["image_src"]

        if src.exists():
            shutil.copy2(src, images_dir / post["image_src"])
        else:
            print(f"  WARNING: Missing image {src}")

    # Build a post lookup by id
    post_by_id = {p["id"]: p for p in posts}

    # Generate comic pages: /1/, /2/, etc.
    for post in posts:
        page_dir = SITE_DIR / str(post["id"])
        page_dir.mkdir()
        html = render_comic_page(post, posts, total)
        (page_dir / "index.html").write_text(html)
        print(f"  #{post['id']}: {make_title(post)}")

    # Generate archive page
    archive_dir = SITE_DIR / "archive"
    archive_dir.mkdir()
    (archive_dir / "index.html").write_text(render_archive_page(posts))
    print(f"  /archive/")

    # Generate create page
    create_dir = SITE_DIR / "create"
    create_dir.mkdir()
    (create_dir / "index.html").write_text(render_create_page())
    print(f"  /create/")

    # Generate community page
    community_dir = SITE_DIR / "community"
    community_dir.mkdir()
    (community_dir / "index.html").write_text(render_community_page())
    print(f"  /community/")

    # Generate about page
    about_dir = SITE_DIR / "about"
    about_dir.mkdir()
    (about_dir / "index.html").write_text(render_about_page())
    print(f"  /about/")

    # Root index redirects to latest
    (SITE_DIR / "index.html").write_text(render_index_redirect(total))
    print(f"  / -> /{total}/")

    print(f"\nSite built: {SITE_DIR}/")
    print(f"  {total} comics, {total} pages + archive + about")
    return total


# Alias for use by daily_pipeline.py
build_all = build_site


def serve(port=8000):
    """Start a local HTTP server for the site."""
    import http.server
    import functools

    os.chdir(SITE_DIR)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE_DIR))
    with http.server.HTTPServer(("", port), handler) as httpd:
        print(f"\nServing at http://localhost:{port}")
        print(f"Latest comic: http://localhost:{port}/")
        print("Press Ctrl+C to stop\n")
        httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Build Spider Death Blog static site")
    parser.add_argument("--serve", action="store_true", help="Start local server after building")
    parser.add_argument("--port", type=int, default=8000, help="Port for local server (default: 8000)")
    args = parser.parse_args()

    build_site()

    if args.serve:
        serve(args.port)


if __name__ == "__main__":
    main()
