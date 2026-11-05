"""A mini NiceGUI: Python builds an element tree, a server sends it, Vue draws it."""

import json
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


class Element:
    """One node of the tree. Elements made inside its `with` block become its children."""

    stack = []  # the elements whose `with` block is open right now

    def __init__(self, tag, style=None):
        self.tag, self.style, self.children = tag, style or {}, []
        if Element.stack:
            Element.stack[-1].children.append(self)

    def __enter__(self):
        Element.stack.append(self)
        return self

    def __exit__(self, *_):
        Element.stack.pop()

    def to_dict(self):
        return {'tag': self.tag, 'style': self.style, 'children': [c.to_dict() for c in self.children]}


BOX = {'width': '200px', 'height': '120px', 'border': '2px solid #333', 'box-sizing': 'border-box'}


def build():
    with Element('div', {'padding': '16px'}) as page:  # like NiceGUI's content area
        with Element('div', {'display': 'flex', 'flex-wrap': 'wrap', 'gap': '16px'}):  # like ui.row()
            Element('div', BOX)  # left
            Element('div', BOX)  # right
    return page


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>2.2 Mini NiceGUI (Vue 3)</title>
  <style>body { margin: 0; }</style>
</head>
<body>
  <div id="app"></div>
  <script type="module">
    import { createApp, h } from 'https://cdn.jsdelivr.net/npm/vue@3/dist/vue.esm-browser.prod.js'

    const tree = __TREE__
    const render = node => h(node.tag, { style: node.style }, node.children.map(render))

    createApp({ render: () => render(tree) }).mount('#app')
  </script>
</body>
</html>
"""

app = FastAPI()


@app.get('/', response_class=HTMLResponse)
def index():
    return PAGE.replace('__TREE__', json.dumps(build().to_dict()))


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('PORT', '8080')))
