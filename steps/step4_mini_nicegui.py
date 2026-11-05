import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


# ── Your code: the element tree (what NiceGUI's ui.* does) ──────────────
class Element:
    stack = []  # the element currently open in a `with` block

    def __init__(self, tag, style=''):
        self.tag, self.style, self.children = tag, style, []
        if Element.stack:
            Element.stack[-1].children.append(self)

    def __enter__(self):
        Element.stack.append(self)
        return self

    def __exit__(self, *_):
        Element.stack.pop()

    def to_dict(self):
        return {'tag': self.tag, 'style': self.style,
                'children': [c.to_dict() for c in self.children]}


RECT = 'width: 200px; height: 120px; border: 2px solid #333'


def build():
    with Element('div', 'display: flex; gap: 16px') as root:  # row
        Element('div', RECT)                                   # left
        Element('div', RECT)                                   # right
    return root


# ── Renderer: the browser page, where Vue turns the JSON into elements ──
PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Step 4 – Mini NiceGUI</title></head>
<body>
  <div id="app"></div>
  <script type="module">
    import { createApp, h } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js'

    const tree = __TREE__
    const render = node => h(node.tag, { style: node.style }, node.children.map(render))

    createApp({ render: () => render(tree) }).mount('#app')
  </script>
</body>
</html>"""


# ── Server: sends the page with the tree inside as JSON ─────────────────
app = FastAPI()


@app.get('/', response_class=HTMLResponse)
def index():
    return PAGE.replace('__TREE__', json.dumps(build().to_dict()))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=8080)
