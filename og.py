#!/usr/bin/env python3
"""Generate Open Graph share images (1200x630) for every page.

Reads the og:title / og:description already baked into each *.html by build.py,
so the cards always match what is actually published, and this script needs
nothing but Pillow — no imports from build.py, no source markdown. One card per
HTML page lands in og/<slug>.png, referenced by that page's og:image tag.

Run locally or in CI:  python3 og.py
"""

import html
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
FONTS = OUT / "assets" / "fonts"
OGDIR = OUT / "og"
SITE_NAME = "Souhaib Ben Farhat"

W, H = 1200, 630
MARGIN = 92
CW = W - 2 * MARGIN

# palette — the site's dark theme
BG = (23, 24, 26)
INK = (236, 234, 227)
DEK = (176, 175, 167)
MUTED = (139, 138, 130)
RULE = (52, 51, 47)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def meta(source: str, prop: str) -> str:
    m = re.search(rf'<meta property="{prop}" content="([^"]*)"', source)
    return html.unescape(m.group(1)) if m else ""


def wrap(text: str, f: ImageFont.FreeTypeFont, max_w: int) -> list:
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = f"{line} {w}".strip()
        if f.getlength(trial) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def fit(text: str, path: str, max_w: int, max_lines: int, hi: int, lo: int):
    """Largest size at which the title wraps within max_lines."""
    for size in range(hi, lo - 1, -2):
        f = font(path, size)
        lines = wrap(text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    f = font(path, lo)
    return f, wrap(text, f, max_w)[:max_lines]


def line_h(f: ImageFont.FreeTypeFont, leading: float = 1.16) -> int:
    asc, desc = f.getmetrics()
    return int((asc + desc) * leading)


def draw_tracked(d: ImageDraw.ImageDraw, xy, text: str, f, fill, tracking: float) -> None:
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking


def card(title: str, dek: str, eyebrow: str, out_path: Path,
         title_max_lines: int = 3, title_hi: int = 82, title_lo: int = 50) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    sans = font("PTSans-Bold.ttf", 23)
    italic = font("PTSerif-Italic.ttf", 31)

    draw_tracked(d, (MARGIN, 84), eyebrow.upper(), sans, MUTED, tracking=3.5)

    tf, tlines = fit(title, "PTSerif-Bold.ttf", CW, title_max_lines, title_hi, title_lo)
    tlh = line_h(tf)
    dek_lines = wrap(dek, italic, CW)[:3] if dek else []
    dlh = line_h(italic)
    gap = 30 if dek_lines else 0

    block_h = len(tlines) * tlh + gap + len(dek_lines) * dlh
    top = 150 + (390 - block_h) // 2  # center in the middle band

    y = top
    for ln in tlines:
        d.text((MARGIN, y), ln, font=tf, fill=INK)
        y += tlh
    y += gap
    for ln in dek_lines:
        d.text((MARGIN, y), ln, font=italic, fill=DEK)
        y += dlh

    d.line([(MARGIN, 548), (W - MARGIN, 548)], fill=RULE, width=1)
    draw_tracked(d, (MARGIN, 568), "souhaibbenfarhat.github.io/writing", sans, MUTED, tracking=1.0)

    OGDIR.mkdir(exist_ok=True)
    img.save(out_path, "PNG")


def main() -> None:
    pages = sorted(p for p in OUT.glob("*.html"))
    count = 0
    for page in pages:
        slug = page.stem
        src = page.read_text(encoding="utf-8")
        dek = meta(src, "og:description")
        if slug == "index":
            card("Writing", dek, SITE_NAME, OGDIR / "index.png",
                 title_max_lines=1, title_hi=140, title_lo=90)
        else:
            title = meta(src, "og:title")
            if not title:
                continue
            card(title, dek, f"{SITE_NAME} · Writing", OGDIR / f"{slug}.png")
        count += 1
        print(f"  og/{slug}.png")
    print(f"Done — {count} OG images in {OGDIR}")


if __name__ == "__main__":
    main()
