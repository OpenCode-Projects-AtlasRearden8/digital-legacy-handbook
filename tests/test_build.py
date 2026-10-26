"""Tests for the Digital Legacy Handbook build.

Run:  python3 -m unittest discover -s tests -v
"""

import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

DOCS = ROOT / "docs"
SLUGS = [s for s, _ in build.PAGES]


# ---------------------------------------------------------------- helpers

class TagBalanceParser(HTMLParser):
    """Checks that every opened tag is closed (void elements excepted)."""

    VOID = {"meta", "br", "hr", "img", "input", "link"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack:
            self.errors.append(f"unexpected </{tag}> at {self.getpos()}")
            return
        open_tag, pos = self.stack.pop()
        if open_tag != tag:
            self.errors.append(
                f"mismatch: <{open_tag}> opened at {pos} closed by </{tag}> "
                f"at {self.getpos()}"
            )


def page_bodies():
    return {slug: (DOCS / f"{slug}.md").read_text(encoding="utf-8")
            for slug in SLUGS}


# ---------------------------------------------------------------- converter

class TestMarkdown(unittest.TestCase):
    def test_headings(self):
        h = build.md_to_html("# One\n\n## Two")
        self.assertIn("<h1>One</h1>", h)
        self.assertIn("<h2>Two</h2>", h)

    def test_inline_styles_escape(self):
        h = build.md_to_html("Text with <b> & **bold**")
        self.assertIn("&lt;b&gt; &amp; <strong>bold</strong>", h)

    def test_link_and_code(self):
        h = build.md_to_html("See [the doc](x.md) and `make_thing()`")
        self.assertIn('<a href="x.md">the doc</a>', h)
        self.assertIn("<code>make_thing()</code>", h)

    def test_simple_list(self):
        h = build.md_to_html("- one\n- two")
        self.assertEqual(h, "<ul>\n<li>one</li>\n<li>two</li>\n</ul>")

    def test_nested_list_is_inside_previous_li(self):
        h = build.md_to_html("- a\n  - a1\n- b")
        self.assertIn("<li>a\n<ul>\n<li>a1</li>\n</ul>\n</li>", h)

    def test_numbered_list(self):
        h = build.md_to_html("1. one\n2. two")
        self.assertIn("<ol>", h)
        self.assertIn("<li>one</li>", h)
        self.assertIn("</ol>", h)

    def test_checkboxes(self):
        h = build.md_to_html("- [ ] todo\n- [x] done")
        self.assertIn('<input type="checkbox" disabled> ', h)
        self.assertIn('checked', h)

    def test_table(self):
        h = build.md_to_html("| A | B |\n| --- | --- |\n| 1 | **2** |")
        self.assertIn("<th>A</th>", h)
        self.assertIn("<td><strong>2</strong></td>", h)
        self.assertIn("</tbody></table>", h)

    def test_blockquote_joins_lines(self):
        h = build.md_to_html("> first line\n> second")
        self.assertIn("<blockquote>first line second</blockquote>", h)

    def test_code_fence_escapes(self):
        h = build.md_to_html("```\nif (a < b): return\n```")
        self.assertIn("a &lt; b", h)

    def test_paragraph_wraps_lines(self):
        h = build.md_to_html("one line\nthen next")
        self.assertEqual(h, "<p>one line then next</p>")

    def test_hr(self):
        self.assertIn("<hr>", build.md_to_html("---"))


# ---------------------------------------------------------------- content

class TestDocs(unittest.TestCase):
    def test_every_doc_exists_nonempty_with_h1(self):
        for slug, body in page_bodies().items():
            with self.subTest(slug=slug):
                self.assertTrue(body.strip(), f"docs/{slug}.md is empty")
                self.assertTrue(
                    re.match(r"^#\s+\S", body), f"docs/{slug}.md lacks an H1"
                )

    def test_internal_links_resolve(self):
        for slug, body in page_bodies().items():
            for target in re.findall(r"\]\(([^)#\s]+\.md)\)", body):
                self.assertTrue(
                    (DOCS / target).exists(),
                    f"docs/{slug}.md links to missing docs/{target}",
                )

    def test_glossary_table_has_no_invented_terms(self):
        body = (DOCS / "08-glossary.md").read_text(encoding="utf-8")
        for banned in ("GRAVE-ready", "IPA / IREC", "LOC / Letter"):
            self.assertNotIn(banned, body)

    def test_letter_mentions_password_pointer_rule(self):
        body = (DOCS / "07-handoff-letter.md").read_text(encoding="utf-8")
        self.assertIn("passcode", body)
        self.assertIn("signature", body.lower())


# ---------------------------------------------------------------- site

class TestSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rc = build.build()
        assert rc == 0, "build failed"
        cls.site = ROOT / "site"

    def test_all_pages_built(self):
        for slug in SLUGS:
            self.assertTrue((self.site / f"{slug}.html").exists(), slug)

    def test_nav_links_and_footer(self):
        html = (self.site / "index.html").read_text(encoding="utf-8")
        for slug in SLUGS:
            self.assertIn(f'href="{slug}.html"', html)
        self.assertIn("2026 Asdale Dynamics, LLC", html)

    def test_print_page_has_no_nav_and_exists(self):
        p = self.site / "print" / "07-handoff-letter.html"
        self.assertTrue(p.exists())
        html = p.read_text(encoding="utf-8")
        self.assertNotIn('class="toc"', html)

    def test_all_built_pages_are_well_formed_html(self):
        Parser = TagBalanceParser
        checks = sorted(self.site.glob("*.html")) + \
            sorted(self.site.glob("print/*.html"))
        self.assertTrue(checks)
        for path in checks:
            parser = Parser()
            parser.feed(path.read_text(encoding="utf-8"))
            parser.close()
            self.assertFalse(parser.errors, f"{path}: {parser.errors[:5]}")
            self.assertFalse(
                parser.stack, f"{path}: unclosed tags {[t for t, _ in parser.stack]}"
            )

    def test_internal_html_links_resolve(self):
        site = self.site
        checks = sorted(site.glob("*.html")) + sorted(site.glob("print/*.html"))
        found = 0
        for path in checks:
            text = path.read_text(encoding="utf-8")
            base = site / "print" if path.parent.name == "print" else site
            for href in re.findall(r'href="([^"#]+\.html)"', text):
                self.assertTrue(
                    (base / href).exists(),
                    f"{path} links to missing {href}",
                )
                found += 1
        self.assertGreater(found, len(SLUGS), "expected many internal links")

    def test_no_secret_material_in_repo_files(self):
        patterns = [
            re.compile(p)
            for p in (r"AKIA[0-9A-Z]{16}", r"sk-[A-Za-z0-9]{20,}",
                      r"BEGIN (RSA )?PRIVATE KEY",
                      r"(?i)actual.?password\s*[:=]\s*\S+")
        ]
        for path in list(ROOT.rglob("*")):
            if not path.is_file() or path.suffix in (".zip",) or \
                    ".git" in path.parts or path.name == "build.py":
                continue
            try:
                text = path.read_text(
                    encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat in patterns:
                self.assertIsNone(
                    pat.search(text), f"secret pattern {pat.pattern} in {path}"
                )

    def test_license_line_exact(self):
        lic = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Asdale Dynamics, LLC", lic)


if __name__ == "__main__":
    unittest.main()
