#!/usr/bin/env python3
"""Build the Digital Legacy Handbook static site from docs/*.md into site/.

Standard library only. Usage:
    python3 build.py             # build site/
    python3 build.py --clean     # remove site/ and exit
    python3 build.py --serve     # build, then preview at http://localhost:8000
"""

import argparse
import http.server
import re
import shutil
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
SITE = ROOT / "site"

TITLE = "Digital Legacy Handbook"
SUBTITLE = "A calm manual for your digital life's worst day"
FOOTER = (
    "Digital Legacy Handbook &mdash; MIT Licensed &mdash; "
    "Copyright (c) 2026 Asdale Dynamics, LLC"
)

# Ordered toc: (slug, title)
PAGES = [
    ("index", "Start here"),
    ("01-when-im-gone-folder", "The when-I'm-gone folder"),
    ("02-what-to-write-down", "What to write down"),
    ("03-what-never-to-share", "What never to share"),
    ("04-memorialize-or-delete", "Memorialize or delete"),
    ("05-closing-recurring-charges", "Closing recurring charges"),
    ("06-executor-checklists", "Executor checklists"),
    ("07-handoff-letter", "Handoff letter (printable)"),
    ("08-glossary", "Glossary"),
]

# Inline-print page (handoff letter) gets the print/no-nav treatment.
PRINT_SLUGS = {"07-handoff-letter"}


# ---------------------------------------------------------------- markdown

def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def inline(md: str) -> str:
    """Inline markdown -> HTML. Code spans first so they're preserved."""
    parts = re.split(r"(`[^`]+`)", md)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append("<code>" + escape(part[1:-1]) + "</code>")
            continue
        part = escape(part)
        part = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', part)
        part = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", part)
        part = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", part)
        part = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", part)
        out.append(part)
    return "".join(out)


def _close_all(html, stack):
    while stack:
        html.append("</%s>" % stack.pop()[0])


def _find_list_signal(html, stack, depth, tag):
    while stack and (stack[-1][1] > depth or
                     (stack[-1][1] == depth and stack[-1][0] != tag)):
        html.append("</%s>" % stack.pop()[0])

def md_to_html(md: str) -> str:
    """A small, testable markdown subset renderer.

    Pipeline: parse docs into block nodes, then render. Supports headings
    (#..######), paragraphs, bullet/numbered lists with 2-space nesting,
    checkbox items, list-item continuation lines, single-level blockquotes,
    fenced code blocks, pipe tables, horizontal rules and inline styles.
    All text is HTML-escaped. Returns an HTML fragment.
    """
    body = "\n".join(_render_block(b) for b in _parse_blocks(md))
    return re.sub(r"\n{2,}", "\n", body).strip()


