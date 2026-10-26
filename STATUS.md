# STATUS.md

Last verified: 2026-10-26

## What was built

**Digital Legacy Handbook** — a calm, plain-English manual for preparing your
digital life for an emergency or your worst day. Local-first: plain Markdown
documents plus a dependency-free Python build script that generates a small
static HTML site. No accounts, no cloud, no tracking.

Contents:

- `docs/` — 9 Markdown pages:
  - `index.md` — start-here guide and the three golden rules
  - `01-when-im-gone-folder.md` — building the physical/encrypted folder
  - `02-what-to-write-down.md` — accounts, wishes, password *locations*
  - `03-what-never-to-share.md` — raw passwords, seed phrases, the
    two-envelope split, raid-kit avoidance
  - `04-memorialize-or-delete.md` — ghost vs. memorialized vs. deleted,
    per-platform legacy features, executor close-out steps
  - `05-closing-recurring-charges.md` — statement sweep, strongest-point
    cancellation order, the keep-list
  - `06-executor-checklists.md` — 72 hours / week one / paperwork / digital
    cleanup / close-out checklists
  - `07-handoff-letter.md` — printable one-page handoff letter template
  - `08-glossary.md` — ~25 plain-English definitions
- `build.py` — stdlib-only Markdown subset renderer + static site generator
  (warm serif design, responsive layout, print stylesheet so the handoff
  letter prints on one page, `--serve` preview mode, `--clean` flag)
- `tests/test_build.py` — 23 tests: converter unit tests, doc content checks,
  HTML well-formedness (tag-balance parser on every built page), internal
  link integrity (docs to docs, site page to page), nav/footer presence,
  secret-pattern scan, LICENSE copyright-line check
- `LICENSE` (MIT, "Copyright (c) 2026 Asdale Dynamics, LLC"), `README.md`

Complements the free-emergency-binder-kit and free-home-inventory-kit (paper
and physical document sides of the same job).

## How to run it

Requires Python 3.8+ (standard library only; no pip installs).

```bash
python3 build.py                              # build site/ from docs/
python3 build.py --serve                      # preview at http://localhost:8000
python3 build.py --clean                      # remove site/
python3 -m unittest discover -s tests -v      # run the test suite
```

Open `site/index.html` in a browser; `site/print/07-handoff-letter.html` is
the print-only letter page.

## Verification results

- `python3 -m unittest discover -s tests` — **OK, 23/23 tests pass**
- `python3 build.py` — builds 9 pages + 1 print page into `site/`
- All built pages pass the tag-balance/HTML well-formedness check
- All internal doc links and all built page-to-page links resolve
- Secret-pattern scan (AWS-style keys, private-key blocks, etc.): clean
- Hand-verified rendering: nested lists and checkbox items render inside the
  correct `<li>`; tables, blockquotes, code fences, and the letter's fill-in
  lines render as intended

## Known gaps / future work

- The Markdown renderer covers the subset this handbook uses (headings,
  paragraphs, nested *and* mixed-level lists, checkboxes, tables, blockquotes,
  code fences, inline styles). It does not aim to be a full CommonMark
  implementation; obscure constructs (reference links, setext headings,
  nested blockquotes) are out of scope.
- Content is US-flavored (probate/executor terminology varies by state and
  country; specifics are flagged as "ask a local attorney" in the text).
- No dark mode; print styling is tuned for the handoff letter first.
- Suggested next steps: a fill-in-the-blank printable PDF workbook page, and
  a cross-link to the companion kits' docs when those land together.
