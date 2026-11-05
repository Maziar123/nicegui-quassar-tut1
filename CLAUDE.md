# Project notes for Claude

Student tutorial: the same page (two empty 200×120 rectangles side by side, 16px gap) built five ways, from plain Vue 3 to NiceGUI. See README.md for the step list.

## Rules

- `design/wireframe-tv.html` is the only wireframe. Follow it for any page layout work, and change it (not a new file) when the design changes. It targets a 4K / 8K TV: Quasar & NiceGUI & xxx side-by-side cross-reference and tutorial.
- `docs/index.html` is generated. Never edit it by hand. Change `steps/*`, `tutorial/build.py` or `tutorial/template.html`, then run `python tutorial/build.py` and commit the regenerated page together with the source change.
- Every file in `steps/` must stay runnable on its own. Test a change before committing:
  - HTML steps: open in headless Chrome and take a screenshot.
  - Python steps: run with `show=False, reload=False` (NiceGUI) and fetch the page with curl.
- Layer → code-line mapping in `build.py` uses text markers (`find_range(block, start, end)`), not hard-coded line numbers. If you change a step file, check that its markers still match; the build fails loudly when one doesn't.
- Steps 3 and 5 must render pixel-identical. Note Quasar sets `box-sizing: border-box`, so the Quasar steps draw 200px boxes while plain-HTML steps draw 204px (border outside).
- Audience is students: short sentences, plain words, no em-dash asides on the page.
- Linux instructions target Arch Linux (use a venv; system pip is blocked by PEP 668).

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tutorial/build.py            # rebuild docs/index.html
python steps/step3_nicegui.py       # http://localhost:8080
python steps/step4_mini_nicegui.py  # http://localhost:8080
```

## Versions (tested 2026-11-05)

NiceGUI 4.0.0 (Vue 3.5.44, Quasar 2.35.2 bundled), FastAPI 0.162.0, uvicorn 0.54.0, Pygments 2.21.0.
The HTML steps load `vue@3` / `quasar@2` from jsDelivr/unpkg, which resolve to the newest release in each major version.