def _parse_blocks(md: str) -> list:
    lines = md.split("\n")
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # fenced code block
        if s.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            blocks.append(("code", "\n".join(buf)))
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            blocks.append(("heading", len(m.group(1)), m.group(2)))
            i += 1
            continue

        # horizontal rule
        if re.match(r"^-{3,}$", s):
            blocks.append(("hr",))
            i += 1
            continue

        # table (this line is a pipe row and the next is a divider row)
        if s.startswith("|") and i + 1 < n and \
                re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            rows = [s]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            blocks.append(("table", rows[0], rows[1:]))
            continue

        # blockquote (single level)
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].lstrip())
                i += 1
            blocks.append(("quote", " ".join(buf)))
            continue

        # list run (items + indented continuation lines)
        m = re.match(r"^(\s*)(-|\*|\d+\.)\s+(.*)$", line)
        if m:
            items = []
            while i < n:
                m = re.match(r"^(\s*)(-|\*|\d+\.)\s+(.*)$", lines[i])
                if m:
                    ordered = bool(re.match(r"\d+\.", m.group(2)))
                    items.append([len(m.group(1)) // 2, ordered, m.group(3)])
                    i += 1
                elif items and re.match(r"^\s{2,}\S", lines[i]):
                    items[-1][2] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            blocks.append(("list", items))
            continue

        # paragraph (join soft-wrapped lines)
        buf = [s]
        i += 1
        while i < n:
            nxt = lines[i]
            ns = nxt.strip()
            if (not ns or ns.startswith(("```", "#", ">"))
                    or re.match(r"^\s*(-|\*|\d+\.)\s", nxt)
                    or re.match(r"^-{3,}$", ns)
                    or (ns.startswith("|") and i + 1 < len(lines)
                        and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()))
                    or re.match(r"^\s{2,}\S", nxt)):
                break
            buf.append(ns)
            i += 1
        blocks.append(("para", " ".join(buf)))

    return blocks


def _split_row(row: str) -> list:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _render_block(block: tuple) -> str:
    kind = block[0]

    if kind == "heading":
        level, text = block[1], block[2]
        return f"<h{level}>{inline(text)}</h{level}>"

    if kind == "hr":
        return "<hr>"

    if kind == "code":
        return "<pre><code>" + escape(block[1]) + "</code></pre>"

    if kind == "quote":
        return "<blockquote>" + inline(block[1]) + "</blockquote>"

    if kind == "para":
        return "<p>" + inline(block[1]) + "</p>"

    if kind == "table":
        header = _split_row(block[1])
        rows = []
        for raw in block[2]:
            cells = _split_row(raw)
            cells += [""] * (len(header) - len(cells))
            rows.append(cells)
        parts = ["<table><thead><tr>"]
        parts += [f"<th>{inline(h)}</th>" for h in header]
        parts.append("</tr></thead><tbody>")
        for cells in rows:
            parts.append("<tr>")
            parts += [f"<td>{inline(c)}</td>" for c in cells]
            parts.append("</tr>")
        parts.append("</tbody></table>")
        return "".join(parts)

    if kind == "list":
        html, _ = _render_items(block[1], 0, False)
        return html

    raise ValueError(f"unknown block kind: {kind}")


def _render_items(items: list, pos: int, depth: int):
    """Render items from index `pos` whose depth == current.

    Returns (html, next_unconsumed_index).
    """
    parts = []
    idx = pos
    ordered = None
    while idx < len(items):
        d, is_ordered, text = items[idx]
        if d < depth:
            break
        if d > depth:
            sub_html, idx = _render_items(items, idx, depth + 1)
            parts.append(sub_html)
            parts.append("</li>")   # close the item holding the nested list
            continue
        # same depth
        if ordered is None:
            ordered = is_ordered
        elif ordered != is_ordered:
            break  # marker type switched; caller re-opens at this item
        tag = "ol" if ordered else "ul"
        if not parts:
            parts = [f"<{tag}>"]
        checkbox = ""
        cb = re.match(r"^\[([ xX])\]\s*(.*)$", text)
        if cb:
            checked = " checked" if cb.group(1) != " " else ""
            checkbox = f'<input type="checkbox" disabled{checked}> '
            text = cb.group(2)
        cls = ' class="check"' if checkbox else ""
        if idx + 1 < len(items) and items[idx + 1][0] > d:
            # nested list follows: keep this <li> open for the sub-list
            parts.append(f"<li{cls}>{checkbox}{inline(text)}")
        else:
            parts.append(f"<li{cls}>{checkbox}{inline(text)}</li>")
        idx += 1
    if not parts:
        return "", idx
    tag = "ol" if ordered else "ul"
    return "\n".join(parts) + f"\n</{tag}>", idx
# ---------------------------------------------------------------- the site

CSS = """\
:root {
  --bg: #faf7f2; --paper: #fffdf9; --ink: #33302a; --soft: #6f675a;
  --accent: #7a5c3d; --line: #e6ded0; --ok: #38744c;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.65 Georgia, 'Times New Roman', serif;
}
.layout { display: flex; max-width: 60rem; margin: 0 auto; gap: 2.5rem; padding: 0 1.25rem; }
nav.toc {
  width: 15rem; flex: 0 0 auto; padding: 2rem 0; font-family: Verdana, Arial, sans-serif;
  font-size: 0.82rem; border-right: 1px solid var(--line);
}
nav.toc h1 { font-size: 0.95rem; margin: 0 0 0.2rem; color: var(--accent); }
nav.toc .sub { color: var(--soft); margin: 0 0 1.2rem; font-size: 0.72rem; }
nav.toc a { display: block; color: var(--ink); text-decoration: none; padding: 0.28rem 0.6rem; border-radius: 4px; }
nav.toc a:hover { background: var(--paper); }
nav.toc a.current { background: var(--paper); color: var(--accent); font-weight: bold; }
main { padding: 2rem 0 4rem; max-width: 38rem; }
main h1 { font-size: 1.9rem; line-height: 1.2; color: var(--accent); margin-top: 0; }
main h2 { font-size: 1.3rem; color: var(--accent); margin-top: 2.2rem; }
main p, main li { hyphens: auto; }
main em:first-child { color: var(--soft); }
a { color: var(--accent); }
main a { text-decoration: underline; text-decoration-color: #d3c2a8; }
hr { border: 0; border-top: 1px solid var(--line); margin: 2rem 0; }
blockquote {
  margin: 1.2rem 0; padding: 0.4rem 1rem; border-left: 3px solid var(--accent);
  background: var(--paper); font-style: italic;
}
blockquote p { margin: 0.2rem 0; }
table { border-collapse: collapse; width: 100%; margin: 1.2rem 0; font-size: 0.92rem; }
th, td { border: 1px solid var(--line); padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }
th { background: var(--paper); font-family: Verdana, Arial, sans-serif; font-size: 0.8rem; color: var(--accent); }
code { background: var(--paper); border: 1px solid var(--line); border-radius: 3px; padding: 0.05rem 0.3rem; font-size: 0.85em; }
pre { background: var(--paper); border: 1px solid var(--line); border-radius: 6px; padding: 0.8rem 1rem; overflow-x: auto; }
pre code { border: 0; padding: 0; }
input[type=checkbox] { accent-color: var(--ok); }
li.check { list-style: none; margin-left: -1.4rem; }
ul .check, ol .check { display: block; }
footer { color: var(--soft); font-family: Verdana, Arial, sans-serif; font-size: 0.72rem; text-align: center; padding: 2rem 1rem 3rem; }
.pagenav { margin-top: 3rem; display: flex; justify-content: space-between; gap: 1rem; }
.pagenav a { text-decoration: none; border: 1px solid var(--line); background: var(--paper); padding: 0.5rem 0.9rem; border-radius: 6px; font-size: 0.85rem; }
.pagenav a:hover { border-color: var(--accent); }
@media (max-width: 52rem) {
  .layout { flex-direction: column; gap: 0; }
  nav.toc { border-right: 0; border-bottom: 1px solid var(--line); width: 100%; padding: 1.25rem 0; }
  main { padding-top: 1.5rem; }
}
@media print {
  body { background: #fff; font-size: 12pt; }
  nav.toc, footer, .pagenav { display: none; }
  .layout { display: block; max-width: none; padding: 0; }
  main { max-width: none; padding: 0; }
  .letter-rule { page-break-inside: avoid; }
  a { color: inherit; text-decoration: none; }
}
"""

NAV_TEMPLATE = """
<nav class="toc">
  <h1>{title}</h1>
  <div class="sub">{subtitle}</div>
  {links}
</nav>
"""

PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A calm, plain-English manual for getting your digital life ready for an emergency or the worst day.">
<title>{title} &middot; {site_title}</title>
<style>{css}</style>
</head>
<body>
<div class="layout">
{nav}<main>
{content}
{pagenav}
</main>
</div>
<footer>{footer}</footer>
</body>
</html>
"""


def page_nav(slug: str) -> str:
    idx = [s for s, _ in PAGES].index(slug)
    prev = next = None
    if idx > 0:
        prev = PAGES[idx - 1]
    if idx + 1 < len(PAGES):
        next = PAGES[idx + 1]
    parts = ['<div class="pagenav">']
    if prev:
        parts.append(f'<a href="{prev[0]}.html">&larr; {prev[1]}</a>')
    else:
        parts.append("<span></span>")
    if next:
        parts.append(f'<a href="{next[0]}.html">{next[1]} &rarr;</a>')
    else:
        parts.append("<span></span>")
    parts.append("</div>")
    return "".join(parts)


def nav_html(current: str) -> str:
    links = []
    for slug, name in PAGES:
        cls = ' class="current"' if slug == current else ""
        links.append(f'<a{cls} href="{slug}.html">{name}</a>')
    return NAV_TEMPLATE.format(
        title=TITLE, subtitle=SUBTITLE, links="\n  ".join(links)
    )


def title_of(md: str) -> str:
    for line in md.split("\n"):
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            return m.group(1).strip()
    return "Untitled"


def build() -> int:
    sources = {}
    for slug, _ in PAGES:
        path = DOCS / f"{slug}.md"
        if not path.exists():
            print(f"ERROR: missing doc docs/{slug}.md", file=sys.stderr)
            return 1
        sources[slug] = path.read_text(encoding="utf-8")

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "print").mkdir(parents=True)

    for slug, _ in PAGES:
        md = sources[slug]
        # page links point at site pages, not raw markdown
        md = re.sub(r"\]\(([^)#\s]+)\.md\)", r"](\1.html)", md)
        body = md_to_html(md)
        t = title_of(md)
        html = PAGE_TEMPLATE.format(
            title=t,
            site_title=TITLE,
            css=CSS,
            nav=nav_html(slug),
            content=body,
            pagenav=page_nav(slug),
            footer=FOOTER,
        )
        (SITE / f"{slug}.html").write_text(html, encoding="utf-8")

    # print-only versions: no nav, no footer, plain chrome
    for slug in PRINT_SLUGS:
        md = sources[slug]
        html = PAGE_TEMPLATE.format(
            title=title_of(md) + " (print)",
            site_title=TITLE,
            css=CSS,
            nav="",
            content=md_to_html(md),
            pagenav="",
            footer="",
        )
        (SITE / "print" / f"{slug}.html").write_text(html, encoding="utf-8")

    print(f"Built {len(PAGES)} pages + {len(PRINT_SLUGS)} print page(s) -> {SITE}/")
    return 0


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def log_message(self, fmt, *args):  # quieter logs
        pass


def serve(port: int = 8000) -> None:
    url = f"http://localhost:{port}/index.html"
    print(f"Serving {SITE}/ at {url}  (Ctrl+C to stop)")
    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clean", action="store_true", help="remove site/ and exit")
    ap.add_argument("--serve", action="store_true", help="build, then preview")
    args = ap.parse_args()
    if args.clean:
        if SITE.exists():
            shutil.rmtree(SITE)
            print(f"Removed {SITE}")
        return 0
    rc = build()
    if rc == 0 and args.serve:
        serve()
    return rc


if __name__ == "__main__":
    sys.exit(main())
