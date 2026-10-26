# Digital Legacy Handbook

A calm, warm, plain-English manual for getting your digital life ready for an
emergency — or the worst day. It covers the "when-I'm-gone folder," what to
write down (accounts, wishes, passwords), what to *never* share, memorializing
vs. deleting accounts, closing recurring charges for a loved one, and
executor-friendly checklists. It ends with a printable one-page handoff letter
and a glossary.

Everything here is **local-first**: plain Markdown documents plus a tiny
build script that turns them into a small static HTML site on your own machine.
No accounts, no cloud, no tracking. Print it, share it, tape it in a binder.

This project complements the **free-emergency-binder-kit** (paper documents,
insurance, household records) and **free-home-inventory-kit** (what you own and
what it's worth). This handbook covers the *digital* half of the same job.

## Who it's for

Anyone who has ever thought *"'d hate for my family to have to dig through my
phone"* — and anyone who might someday have to do the digging for someone they
love. Written like a friend would explain it: step by step, never condescending.

## What's inside

| Doc | What it covers |
| --- | --- |
| [docs/index.md](docs/index.md) | Start here — how to use the handbook |
| [docs/01-when-im-gone-folder.md](docs/01-when-im-gone-folder.md) | Building the when-I'm-gone folder |
| [docs/02-what-to-write-down.md](docs/02-what-to-write-down.md) | Accounts, wishes, passwords — what to record |
| [docs/03-what-never-to-share.md](docs/03-what-never-to-share.md) | What to keep private, even from family |
| [docs/04-memorialize-or-delete.md](docs/04-memorialize-or-delete.md) | Memorializing vs. deleting accounts |
| [docs/05-closing-recurring-charges.md](docs/05-closing-recurring-charges.md) | Stopping bills and subscriptions for a loved one |
| [docs/06-executor-checklists.md](docs/06-executor-checklists.md) | Executor-friendly checklists |
| [docs/07-handoff-letter.md](docs/07-handoff-letter.md) | Printable one-page handoff letter |
| [docs/08-glossary.md](docs/08-glossary.md) | Glossary in plain English |

## How to run it

Requirements: Python 3.8+ (standard library only — no installs needed).

```bash
./build.py          # or: python3 build.py
```

This generates the static site in `site/`:

```bash
./build.py --serve  # optional: preview at http://localhost:8000
```

Open `site/index.html` in any browser. `site/print/handoff-letter.html` is
styled to print on one page.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## A note, not legal advice

This handbook is practical guidance and education, not legal, tax, or medical
advice. Laws about wills, executors, and digital property differ by state and
country — a chat with a local attorney or estate planner is worth it for
anything high-stakes.

## Credits

Built and maintained by **Asdale Dynamics, LLC** — beginner-friendly AI
education, books, and practical tools. Part of Dylan Asdale's plain-English
manuals and free kits.

Licensed under the MIT License — see [LICENSE](LICENSE).
"Copyright (c) 2026 Asdale Dynamics, LLC".
