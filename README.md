# Vue to NiceGUI, layer by layer

A step-by-step tutorial for students. One tiny page (two empty rectangles side by side) is built five different ways, from plain Vue 3 up to NiceGUI, so you can see which layers each approach adds.

**Open the tutorial:** [`docs/index.html`](docs/index.html). It is one self-contained HTML file with the code, a picture of what the browser shows, and an interactive layer diagram for every step. Click a layer to light up the code that belongs to it.

## The steps

| Step | File | What it shows | Runs with |
|---|---|---|---|
| 1 | [`steps/step1-empty-rectangle.html`](steps/step1-empty-rectangle.html) | One empty rectangle with Vue 3 | A browser |
| 2 | [`steps/step2-two-rectangles.html`](steps/step2-two-rectangles.html) | Two rectangles side by side (flexbox) | A browser |
| 3 | [`steps/step3_nicegui.py`](steps/step3_nicegui.py) | The same page in NiceGUI (Python) | Python + NiceGUI |
| 4 | [`steps/step4_mini_nicegui.py`](steps/step4_mini_nicegui.py) | The NiceGUI road built by hand: element tree → FastAPI → JSON → Vue `h()` | Python + FastAPI + uvicorn |
| 5 | [`steps/step5_vue_quasar.html`](steps/step5_vue_quasar.html) | The same road with no Python: Vue 3 + Quasar 2 | A browser |

[`steps/step3_sent_to_browser.json`](steps/step3_sent_to_browser.json) is the element tree NiceGUI actually sent to the browser for Step 3, captured from a real run.

## Run the steps

HTML steps (1, 2, 5): open the file in a browser. They load Vue and Quasar from a CDN, so they need internet the first time.

Python steps (3, 4), on Arch Linux or anywhere else. Arch's system Python refuses `pip install` (PEP 668), so use a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python steps/step3_nicegui.py        # opens http://localhost:8080
python steps/step4_mini_nicegui.py   # serves http://localhost:8080
```

## Rebuild the tutorial page

`docs/index.html` is generated. Edit the files in `steps/` or `tutorial/`, then run:

```bash
python tutorial/build.py
```

The build reads the step files, highlights them with Pygments, works out which code lines belong to each layer, and writes `docs/index.html`. The code on the page is always the code in `steps/`.

To publish the page with GitHub Pages: Settings → Pages → Deploy from a branch → `main` / `docs`.

## Layout

```
steps/              the five tested sample files (+ captured JSON)
tutorial/build.py   generates docs/index.html; step texts and layer data live here
tutorial/template.html   page layout, styles and script
docs/index.html     the built tutorial (generated, committed for easy viewing)
design/wireframe-tv.html the one design wireframe (4K / 8K TV): Quasar & NiceGUI & xxx side by side
```

## Tested with

NiceGUI 4.0.0 (bundles Vue 3.5.44 and Quasar 2.35.2), FastAPI 0.162.0, uvicorn 0.54.0, headless Chrome. Tested 5 November 2026. Steps 3 and 5 were screenshotted and compared: the pixels match.
