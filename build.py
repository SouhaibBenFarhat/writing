#!/usr/bin/env python3
"""Build the Writing section from Markdown articles.

Usage:  python3 build.py

Reads each source .md, strips any draft/LinkedIn scaffolding, converts the
article body to HTML, and writes one page per article plus an index. Prose is
read straight from source, so nothing is re-typed by hand. Add a new essay by
dropping a config row below.
"""

import html
import re
from pathlib import Path

# Where the source markdown lives, and where pages are written.
SRC = Path.home() / "Desktop"
OUT = Path(__file__).resolve().parent

SITE_NAME = "Souhaib Ben Farhat"
SITE_URL = "https://souhaibbenfarhat.github.io/writing"  # absolute base for OG tags
PORTFOLIO_URL = "../"  # served at github.io/writing/ -> ".." is the portfolio root

# --- article registry: newest first -----------------------------------------
# extract rule:
#   after-dek     body is everything after the "*italic dek*" line
#   after-hr      body is everything after the first "---" rule
#   post-body     body is between "## Post body (copy-paste ready)" and the next "---"
ARTICLES = [
    {
        "slug": "the-senior-engineers-paradox",
        "src": "the-senior-engineers-paradox.md",
        "title": "The Senior Engineer's Paradox",
        "dek": "The more senior the room, the fewer facts are left to decide anything — so past a certain level, engineering stops being a technical problem and becomes a social one.",
        "date": "July 23, 2026",
        "extract": "after-hr",
    },
    {
        "slug": "race-to-the-optimum",
        "src": "race-to-the-optimum.md",
        "title": "The Race Is to the Optimum, Not the Maximum",
        "dek": "Thrust SSC, Landauer's limit, and why the fight isn't won by whoever builds the largest data centre.",
        "date": "July 23, 2026",
        "extract": "post-body",
    },
    {
        "slug": "from-where-im-sitting",
        "src": "not-yet-caught.md",
        "title": "From Where I'm Sitting",
        "dek": "On misinformation, incentives, and the uncomfortable possibility that we're not the audience — we're the metric.",
        "date": "July 23, 2026",
        "extract": "post-body",
    },
    {
        "slug": "if-everyone-speeds-up-nobody-moves",
        "src": "if-everyone-speeds-up-nobody-moves.md",
        "title": "If Everyone Speeds Up, Nobody Moves",
        "dek": "Notes on what AI actually moved, and what it only appeared to.",
        "date": "July 22, 2026",
        "extract": "after-dek",
    },
    {
        "slug": "ai-highest-abstraction",
        "src": "ai-isnt-replacing-engineers.md",
        "title": "AI Is the Highest Abstraction Engineering Has Ever Built",
        "dek": "A reasoning journey — from a stranger's comment to something that finally held up.",
        "date": "July 22, 2026",
        "extract": "after-dek",
    },
]

# LinkedIn has no markdown, so emphasis was typed as Mathematical Sans-Serif
# Bold glyphs. On the web, fold those runs back to ASCII wrapped in <strong>.
def _bold_ascii(ch: str):
    o = ord(ch)
    if 0x1D5EE <= o <= 0x1D607:
        return chr(o - 0x1D5EE + ord("a"))
    if 0x1D5D4 <= o <= 0x1D5ED:
        return chr(o - 0x1D5D4 + ord("A"))
    if 0x1D7EC <= o <= 0x1D7F5:
        return chr(o - 0x1D7EC + ord("0"))
    return None


def fold_bold_glyphs(text: str) -> str:
    out, i, n = [], 0, len(text)
    while i < n:
        if _bold_ascii(text[i]) is not None:
            run, j = [], i
            while j < n:
                a = _bold_ascii(text[j])
                if a is not None:
                    run.append(a)
                    j += 1
                elif text[j] == " " and j + 1 < n and _bold_ascii(text[j + 1]) is not None:
                    run.append(" ")
                    j += 1
                else:
                    break
            out.append("\x00BOLD\x00" + "".join(run) + "\x00ENDBOLD\x00")
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def extract_body(text: str, rule: str) -> str:
    lines = text.splitlines()
    if rule == "after-dek":
        for i, ln in enumerate(lines):
            if ln.strip().startswith("*") and ln.strip().endswith("*"):
                return "\n".join(lines[i + 1:]).strip()
        # no dek found: drop just the H1
        return "\n".join(lines[1:]).strip()
    if rule == "after-hr":
        for i, ln in enumerate(lines):
            if ln.strip() == "---":
                return "\n".join(lines[i + 1:]).strip()
        raise ValueError("after-hr: no '---' found")
    if rule == "post-body":
        start = None
        for i, ln in enumerate(lines):
            if ln.strip().lower().startswith("## post body"):
                start = i + 1
                break
        if start is None:
            raise ValueError("post-body: marker not found")
        end = len(lines)
        for j in range(start, len(lines)):
            if lines[j].strip() == "---":
                end = j
                break
        return "\n".join(lines[start:end]).strip()
    raise ValueError(f"unknown rule {rule!r}")


