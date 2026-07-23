#!/usr/bin/env python3
"""Generate Open Graph share images (1200x630) for every page.

Reads the og:title / og:description already baked into each *.html by build.py,
so the cards always match what is published, and this script needs nothing but
Pillow — no imports from build.py, no source markdown.

Each page yields two cards: a dark one at og/<slug>.png (the canonical og:image
social platforms use — one static image, since feeds can't pick a theme) and a
light one at og/<slug>-light.png, which the portfolio swaps to in light mode.

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

# palettes — mirror the site's dark and light themes
PALETTES = {
    "dark": {
        "bg": (23, 24, 26), "ink": (236, 234, 227),
        "dek": (176, 175, 167), "muted": (139, 138, 130), "rule": (52, 51, 47),
    },
    "light": {
        "bg": (252, 252, 251), "ink": (28, 28, 26),
        "dek": (85, 85, 79), "muted": (118, 118, 110), "rule": (216, 216, 209),
    },
}


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


def card(title: str, dek: str, eyebrow: str, out_path: Path, pal: dict,
         title_max_lines: int = 3, title_hi: int = 82, title_lo: int = 50) -> None:
    img = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(img)

    sans = font("PTSans-Bold.ttf", 23)
    italic = font("PTSerif-Italic.ttf", 31)

    draw_tracked(d, (MARGIN, 84), eyebrow.upper(), sans, pal["muted"], tracking=3.5)

    tf, tlines = fit(title, "PTSerif-Bold.ttf", CW, title_max_lines, title_hi, title_lo)
    tlh = line_h(tf)
    dek_lines = wrap(dek, italic, CW)[:3] if dek else []
    dlh = line_h(italic)
    gap = 30 if dek_lines else 0

    block_h = len(tlines) * tlh + gap + len(dek_lines) * dlh
    top = 150 + (390 - block_h) // 2  # center in the middle band

    y = top
    for ln in tlines:
        d.text((MARGIN, y), ln, font=tf, fill=pal["ink"])
        y += tlh
    y += gap
    for ln in dek_lines:
        d.text((MARGIN, y), ln, font=italic, fill=pal["dek"])
        y += dlh

    d.line([(MARGIN, 548), (W - MARGIN, 548)], fill=pal["rule"], width=1)
    draw_tracked(d, (MARGIN, 568), "souhaibbenfarhat.github.io/writing", sans, pal["muted"], tracking=1.0)

    OGDIR.mkdir(exist_ok=True)
    img.save(out_path, "PNG")


def render(slug: str, title: str, dek: str, eyebrow: str, **kw) -> None:
    """One card per theme: <slug>.png (dark, canonical) and <slug>-light.png."""
    for theme, pal in PALETTES.items():
        suffix = "" if theme == "dark" else "-light"
        card(title, dek, eyebrow, OGDIR / f"{slug}{suffix}.png", pal, **kw)
        print(f"  og/{slug}{suffix}.png")


def main() -> None:
    pages = sorted(OUT.glob("*.html"))
    n = 0
    for page in pages:
        slug = page.stem
        src = page.read_text(encoding="utf-8")
        dek = meta(src, "og:description")
        if slug == "index":
            render(slug, "Writing", dek, SITE_NAME, title_max_lines=1, title_hi=140, title_lo=90)
        elif (title := meta(src, "og:title")):
            render(slug, title, dek, f"{SITE_NAME} · Writing")
        else:
            continue
        n += 1
    print(f"Done — {n} pages × {len(PALETTES)} themes = {n * len(PALETTES)} images in {OGDIR}")


if __name__ == "__main__":
    main()
