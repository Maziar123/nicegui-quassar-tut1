# AGENTS.md

Guide for coding agents (and people) working on this repository.
`CLAUDE.md` is a symlink to this file: edit `AGENTS.md` only. (On Windows, enable git symlinks,
`git config core.symlinks true`, or `CLAUDE.md` checks out as a one-line text file.)

## What this is

**Quasar & NiceGUI & Vue 3: side-by-side cross-reference and tutorial.** A student tutorial.
Every step builds the same small page three times (Quasar, NiceGUI, plain Vue 3) and shows the three
versions side by side. Numbered cross-comments link the matching lines, and a screenshot proves the
three pages render the same pixels.

The page is made for a 4K / 8K classroom TV, and it still works on a laptop or a phone.
The layout follows **`design/wireframe-tv.html`**. It is the only wireframe: follow it, and change it
(not a new file) when the design changes.

## Layout

```
content/                         what the tutorial says (data, not layout)
  site.toml                      title, lead, the columns, setup text, languages
  NN-name/section.toml           one section: name, about, planned step names
  NN-name/NN-name/               one step
    step.toml                    name, intro, column notes, run / open, try_it, cross-comments
    step.html                    optional: overrides blocks of tutorial/templates/step.html
    1-name.md, 2-name.md         optional Markdown blocks below the screenshot, in file-name order
    picture.svg                  the one picture next to the intro (use currentColor)
    quasar.html                  column 1, runs on its own in a browser
    nicegui_app.py               column 2, runs on its own with python
    vue.html                     column 3, runs on its own in a browser
                                 (a column file is <id>.html / <id>.py or <id>_<name>; vue-old.html is ignored)
    shots/                       made by tutorial/shoot.py (PNGs + result.json), committed
tutorial/
  model.py                       reads content/ into typed objects (Site, Section, Step, Cross, Code, Shots)
  steps.py                       find a step by number (`./run steps`, `./run nicegui 1.1`)
  mdrender.py                    Markdown: Pygments code fences, Mermaid + HTML code/preview blocks
  build.py                       renders the model with the templates into docs/
  shoot.py                       screenshots every column and compares the pixels (uses model.py)
  templates/                     Jinja2 templates (see "Templates and blocks")
  assets/site.css, site.js       shared by every page; copied to docs/assets/
  i18n/en.toml                   every UI string
docs/                            GENERATED. Never edit by hand. Published with GitHub Pages
  index.html                     summary + every section, each step embedded
  steps/<s>-<n>.html             each step on its own page
  assets/                        site.css, site.js, shots/ (only the screenshots a page shows)
tests/test_model.py              markers, translations, Markdown fences, build safety, build smoke test
tests/test_browser.py            the built site in headless Chromium (layout, scroll, cross-comments, Mermaid)
pyproject.toml, uv.lock          dependencies (runtime + dev group) and tool settings; the exact lock
requirements.txt                 exported from uv.lock for plain pip (do not edit)
justfile                         every project command (`./run` lists them)
run                              root shortcut: ./run <command> = uv run just <command>
.pre-commit-config.yaml          git hooks (prek); .github/ CI, Pages deploy, Dependabot
design/wireframe-tv.html         the layout to follow
design/tooling-2026-11.md        survey of frameworks and tools (why the generator stays custom; what to adopt next)
steps/                           older stand-alone samples (material for Section 2), kept runnable
```

## Toolbox and commands

One tool installs everything: **uv**. On Arch Linux: `sudo pacman -S uv` (or see docs.astral.sh/uv).
uv manages the Python version (`.python-version`), the virtual environment (`.venv`) and the exact
package versions (`uv.lock`), so the system pip and PEP 668 never get in the way.

```bash
./run                   # list every command (first run creates .venv from uv.lock by itself)
./run setup             # once: git hooks (prek) + Chromium for screenshots and browser tests
./run serve             # build and open the site on http://localhost:8000
./run nicegui 1.1       # run the NiceGUI column of step 1.1
./run open 1.1 vue      # open an HTML column (quasar / vue) in the browser
```

`./run X` is exactly `uv run just X`: the root `run` script only checks that uv is installed.