def attr(text: str) -> str:
    """Escape for a double-quoted HTML attribute: &, <, >, and " — but NOT the
    apostrophe. In a double-quoted attribute ' is already safe, and emitting it as
    &#x27; trips naive entity decoders downstream (e.g. a card reader that only
    knows the decimal &#39;)."""
    return html.escape(text, quote=False).replace('"', "&quot;")


def inline(text: str) -> str:
    """Escape HTML, then apply the small subset of Markdown inline syntax."""
    text = fold_bold_glyphs(text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = text.replace("\x00BOLD\x00", "<strong>").replace("\x00ENDBOLD\x00", "</strong>")
    return text


def cells(row: str) -> list:
    parts = row.split("|")[1:-1]  # drop the empty edges
    return [c.strip() for c in parts]


def md_to_html(body: str) -> str:
    lines = body.splitlines()
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped == "---":
            out.append("<hr />")
            i += 1
        elif stripped.startswith("### "):
            out.append(f"<h3>{inline(stripped[4:])}</h3>")
            i += 1
        elif stripped.startswith("## "):
            out.append(f"<h2>{inline(stripped[3:])}</h2>")
            i += 1
        elif stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(buf))}</p></blockquote>")
        elif stripped.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            header = cells(rows[0])
            body_rows = [r for r in rows[1:] if not set(r.replace("|", "").strip()) <= {"-", ":", " "}]
            thead = "".join(f"<th>{inline(c)}</th>" for c in header)
            tbody = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells(r)) + "</tr>"
                for r in body_rows
            )
            out.append(
                f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead>'
                f"<tbody>{tbody}</tbody></table></div>"
            )
        else:
            buf = []
            while i < n and lines[i].strip() and not re.match(r"^(#{2,3} |>|\||---$)", lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(buf))}</p>")
    return "\n      ".join(out)


def page(article: dict) -> str:
    body = extract_body((SRC / article["src"]).read_text(encoding="utf-8"), article["extract"])
    prose = md_to_html(body)
    title = html.escape(article["title"], quote=False)
    dek = html.escape(article["dek"], quote=False)
    t_attr = attr(article["title"])
    d_attr = attr(article["dek"])
    slug = article["slug"]
    og_image = f"{SITE_URL}/og/{slug}.png"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} — {SITE_NAME}</title>
  <meta name="description" content="{d_attr}" />
  <link rel="canonical" href="{SITE_URL}/{slug}.html" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="{SITE_NAME}" />
  <meta property="og:title" content="{t_attr}" />
  <meta property="og:description" content="{d_attr}" />
  <meta property="og:url" content="{SITE_URL}/{slug}.html" />
  <meta property="og:image" content="{og_image}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="{t_attr}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{t_attr}" />
  <meta name="twitter:description" content="{d_attr}" />
  <meta name="twitter:image" content="{og_image}" />
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <main class="site article">
    <nav class="topnav">
      <a href="index.html">← Writing</a>
      <a href="{PORTFOLIO_URL}">Portfolio</a>
    </nav>
    <header>
      <h1>{title}</h1>
      <p class="dek">{dek}</p>
      <p class="meta">{article['date']} · {SITE_NAME}</p>
    </header>
    <div class="prose">
      {prose}
    </div>
    <footer class="foot">
      <a href="index.html">← All writing</a>
      <span>{SITE_NAME}</span>
    </footer>
  </main>
</body>
</html>
"""


def index() -> str:
    entries = "\n".join(
        f"""      <a class="entry" href="{a['slug']}.html">
        <p class="date">{a['date']}</p>
        <p class="etitle">{html.escape(a['title'], quote=False)}</p>
        <p class="edek">{html.escape(a['dek'], quote=False)}</p>
      </a>"""
        for a in ARTICLES
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Writing — {SITE_NAME}</title>
  <meta name="description" content="Essays on AI, abstraction, incentives, and engineering judgment." />
  <link rel="canonical" href="{SITE_URL}/" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="{SITE_NAME}" />
  <meta property="og:title" content="Writing — {SITE_NAME}" />
  <meta property="og:description" content="Essays on AI, abstraction, incentives, and engineering judgment." />
  <meta property="og:url" content="{SITE_URL}/" />
  <meta property="og:image" content="{SITE_URL}/og/index.png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:image" content="{SITE_URL}/og/index.png" />
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <main class="site">
    <nav class="topnav">
      <a href="{PORTFOLIO_URL}">← Portfolio</a>
    </nav>
    <header class="masthead">
      <p class="name">{SITE_NAME}</p>
      <h1>Writing</h1>
      <p class="tagline">Essays on AI, abstraction, incentives, and the judgment a machine can't automate.</p>
    </header>
    <section class="list">
{entries}
    </section>
    <footer class="foot">
      <span>{SITE_NAME}</span>
      <a href="{PORTFOLIO_URL}">Portfolio</a>
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    for a in ARTICLES:
        (OUT / f"{a['slug']}.html").write_text(page(a), encoding="utf-8")
        print(f"  wrote {a['slug']}.html")
    (OUT / "index.html").write_text(index(), encoding="utf-8")
    print("  wrote index.html")
    print(f"Done — {len(ARTICLES)} articles + index in {OUT}")


if __name__ == "__main__":
    main()
