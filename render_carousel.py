#!/usr/bin/env python3
"""Render a carousel spec (JSON) to a 1200x1500 PDF plus a cover PNG.

Type and color come from docs/02-visual-design-system.md. Nothing here invents a
palette or a font.

Usage:
    python3 render_carousel.py carousels/a-adoption.json
"""

import base64
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
FONTS = ROOT / "assets" / "fonts"
BUILD = ROOT / "build"

# Palette -- file 02
COLORS = {
    "ink": "#111418",
    "muted": "#8A8F98",
    "accent": "#2F6FEB",
    "paper": "#F5F3EE",
    "tint": "#EAE7E0",
    "band": "#DFE7F8",
    "line": "#D6D3CC",
    "panelline": "#2A2F36",
}

# Chrome binary. Override with CHROME_PATH on Linux or a non-default install.
CHROME = os.environ.get(
    "CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# Frame is 1200x1500. A carousel is read at roughly a third of its native size
# on a phone, so sizes are set for the canvas. See "Carousel scale" in file 02.
SCALE = {
    "display": 116,
    "head": 72,
    "stat": 240,
    "body": 34,
    "eyebrow": 24,
    "micro": 20,
}


def font_face(name, path, weight="100 900"):
    data = base64.b64encode((FONTS / path).read_bytes()).decode()
    return (
        f"@font-face{{font-family:'{name}';font-weight:{weight};font-style:normal;"
        f"src:url(data:font/ttf;base64,{data}) format('truetype');}}"
    )


def css():
    return f"""
{font_face('Display', 'PlayfairDisplay.ttf')}
{font_face('Sans', 'Inter.ttf')}

@page {{ size: 12.5in 15.625in; margin: 0; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

.frame {{
  width: 1200px; height: 1500px;
  padding: 110px 100px;
  position: relative;
  display: flex; flex-direction: column; justify-content: center;
  background: {COLORS['paper']};
  font-variant-numeric: lining-nums;
  page-break-after: always;
  overflow: hidden;
}}
.frame:last-child {{ page-break-after: auto; }}
.frame.tint  {{ background: {COLORS['tint']}; }}
.frame.band  {{ background: {COLORS['band']}; }}
.frame.panel {{ background: {COLORS['ink']}; }}

/* Eyebrow -- on every frame. The recognizable unit is eyebrow, then serif. */
.eyebrow {{
  position: absolute; top: 110px; left: 100px;
  font-family: Sans; font-weight: 600; font-size: {SCALE['eyebrow']}px;
  text-transform: uppercase; letter-spacing: 1.8px;
  color: {COLORS['muted']};
}}
.panel .eyebrow {{ color: {COLORS['accent']}; }}

/* Hierarchy comes from size and font-switching, never from bolding. */
.display {{
  font-family: Display; font-weight: 400; font-size: {SCALE['display']}px;
  line-height: 1.08; letter-spacing: 0.25px; color: {COLORS['ink']};
}}
.head {{
  font-family: Display; font-weight: 400; font-size: {SCALE['head']}px;
  line-height: 1.2; letter-spacing: 0.25px; color: {COLORS['ink']};
}}
.panel .display, .panel .head {{ color: {COLORS['paper']}; }}

.stat {{
  font-family: Display; font-weight: 400; font-size: {SCALE['stat']}px;
  line-height: 1.0; letter-spacing: -0.25px; color: {COLORS['accent']};
}}
.label {{
  font-family: Sans; font-weight: 400; font-size: 38px;
  line-height: 1.45; letter-spacing: 0.2px; color: {COLORS['ink']};
  margin-top: 44px; max-width: 880px;
}}
.body {{
  font-family: Sans; font-weight: 400; font-size: {SCALE['body']}px;
  line-height: 1.5; letter-spacing: 0.2px; color: {COLORS['muted']};
  margin-top: 40px; max-width: 820px;
}}
.panel .body, .panel .label {{ color: {COLORS['tint']}; }}

.spacer {{ flex: 1; }}

.rule {{ height: 1px; background: {COLORS['line']}; margin-top: 56px; }}
.panel .rule {{ background: {COLORS['panelline']}; }}

/* Frame counter -- micro label, bottom left */
.counter {{
  position: absolute; left: 100px; bottom: 90px;
  font-family: Sans; font-weight: 500; font-size: {SCALE['micro']}px;
  text-transform: uppercase; letter-spacing: 1.5px; color: {COLORS['muted']};
}}
"""


def render_frame(frame, index, total):
    bg = frame.get("bg", "paper")
    if bg not in ("paper", "tint", "band", "panel"):
        sys.exit(f"Unknown bg: {bg}. Use paper, tint, band or panel (file 02).")
    parts = [f'<div class="frame {bg}">']
    parts.append(f'<div class="eyebrow">{frame["eyebrow"]}</div>')

    kind = frame["type"]
    if kind == "display":
        parts.append(f'<div class="display">{frame["text"]}</div>')
    elif kind == "head":
        parts.append(f'<div class="head">{frame["text"]}</div>')
        if frame.get("body"):
            parts.append(f'<div class="body">{frame["body"]}</div>')
    elif kind == "stat":
        parts.append(f'<div class="stat">{frame["stat"]}</div>')
        parts.append(f'<div class="label">{frame["text"]}</div>')
    else:
        sys.exit(f"Unknown frame type: {kind}")

    parts.append(f'<div class="counter">{index:02d} / {total:02d}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def build_html(spec):
    frames = spec["frames"]
    total = len(frames)
    if total not in (4, 6):
        sys.exit(f"Carousels are 4 or 6 frames. This spec has {total}.")

    for i, f in enumerate(frames, 1):
        words = len(" ".join([f.get("text", ""), f.get("body", ""), f.get("stat", "")]).split())
        if words > 18:
            sys.exit(f"Frame {i} has {words} words. Max is 18.")

    body = "\n".join(render_frame(f, i, total) for i, f in enumerate(frames, 1))
    return f"<!doctype html><meta charset='utf-8'><style>{css()}</style>{body}"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    slug = spec["slug"]

    BUILD.mkdir(exist_ok=True)
    html_path = BUILD / f"{slug}.html"
    pdf_path = BUILD / f"{slug}.pdf"
    html_path.write_text(build_html(spec))

    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True,
    )

    # Cover image, for the Buffer document thumbnail
    png_path = BUILD / f"{slug}-cover.png"
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--window-size=1200,1500",
         "--default-background-color=F5F3EEFF",
         f"--screenshot={png_path}", html_path.as_uri()],
        check=True, capture_output=True,
    )

    print(f"{pdf_path}  ({len(spec['frames'])} frames)")
    print(f"{png_path}")


if __name__ == "__main__":
    main()
