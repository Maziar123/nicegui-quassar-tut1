# Quasar & NiceGUI & Vue 3

A side-by-side cross-reference and tutorial for students. Every step builds the same small page three times, with **Quasar**, **NiceGUI** and plain **Vue 3**, and shows the three versions next to each other. Numbered cross-comments link the matching lines, and a screenshot proves the three pages look the same.

The page is made for a 4K / 8K classroom TV. It also works on a laptop and a phone.

**Open the tutorial:** [`docs/index.html`](docs/index.html). Each step also has its own page in [`docs/steps/`](docs/steps/).

On every page, the top bar lets you hide or show a column, change the text size (A− / A / A+) and switch the theme (Auto / Light / Dark). Keys: `1` `2` `3` toggle a column, `C` steps through cross-comments, `[` `]` move between steps, `Esc` clears the highlight.

## Steps so far

| Step | Folder | Shows |
|---|---|---|
| 1.1 | [`content/01-layout/01-one-box`](content/01-layout/01-one-box) | One empty box: page frame, padding, `box-sizing` |

More steps are planned and listed on the page: two boxes side by side, spacing, the element tree, server to browser, a mini NiceGUI, clicks and updates.

## Run a step yourself

Quasar and Vue columns: open the `.html` file in a browser. They load Vue and Quasar from jsDelivr, so they need internet the first time.

NiceGUI columns need Python. On Arch Linux, use a virtual environment, because the system pip is blocked (PEP 668):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python content/01-layout/01-one-box/nicegui_app.py   # opens http://localhost:8080
```

## Change the tutorial

`docs/` is generated. Edit `content/` or `tutorial/`, then rebuild:

```bash
pip install -r requirements-dev.txt
playwright install chromium         # once
python tutorial/shoot.py            # screenshots + pixel compare, after changing a column file
python tutorial/build.py            # writes docs/
python -m pytest                    # checks markers, translations and the build
```

How it fits together, how to add a step, the template blocks, and how to add a language are in [`AGENTS.md`](AGENTS.md). The layout follows [`design/wireframe-tv.html`](design/wireframe-tv.html).

## Layout

```
content/                 the tutorial text, the column files and their screenshots
tutorial/model.py        reads content/ into typed objects
tutorial/build.py        renders them with the templates into docs/
tutorial/shoot.py        screenshots every column and compares the pixels
tutorial/templates/      Jinja2 page, step and block templates
tutorial/assets/         site.css and site.js, shared by every page
tutorial/i18n/           UI strings (English now; more languages can be added)
docs/                    the built site (generated, committed for GitHub Pages)
tests/                   pytest tests
design/wireframe-tv.html the layout to follow
steps/                   older stand-alone samples, kept as material for Section 2
```

To publish with GitHub Pages: Settings → Pages → Deploy from a branch → `main` / `docs`.

## Tested with

NiceGUI 4.0.0 (bundles Vue 3.5.44 and Quasar 2.35.2), Vue 3.5.45 and Quasar 2.35.2 from the CDN, FastAPI 0.162.0, uvicorn 0.54.0, Jinja2 3.1.6, Pygments 2.21.0, Playwright 1.64.1, pytest 9.2.0 with headless Chromium. Tested 5 November 2026. In Step 1.1, the three columns render identical pixels.