| Command | Does |
|---|---|
| `just shoot` | screenshot every column, compare pixels, write `shots/` (after changing a column file) |
| `just build` | build the site into `docs/` |
| `just serve` | build, then serve `docs/` on http://localhost:8000 and open the browser |
| `just steps` | list the steps: number, name, folder, column files (`tutorial/steps.py`) |
| `just nicegui 1.1` / `just open 1.1 vue` | run a NiceGUI column / open an HTML column, by step number |
| `just test` / `just test-browser` | fast tests / browser tests in headless Chromium |
| `just lint` / `just fmt` | ruff check + format check / format and fix |
| `just reqs` | write `requirements.txt` from `uv.lock` (after changing dependencies) |
| `just ci` | everything CI runs: lint, requirements, tests, browser tests, docs up to date |
| `just upgrade` | update the indirect packages in `uv.lock`, then `requirements.txt`, screenshots and `docs/` (direct packages: edit their `==` in `pyproject.toml` first) |

Tools (all pinned in `pyproject.toml` → `uv.lock`, so every machine and CI use the same versions):
uv (environment), ruff (lint + format, settings in `pyproject.toml`), pytest (`tests/`), Playwright
(screenshots, browser tests), prek (git hooks from `.pre-commit-config.yaml`; pre-commit compatible),
just (`justfile`). Dependencies live only in `pyproject.toml`; never edit `uv.lock` or `requirements.txt`
by hand (`requirements.txt` is exported for students who use plain pip, and a check keeps it in sync).

Git hooks (after `just setup`) run on every commit: ruff check, ruff format, requirements check, fast
tests, and `build.py --check`. CI (`.github/workflows/ci.yml`) runs `just ci` on every push and pull
request. `.github/workflows/pages.yml` publishes `docs/` (Settings → Pages → Source: GitHub Actions).
Dependabot opens monthly update pull requests for the GitHub Actions only. Python packages are
updated by hand (`./run upgrade`), because a new NiceGUI or Pygments can change the pages: the
screenshots and `docs/` must be redone and looked at. CI fetches the pinned Mermaid from npm, so the
browser tests draw diagrams there too; in CI a missing Chromium fails the run instead of skipping.
`.gitattributes` keeps every file LF (the bash `run` script and the screenshot hashes need exact bytes).

Machine settings go in a git-ignored `.env` (read by `just`): `XREF_CHROMIUM=/path/to/chromium` uses
an existing browser, `XREF_NPM_DIR=/path` serves CDN files from unpacked npm packages (when the CDN is
blocked; also lets the browser tests draw Mermaid).

`ln -s AGENTS.md CLAUDE.md` restores the symlink if it is ever lost.

`build.py --out DIR` writes somewhere else (the tests use a temp folder). The build renders into a
temporary folder and swaps the result in only when everything worked; the swap moves the old entries
aside first and puts them back if it fails half-way, so `docs/` is always the old site or the new one. `DIR/.xref-build.json` lists what the build owns (`index.html`, `steps/`, `assets/`,
`<lang>/`); those are replaced, a language removed from `site.toml` is cleaned up, and other files
(a `CNAME`, say) are kept. A non-empty folder without that manifest is refused (`docs/` itself is allowed).

`build.py --check` builds into a temporary folder and fails, listing the files, when `docs/` differs.

`shoot.py` options: `--chromium PATH` (or `XREF_CHROMIUM`) uses an existing Chromium. `--npm-dir DIR`
(or `XREF_NPM_DIR`) serves the CDN files from unpacked npm packages (`DIR/vue/`, `DIR/quasar/`,
`DIR/mermaid/`) when jsDelivr / unpkg are blocked. They are the same files, because both CDNs mirror the
npm registry. When two columns differ, `shots/diff-<column>.png` shows the differing pixels in red.

## Templates and blocks

Jinja2, autoescape on, `StrictUndefined` (a typo fails the build). Templates get objects from
`tutorial/model.py`, not dicts: `step.note(c.id).run`, `x.refs`, `r.builtin`, `sh.urls`. UI strings are
`t.<key>` (a namespace, so no key can collide with a dict method).

- `base.html`: page skeleton. Blocks: `title`, `description`, `body_class`, `main`. Includes
  `partials/topbar.html`, `partials/rail.html`, `partials/footer.html`. With more than one language,
  every page gets `<link rel="alternate" hreflang>` links and a language switcher in the top bar
  (names from `name` in each `i18n/<lang>.toml`).
