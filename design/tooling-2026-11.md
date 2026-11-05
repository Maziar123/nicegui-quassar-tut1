# Tooling survey, November 2026

What else could build a project like this one: frameworks, building blocks and small tools.
Checked 2026-11-05 against PyPI, the npm registry, GitHub search and release pages. Items marked
*unverified* could not be confirmed from an official source in this session.

## Recommendation

**Keep the custom generator.** No framework links one numbered comment to line ranges in *three*
code blocks at once. Quarto, Zensical / Material, Code Hike and Expressive Code all annotate one
block at a time. The cross-comments, the pixel proof and the TV layout are what this project is
about, and the generator that does them is small (about 800 lines of Python).

Worth adopting next, in this order. **Adopted on 2026-11-05: items 1 to 4** (uv, ruff + prek, just, CI + Pages + Dependabot), plus diff pictures in `shoot.py` and browser tests in `tests/test_browser.py`.

1. **uv** (0.13.7): venv, Python version and a lock file in one tool. Simpler than `python -m venv`
   on Arch (PEP 668).
2. **ruff** (0.17.3) for lint and format, run by **prek** (0.5.10, pre-commit compatible, one binary)
   together with `pytest` and a "is `docs/` up to date?" check.
3. **just** (1.59.0) for short commands: `just shoot`, `just build`, `just test`.
4. A **GitHub Actions** job (setup-uv v10, upload-pages-artifact v5, deploy-pages v5) that rebuilds the
   site and fails when the committed `docs/` is out of date.
5. Optional: **Pillow `ImageChops`** for the exact pixel check, and pixelmatch-py only to draw a diff
   picture when columns differ. Optional: render Mermaid to SVG at build time with the Playwright the
   project already has, so diagrams also work offline.

**If a framework is ever wanted:** **Zensical** (successor to Material for MkDocs) is the closest
Python fit. It uses Python-Markdown, Pygments and Jinja2, and has tabs, code annotations and
Mermaid. But it is still alpha (0.0.74), so it is not a base for a classroom site yet. With Node
allowed, **Astro Starlight + Expressive Code** is the strongest choice (RTL i18n, synced tabs, an
annotation plugin API). **VitePress** fits the Vue topic, but its stable line is old (1.6.4, 2025-08) and
v2 is still alpha.

## Docs frameworks

| Name | Latest (date) | Activity | Fit |
|---|---|---|---|
| Zensical | 0.0.74 (2026-10-30), alpha | 6.1k stars, daily | Best Python fit; alpha; RTL *unverified* |
| Material for MkDocs | 9.8.0 (2026-10-24) | 27.6k | In maintenance mode; release notes give end of life 2027-05-05. Not for new projects |
| Sphinx + MyST-Parser | 9.2.0 (2026-10-21) / 5.1.0 (2026-05-13) | 8.1k / 0.9k | Mature, but heavy for one site |
| Jupyter Book 2 / mystmd | 2.1.7 / 1.12.0 (2026-10) | 4.3k / 0.5k | pip install, Node engine inside (*unverified*); weak i18n |
| Quarto | 1.11.9 (2026-10-30) | 6.2k | Per-block code annotations, tabsets, Mermaid; one binary |
| Astro Starlight | 0.42.9 (2026-11-04) | 9.5k, daily | Best Node choice; RTL per locale |
| VitePress | 1.6.4 (2025-08); 2.0.0-alpha.21 | 18.5k | Can embed live Vue / Quasar demos; v2 alpha |
| Docusaurus | 3.10.2 (2026-07-10) | 66.7k | React, heaviest |

## Building blocks

| Area | Name | Latest | Note |
|---|---|---|---|
| Highlighting | Pygments | 2.21.0 | Keep. No Mermaid lexer, so the project has its own (`MermaidLexer`) |
| Highlighting | Shiki | 4.6.0 (2026-11-02) | VS Code grammars incl. Mermaid and Vue; Node only |
| Code blocks | Expressive Code | 0.44.3 | Shiki based, text markers, plugin API |
| Code blocks | Code Hike | 1.1.0 (2026-03) | Closest idea to cross-comments (annotation handlers); React / MDX; quiet since March |
| Markers | tree-sitter-language-pack | 1.23.1 | Optional: tie markers to syntax nodes, not text |
| Markdown | markdown-it-py | 4.2.0 | In use. `mdit-py-plugins` 0.6.1 if containers or attrs are ever needed |
| Diagrams | Mermaid | 12.3.0 (2026-11-03) | In use, pinned to 12.2.0 (2026-10-13) on purpose: a release at least two weeks old |
| Diagrams | D2 / Kroki | 0.9.0 / 0.34.0 | Nicer layouts / many formats; extra binary or server |
| Visual tests | Playwright (Python) | 1.64.1 | In use |
| Visual tests | pixelmatch-py / odiff | 0.4.0 / 4.5.0 | Diff pictures with tolerance |
| Visual tests | Lost Pixel | archived 2026-04 | Avoid |

## Projects to learn from

| Project | Lesson |
|---|---|
| component-party.dev (3.3k, active) | Same component in many frameworks, with framework toggles: the closest model for this UX |
| hyperpolyglot.org | Cross-reference tables, like the summary table here |
| 7GUIs | Seven small GUI tasks: a ready step list for the Events section |
| lissy93/framework-benchmarks | Same app in 10 frameworks, tested with Playwright |
| starlight-codeblocks | A side-column annotation layout worth borrowing |

## Sources

PyPI JSON API (`pypi.org/pypi/<pkg>/json`), npm registry (`registry.npmjs.org/<pkg>`), GitHub search API
(stars, last push), and release pages: squidfunk/mkdocs-material, zensical/zensical, quarto-dev/quarto-cli,
mermaid-js/mermaid, d2lang/d2, yuzutech/kroki, lost-pixel/lost-pixel, astral-sh/setup-uv,
actions/deploy-pages, docusaurus.io/changelog, vitepress.dev/guide/i18n, prek.j178.dev.
zensical.org, quarto.org and expressive-code.com were not reachable from this session, so their
feature claims come from release pages and search results.
