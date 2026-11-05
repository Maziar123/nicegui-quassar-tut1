# AGENTS.md

Guide for coding agents (and people) working on this repository.

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
    picture.svg                  the one picture next to the intro (use currentColor)
    quasar.html                  column 1, runs on its own in a browser
    nicegui_app.py               column 2, runs on its own with python
    vue.html                     column 3, runs on its own in a browser
    shots/                       made by tutorial/shoot.py (PNGs + result.json), committed
tutorial/
  model.py                       reads content/ into typed objects (Site, Section, Step, Cross, Code, Shots)
  build.py                       renders the model with the templates into docs/
  shoot.py                       screenshots every column and compares the pixels (uses model.py)
  templates/                     Jinja2 templates (see "Templates and blocks")
  assets/site.css, site.js       shared by every page; copied to docs/assets/
  i18n/en.toml                   every UI string
docs/                            GENERATED. Never edit by hand. Published with GitHub Pages
  index.html                     summary + every section, each step embedded
  steps/<s>-<n>.html             each step on its own page
  assets/                        site.css, site.js, shots/ (only the screenshots a page shows)
tests/test_model.py              markers, translation merge, language codes, build smoke test
design/wireframe-tv.html         the layout to follow
steps/                           older stand-alone samples (material for Section 2), kept runnable
```

## Commands

Arch Linux (or anywhere): use a virtual environment, because the system pip is blocked (PEP 668).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # students only need requirements.txt
playwright install chromium           # once, for shoot.py
python tutorial/shoot.py              # after changing any column file
python tutorial/build.py              # after changing anything in content/ or tutorial/
python -m pytest                      # before every commit
python content/01-layout/01-one-box/nicegui_app.py   # run one NiceGUI column
```

`build.py --out DIR` writes somewhere else (the tests use a temp folder). The build renders into a
temporary folder and swaps the result in only when everything worked, so a failed build never leaves a
half-empty `docs/`. `DIR/.xref-build.json` lists what the build owns (`index.html`, `steps/`, `assets/`,
`<lang>/`); those are replaced, a language removed from `site.toml` is cleaned up, and other files
(a `CNAME`, say) are kept. A non-empty folder without that manifest is refused (`docs/` itself is allowed).

`shoot.py` options: `--chromium PATH` uses an existing Chromium. `--npm-dir DIR` serves the CDN files
from unpacked npm packages (`DIR/vue/`, `DIR/quasar/`) when jsDelivr / unpkg are blocked. They are the
same files, because both CDNs mirror the npm registry.

## Templates and blocks

Jinja2, autoescape on, `StrictUndefined` (a typo fails the build). Templates get objects from
`tutorial/model.py`, not dicts: `step.note(c.id).run`, `x.refs`, `r.builtin`, `sh.urls`. UI strings are
`t.<key>` (a namespace, so no key can collide with a dict method).

- `base.html`: page skeleton. Blocks: `title`, `body_class`, `main`. Includes `partials/topbar.html`,
  `partials/rail.html`, `partials/footer.html`.
- `index.html`: summary (`partials/summary.html`) + every section, each step embedded.
- `step_page.html`: one step on its own page.
- `step.html`: **the template for every step.** Blocks, top to bottom:
  `head`, `intro`, `columns`, `shots`, `extra`, `cross`, `foot`, `nav`.
- `macros.html`: reusable blocks: `chip`, `browser`, `card`, `code_block`, `column`, `shots`, `ref`, `cross`.

A step changes its own layout with `content/<section>/<step>/step.html`:

```jinja
{% extends "step.html" %}
{% import "macros.html" as m with context %}   {# a child must import the macros itself #}
{% block extra %}{% call m.card("Title", "aside") %}<p>…</p>{% endcall %}{% endblock %}
```

Each step is rendered twice: once embedded in `docs/index.html` (`mode == "index"`) and once as
`docs/steps/<s>-<n>.html` (`mode == "page"`). Links go through `href()`, `step_link()` and
`step_page_href()`, so they work in both. Never hard-code a link to another page.

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

- `docs/` is generated. Change `content/` or `tutorial/`, run `python tutorial/build.py` and
  `python -m pytest`, and commit the source and the regenerated `docs/` together.
- Every column file must run on its own. Test before committing:
  - all columns: `python tutorial/shoot.py`. It must report `identical`, unless the step is about a
    difference, in which case say so in the step text. It stores a sha256 of each column file; when a
    file changes later, the build warns and the page shows the screenshot as out of date.
  - NiceGUI columns also by hand: run with `show=False, reload=False` and fetch the page with curl.
- Never name a column file `nicegui.py`: it hides the real `nicegui` package. Use `nicegui_app.py`.
- Look at the built page at 1920 × 1080, 1440 × 900 and 390 × 844 in both themes, and check the browser
  console for errors. Also scroll with the mouse wheel on a narrow screen, and try text size A+ three
  times: the page must never scroll sideways.
- In site.js, never call `scrollIntoView()` on something inside the sticky rail: it scrolls the window
  too and locks the page on narrow screens. Scroll the rail itself.
- Quasar sets `box-sizing: border-box` on everything. Plain Vue does not, so a plain column writes it
  by hand to match.
- Audience is students: short sentences, plain words, no em-dash asides on the page.
- Versions in use (tested 2026-11-05): NiceGUI 4.0.0 (bundles Vue 3.5.44, Quasar 2.35.2), FastAPI 0.162.0,
  uvicorn 0.54.0, Pygments 2.21.0, Jinja2 3.1.6, Playwright 1.64.1. The HTML columns load `vue@3` and
  `quasar@2` from jsDelivr (Vue 3.5.45, Quasar 2.35.2 today).

## Adding a step

1. Copy a step folder, for example `content/01-layout/01-one-box` to `content/01-layout/02-two-boxes`.
   Folder order sets the number. Remove that name from `planned` in `section.toml`.
2. Write the three column files. Keep them short and make them render the same pixels.
3. Edit `step.toml`: name, intro, notes, `run` (shell command) or `open` (file for the browser), try_it, cross-comments.
4. Draw `picture.svg` with `currentColor`, so it works in both themes.
5. `python tutorial/shoot.py`, then `python tutorial/build.py`. Look at the page, then commit everything.