- `index.html`: summary (`partials/summary.html`) + every section, each step embedded.
- `step_page.html`: one step on its own page.
- `step.html`: **the template for every step.** Blocks, top to bottom:
  `head`, `intro`, `columns`, `shots`, `extra` (the step's Markdown blocks), `cross`, `foot`, `nav`.
- `macros.html`: reusable blocks: `chip`, `browser`, `card`, `code_block`, `column`, `shots`, `ref`,
  `cross`, `fence`. Templates render Markdown with `md.inline(text)` and `md.block(text)`.

A step changes its own layout with `content/<section>/<step>/step.html`:

```jinja
{% extends "step.html" %}
{% import "macros.html" as m with context %}   {# a child must import the macros itself #}
{% block extra %}{% call m.card("Title", "aside") %}<p>…</p>{% endcall %}{% endblock %}
```

Each step is rendered twice: once embedded in `docs/index.html` (`mode == "index"`) and once as
`docs/steps/<s>-<n>.html` (`mode == "page"`). Links go through `href()`, `step_link()` and
`step_page_href()`, so they work in both. Never hard-code a link to another page.

## Markdown

Text fields in `site.toml`, `section.toml` and `step.toml` (intro, notes, `say`, `try_it`, captions) are
inline Markdown: `` `code` ``, `**bold**`, links, and inline HTML such as `<kbd>`. Every `*.md` file in a
step folder is a block below the screenshot (`1-why-border.md`, `2-the-road.md`; the number sets the
order). `# Heading` becomes the block title (headings move down three levels inside a step).
Parser: markdown-it-py (CommonMark + tables + strikethrough), HTML allowed (content is ours).

Code fences, info string `lang [preview] [title="…"] [hl=…] [height=…]`:

| Fence | Shows |
|---|---|
| ` ```css title="vue.html" hl=5 ` | highlighted code (Pygments, same colours as the columns), line 5 marked |
| ` ```mermaid ` | Mermaid code (highlighted by our `MermaidLexer`) and the drawn diagram, Both / Code / Preview |
| ` ```html preview height=200 ` | HTML code and a live preview in a sandboxed iframe (no scripts run) |

The markup of a fence is the `fence` macro in `macros.html`, not Python, so it is styled like every
other block. Mermaid loads only on pages with a diagram, from the pinned URL in `[libs]` of
`content/site.toml` (`mermaid@12.2.0`). It redraws when the theme or text size changes, and when it
cannot load (offline), the block shows the code with a message. To update Mermaid: pick a release
at least two weeks old, change the URL, and look at every diagram in both themes.

A translation of a block sits next to it: `1-why-border.fa.md`. A missing translation falls back to English.

## Cross-comments (step.toml)

```toml
[[cross]]
idea = "The box"                                    # short name, also used in the summary table
say  = "One empty div, 200 × 120 px."
quasar  = { at = [["width: 200px"]], hint = '<div style="…">' }
nicegui = { at = [["BOX = "], ["ui.element('div')"]], hint = "ui.element('div')" }
vue     = { builtin = "what the library does for you" }   # when there is no line to show
```

`at` is a list of ranges `[start]` or `[start, end]`. A marker matches the first line that contains it.
`"=x"` matches a line that is `x` after trimming, and `"==x"` matches a line that is exactly `x`.
Markers are text, never line numbers. The build stops with the file name if a marker no longer
matches. After editing a column file, run the build and fix any marker it reports.

## CSS and JS

- One stylesheet and one script for every page: `tutorial/assets/site.css`, `site.js`. No inline styles
  in templates except the tiny first-paint script in `base.html`.
- Sizes use `--u = min(1vw, 1.7778vh)` (1% of a 16:9 screen), so 4K and 8K look the same at any OS
  scaling. Text uses `--t = --u × --z`, where `--z` is the text-size setting (A− / A / A+).
- Colours are tokens on `:root`, with dark values under `prefers-color-scheme` and `[data-theme="dark"]`.
  Column colours come from `.c-<id>` or `[data-col="<id>"]` as `--c` (line) and `--cb` (fill).
- Use logical properties (`margin-inline-start`, `border-inline-start`, `text-align: start`), not left / right,
  so right-to-left languages work. Code is always `dir="ltr"`.
- The top bar holds: column toggles, key hints, text size (A− / A / A+) and theme (Auto / Light / Dark).
  `data-col` marks things that belong to a column (site.js hides them with the column); other
  per-column data uses its own attribute (`data-copy`, `data-code`).
  Settings live in `localStorage` under `xref-*`. Every read and write is wrapped in try / catch.
- Below 1100 px CSS width, the rail moves to the top and the columns become tabs. Check 390 px too:
  the page must never scroll sideways.

## Languages (ready, only English now)

- UI strings: `tutorial/i18n/<lang>.toml`. A missing key falls back to English.
- Content: put `step.<lang>.toml`, `section.<lang>.toml` or `site.<lang>.toml` next to the English file,
  with only the translated keys. Lists of tables (`[[cross]]`) merge item by item.
- Turn a language on: add its code (like `fa` or `pt-BR`) to `languages` in `content/site.toml`.
  It builds to `docs/<lang>/` and shares `docs/assets/`. The model refuses malformed codes, because
  each one names a folder the build deletes and rewrites. Set `dir = "rtl"` in its i18n file for Persian, Arabic or Hebrew.
- Strings with `{name}` placeholders are filled with `.format()`. When a value holds HTML, escape the
  string first: `(t.key | e).format(file=markup)`.

## Rules

- `docs/` is generated. Change `content/` or `tutorial/`, run `just build` and `just ci`, and commit the
  source and the regenerated `docs/` together. CI fails when `docs/` is out of date.
- A bug fix comes with a test that fails without the fix. Check it: put the bug back, see the test fail.
- Every column file must run on its own. Test before committing:
  - all columns: `python tutorial/shoot.py`. It must report `identical`, unless the step is about a
    difference, in which case say so in the step text. It stores a sha256 of each column file; when a
    file changes, is removed, or is added after the screenshots, the build warns and the page shows the
    screenshot as out of date.
  - NiceGUI columns also by hand: run with `show=False, reload=False` and fetch the page with curl.
- Never name a column file `nicegui.py`: it hides the real `nicegui` package. Use `nicegui_app.py`.
- `just test-browser` checks the built page at 1920 × 1080, 1440 × 900 and 390 × 844, at normal and
  large text: no page or console errors (blocked fonts and CDN aside), no sideways scroll, the page stays
  where it is scrolled, every cross-comment lights exactly its lines, `[` `]` move by position, copied
  code has no cross-comment numbers, a broken diagram leaves nothing behind, and axe finds no serious
  accessibility problem. Tests run with reduced motion and wait for diagrams to settle. Still look at
  new layout work yourself, in both themes.
- In site.js, never call `scrollIntoView()` on something inside the sticky rail: it scrolls the window
  too and locks the page on narrow screens. Scroll the rail itself.
- Quasar sets `box-sizing: border-box` on everything. Plain Vue does not, so a plain column writes it
  by hand to match.
- Accessibility is tested (axe-core in `tests/test_browser.py`): no serious or critical problem in either
  theme. Text needs 4.5:1 contrast: column colours are also text colours, so a new colour must pass on
  white, on the page background and on its own fill. Every page has one `h1` and no skipped heading
  level: templates use `H.title` / `H.sub` (3 / 4 inside the index, 1 / 2 on a step's own page) and
  style headings by class (`step-title`, `card-title`, `block-title`, `md-h1`…), never by tag. A button's
  visible text must be part of its accessible name (add words with `<span class="sr">`, not aria-label).
- Code tokens carry the `tk-` prefix (`tk-k`, `tk-s`, …; `model.TOKEN_PREFIX`). Pygments' bare short
  names clashed twice: `cp` with the code + preview block (now `cpv`) and `sr` with the screen-reader
  class `.sr`, which made regex literals invisible. Never use a `tk-` class for anything else.
- Read and write every text file with `encoding='utf-8'` (Windows defaults to cp1252, which cannot
  even write the page's `A−`). A test checks every `read_text` / `write_text` call.
- Audience is students: short sentences, plain words, no em-dash asides on the page.
- Versions in use (tested 2026-11-05): NiceGUI 4.0.0 (bundles Vue 3.5.44, Quasar 2.35.2), FastAPI 0.162.0,
  uvicorn 0.54.0, Pygments 2.21.0, Jinja2 3.1.6, markdown-it-py 4.2.0, Playwright 1.64.1, pytest 9.2.0,
  ruff 0.17.3, prek 0.5.10, just 1.59.0 (rust-just), uv 0.13.7, axe-playwright-python 0.1.8 (axe-core 4.12),
  Mermaid 12.2.0 (browser), Python 3.13. The HTML columns load `vue@3` and
  `quasar@2` from jsDelivr (Vue 3.5.45, Quasar 2.35.2 today).

## Adding a step

1. Copy a step folder, for example `content/01-layout/01-one-box` to `content/01-layout/02-two-boxes`.
   Folder order sets the number. Remove that name from `planned` in `section.toml`.
2. Write the three column files. Keep them short and make them render the same pixels.
3. Edit `step.toml`: name, intro, notes, `run` (shell command) or `open` (file for the browser), try_it, cross-comments.
4. Draw `picture.svg` with `currentColor`, so it works in both themes.
5. `python tutorial/shoot.py`, then `python tutorial/build.py`. Look at the page, then commit everything.
