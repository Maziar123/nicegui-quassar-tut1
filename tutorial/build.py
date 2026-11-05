"""Builds docs/index.html from the tested sample files in steps/.

Run from anywhere:  python tutorial/build.py
"""
import difflib
import html
import json
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import HtmlLexer, JsonLexer, PythonLexer

HERE = Path(__file__).parent
ROOT = HERE.parent
FILES = ROOT / 'steps'
LEXERS = {'html': HtmlLexer, 'py': PythonLexer, 'json': JsonLexer}
LANG_LABEL = {'html': 'HTML', 'py': 'Python', 'json': 'JSON'}

# ---------------------------------------------------------------- code blocks
BLOCKS = {
    's1':   ('step1-empty-rectangle.html', 'html'),
    's2':   ('step2-two-rectangles.html', 'html'),
    's3':   ('step3_nicegui.py', 'py'),
    's3j':  ('step3_sent_to_browser.json', 'json'),
    's4':   ('step4_mini_nicegui.py', 'py'),
    's5':   ('step5_vue_quasar.html', 'html'),
}
RAW = {b: (FILES / f).read_text() for b, (f, _) in BLOCKS.items()}


def find_range(block, start, end=None):
    lines = RAW[block].split('\n')
    i = next(n for n, l in enumerate(lines) if start in l)
    if end is None:
        return [i + 1, i + 1]

    def hit(l):
        if end.startswith('=='):
            return l == end[2:]
        if end.startswith('='):
            return l.strip() == end[1:]
        return end in l
    j = next(n for n in range(i, len(lines)) if hit(lines[n]))
    return [i + 1, j + 1]


def all_lines(block):
    return [1, len(RAW[block].rstrip('\n').split('\n'))]


def new_lines(old, new):
    a, b = RAW[old].split('\n'), RAW[new].split('\n')
    out = set()
    for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag in ('insert', 'replace'):
            out.update(range(j1 + 1, j2 + 1))
    return {n for n in out if b[n - 1].strip()}


def render_code(block, new=frozenset(), title=None):
    fname, lang = BLOCKS[block]
    hl = highlight(RAW[block], LEXERS[lang](), HtmlFormatter(nowrap=True))
    rows = hl.rstrip('\n').split('\n')
    lines = ''.join(
        f'<span class="ln{" new" if n in new else ""}" data-n="{n}">{r or " "}</span>'
        for n, r in enumerate(rows, 1))
    legend = '<span class="new-key">+ new in this step</span>' if new else ''
    return f'''
<div class="code" id="code-{block}">
  <div class="code-bar">
    <span class="fname">{html.escape(title or fname)}</span>
    <span class="lang">{LANG_LABEL[lang]}</span>{legend}
    <button class="copy" type="button" data-block="{block}">Copy</button>
  </div>
  <pre><code>{lines}</code></pre>
</div>'''


# ---------------------------------------------------------------- the steps
ROWS = ['Your code', 'Server', 'Element tree', 'Renderer', 'Browser']

STEPS = [
  dict(
    id='step-1', n=1, title='One empty rectangle', stack='HTML + Vue 3',
    goal='Draw a single empty box with Vue 3. One file, no install, no build step.',
    blocks=[('s1', None)], new=None,
    view=dict(url='step1-empty-rectangle.html', pad=8, count=1),
    layers=[
      dict(role='you', name='Your HTML + CSS', sub='.rect style and the #app template', arrow=None,
           refs=[('s1', [('<style>', '</style>'), ('<div id="app">', '=</div>')])]),
      dict(role='none', name='No server', sub='You open the file straight from disk'),
      dict(role='lib', name='Virtual DOM tree', sub='Vue compiles the #app template into it', arrow='Vue reads the template',
           refs=[('s1', [('<div id="app">', '=</div>')])]),
      dict(role='lib', name='Vue 3 renderer', sub="createApp({}).mount('#app')", arrow='tree handed to',
           refs=[('s1', [('<script type="module">', '</script>')])]),
      dict(role='dom', name='Browser DOM', sub='One empty 200 × 120 px div', arrow='creates real elements'),
    ],
    new_points=[
      '<code>.rect</code> gives the box its size (<code>width</code>, <code>height</code>) and its outline (<code>border</code>). Nothing inside it, so it stays empty.',
      '<code>&lt;div id="app"&gt;</code> is the part of the page Vue controls. Everything inside it is Vue\'s template.',
      '<code>import { createApp } from …</code> loads Vue as a modern ES module. <code>vue@3</code> always resolves to the newest Vue 3 release (3.5.44 today).',
      '<code>createApp({}).mount(\'#app\')</code> starts an app with no data yet and attaches it to <code>#app</code>.',
    ],
    run=['Save the file and open it in Firefox or Chromium.', 'It needs internet once, to fetch Vue from the CDN.'],
    cmds=None,
    tryit='Change <code>height</code> to <code>60px</code> and <code>border</code> to <code>2px dashed #333</code>, then reload.',
  ),
  dict(
    id='step-2', n=2, title='Two rectangles side by side', stack='HTML + Vue 3 + flexbox',
    goal='Put two boxes next to each other in one row, with a small gap between them.',
    blocks=[('s2', None)], new=('s1', 's2'),
    view=dict(url='step2-two-rectangles.html', pad=8, count=2),
    layers=[
      dict(role='you', name='Your HTML + CSS', sub='.row flex container and two .rect divs', arrow=None,
           refs=[('s2', [('<style>', '</style>'), ('<div id="app">', '==  </div>')])]),
      dict(role='none', name='No server', sub='You open the file straight from disk'),
      dict(role='lib', name='Virtual DOM tree', sub='Vue compiles the #app template into it', arrow='Vue reads the template',
           refs=[('s2', [('<div class="row">', '==    </div>')])]),
      dict(role='lib', name='Vue 3 renderer', sub="createApp({}).mount('#app')", arrow='tree handed to',
           refs=[('s2', [('<script type="module">', '</script>')])]),
      dict(role='dom', name='Browser DOM', sub='A flex row: two divs, 16 px gap', arrow='creates real elements'),
    ],
    new_points=[
      'A new <code>.row</code> box wraps both rectangles.',
      '<code>display: flex</code> lays its children out side by side instead of stacked.',
      '<code>gap: 16px</code> puts a small space between them. Delete it and they touch.',
      'The second <code>&lt;div class="rect"&gt;</code> reuses the same style.',
    ],
    run=['Open the file in a browser, same as Step 1.'],
    cmds=None,
    tryit='Add <code>justify-content: center;</code> to <code>.row</code> to move the pair to the middle of the page.',
  ),
  dict(
    id='step-3', n=3, title='The same page in NiceGUI', stack='Python + NiceGUI 4.0',
    goal='Write the same two rectangles in Python. NiceGUI builds the page and sends it to the browser.',
    blocks=[('s3', None), ('s3j', 'What NiceGUI sends to the browser (captured from a real run)')], new=None,
    view=dict(url='localhost:8080', pad=16, count=2, bb=True),
    layers=[
      dict(role='you', name='Your Python', sub='ui.row() and ui.element()', arrow=None,
           refs=[('s3', [('RECT =', None), ('def root', '# right')])]),
      dict(role='lib', name='NiceGUI server', sub='FastAPI, started by ui.run()', arrow='runs inside',
           refs=[('s3', [('ui.run(', None)])]),
      dict(role='lib', name='JSON element tree', sub='7 elements, sent with the page', arrow='turned into',
           refs=[('s3j', [None])]),
      dict(role='lib', name='Vue 3.5 + Quasar 2.35', sub='nicegui.js renders the tree', arrow='rendered by',
           note='inside the NiceGUI package'),
      dict(role='dom', name='Browser DOM', sub='Same flex row, plus page padding', arrow='creates real elements'),
    ],
    new_points=[
      '<code>with ui.row():</code> is the <code>.row</code> flex box. Anything created inside the <code>with</code> block becomes its child.',
      '<code>ui.element(\'div\').style(RECT)</code> is one <code>&lt;div class="rect"&gt;</code>.',
      '<code>ui.run(root)</code> replaces <code>createApp().mount()</code>. It starts a web server, and the browser connects to it.',
      'Your Python never reaches the browser. NiceGUI turns it into the JSON tree shown under the code, and Vue + Quasar draw that tree.',
      'Quasar sets <code>box-sizing: border-box</code> on every element, so each box is 200 px wide including its border. In Steps 1, 2 and 4 the border sits outside, making 204 px.',
      'NiceGUI wraps your content in <code>q-layout › q-page-container › q-page › nicegui-content</code>. That wrapper adds 16 px of padding.',
    ],
    run=['NiceGUI needs Python 3.10 or newer. On Arch Linux, pip refuses to install into the system Python, so use a virtual environment:'],
    cmds='python -m venv .venv\nsource .venv/bin/activate\npip install nicegui\npython step3_nicegui.py',
    tryit='Open the page source in your browser (Ctrl+U) and search for <code>"elements"</code>. You will find the same JSON shown here.',
  ),
  dict(
    id='step-4', n=4, title='Build the NiceGUI road by hand', stack='Python + FastAPI + Vue 3',
    goal='Rebuild what NiceGUI does in about 50 lines: a Python element tree, a server, JSON, and a Vue render function.',
    blocks=[('s4', None)], new=None,
    view=dict(url='localhost:8080', pad=8, count=2),
    layers=[
      dict(role='you', name='Element class + build()', sub='Your own ui.row / ui.element', arrow=None,
           refs=[('s4', [('class Element', 'Element.stack.pop()'), ('RECT =', None), ('def build', 'return root')])]),
      dict(role='you', name='FastAPI route  /', sub='You write the server', arrow='runs inside',
           refs=[('s4', [('app = FastAPI()', 'return PAGE.replace'), ("if __name__", 'uvicorn.run')])]),
      dict(role='you', name='JSON element tree', sub='to_dict() + json.dumps()', arrow='turned into',
           refs=[('s4', [('def to_dict', "for c in self.children]"), ('return PAGE.replace', None), ('const tree = __TREE__', None)])]),
      dict(role='you', name="Your render() + Vue's h()", sub='Walks the tree, one element per node', arrow='rendered by',
           refs=[('s4', [("import { createApp, h }", "createApp({ render")])]),
      dict(role='dom', name='Browser DOM', sub='Same flex row, no extra padding', arrow='creates real elements'),
    ],
    new_points=[
      '<code>Element.stack</code> remembers which element is open in a <code>with</code> block. New elements become its children. This is how NiceGUI nesting works too.',
      '<code>to_dict()</code> turns the whole tree into plain dicts, ready for <code>json.dumps()</code>.',
      'The server puts that JSON into the page in place of <code>__TREE__</code>.',
      '<code>h(tag, props, children)</code> is Vue\'s way to create an element from code. <code>render</code> calls itself for each child, so any depth works.',
      'Missing compared with NiceGUI: the websocket (Python can\'t change the page after it loads), Quasar components, and one tree per visitor.',
    ],
    run=['On Arch Linux, use a virtual environment (FastAPI and uvicorn come with NiceGUI, or install them alone):'],
    cmds='python -m venv .venv\nsource .venv/bin/activate\npip install fastapi uvicorn\npython step4_mini_nicegui.py',
    tryit="Add a third <code>Element('div', RECT)</code> inside <code>build()</code> and reload. Then <code>print(json.dumps(build().to_dict(), indent=2))</code> to see the tree.",
  ),
  dict(
    id='step-5', n=5, title='Same road, no Python', stack='HTML + Vue 3.5 + Quasar 2.35',
    goal="Keep NiceGUI's browser half (the same tree, Vue 3 and Quasar 2) and drop Python and NiceGUI completely.",
    blocks=[('s5', None)], new=None,
    view=dict(url='step5_vue_quasar.html', pad=16, count=2, bb=True),
    layers=[
      dict(role='you', name='Your HTML + JS', sub='Two NiceGUI CSS rules and the tree', arrow=None,
           refs=[('s5', [('<style>', '</style>'), ('const RECT', None)])]),
      dict(role='none', name='No server', sub='The tree is written in the page'),
      dict(role='you', name='Element tree as a JS object', sub='Same shape as the JSON in Step 3', arrow='written as',
           refs=[('s5', [('const tree =', '==      ]}')])]),
      dict(role='lib', name='Vue 3.5 + Quasar 2.35', sub='Loaded the same way NiceGUI loads them', arrow='rendered by',
           refs=[('s5', [('quasar.prod.css', None), ('<script type="importmap">', '</script>'),
                         ("import * as Vue from 'vue'", 'globalThis.Vue = Vue'), ('<script defer src', None),
                         ('function render', '.use(Quasar)')])]),
      dict(role='dom', name='Browser DOM', sub='Pixel-identical to Step 3', arrow='creates real elements'),
    ],
    new_points=[
      'The import map lets the code say <code>from \'vue\'</code>. Then <code>globalThis.Vue = Vue</code> exposes Vue for Quasar. NiceGUI does exactly this.',
      'Quasar\'s UMD script registers <code>q-layout</code>, <code>q-page</code> and the other components once you call <code>.use(Quasar)</code>.',
      '<code>render()</code> sends <code>q-*</code> tags to <code>resolveComponent()</code> (Quasar components) and everything else to plain HTML tags.',
      'Only the two NiceGUI CSS rules this layout needs are copied: <code>.nicegui-content</code> and <code>.nicegui-row</code>.',
      'Checked in Chrome: this page and Step 3 produce the same pixels.',
    ],
    run=['Open the file in a browser. It needs internet once, to fetch Vue and Quasar from the CDN.'],
    cmds=None,
    tryit="Add <code>{ tag: 'q-btn', props: { label: 'Click me', color: 'primary' } }</code> to the row's children. A real Quasar button appears.",
  ),
]


def layer_html(step, i, L):
    role = L['role']
    if role == 'none':
        return f'''<div class="layer ghost" data-row="{ROWS[i]}">
  <span class="row-name">{ROWS[i]}</span>
  <span class="layer-name">{L["name"]}</span><span class="layer-sub">{L["sub"]}</span>
</div>'''
    refs = []
    for block, marks in L.get('refs', []):
        rng = [all_lines(block) if m is None else find_range(block, *m) for m in marks]
        refs.append([block, rng])
    if refs:
        parts = []
        for block, rng in refs:
            label = 'JSON' if block.endswith('j') else ''
            rng.sort()
            txt = ', '.join(f'{a}' if a == b else f'{a}–{b}' for a, b in rng)
            parts.append(f'{label} lines {txt}'.strip())
        reftxt = '; '.join(parts)
    else:
        reftxt = L.get('note', 'see the view')
    tag = 'button type="button"' if refs else 'div'
    end = 'button' if refs else 'div'
    pressed = ' aria-pressed="false"' if refs else ''
    return f'''<{tag} class="layer {role}" data-row="{ROWS[i]}" data-refs='{json.dumps(refs)}'{pressed}>
  <span class="row-name">{ROWS[i]}</span>
  <span class="layer-name">{html.escape(L["name"])}</span><span class="layer-sub">{html.escape(L["sub"])}</span>
  <span class="layer-ref">{reftxt}</span>
</{end}>'''


def arrow_html(L):
    if L['role'] == 'none' or not L.get('arrow'):
        return '<div class="arrow quiet" aria-hidden="true"></div>'
    return f'<div class="arrow"><span>{L["arrow"]}</span></div>'


def view_html(v, small=False):
    rects = ''.join('<div class="rect"></div>' for _ in range(v['count']))
    return f'''<div class="browser{' small' if small else ''}">
  <div class="browser-bar"><i></i><i></i><i></i><span class="url">{v["url"]}</span></div>
  <div class="canvas{' bb' if v.get('bb') else ''}" style="padding:{v["pad"]}px"><div class="row-demo">{rects}</div></div>
</div>'''


def step_html(s):
    new = new_lines(*s['new']) if s['new'] else frozenset()
    code = ''.join(render_code(b, new if b == s['blocks'][0][0] else frozenset(), t) for b, t in s['blocks'])
    stack = []
    for i, L in enumerate(s['layers']):
        if i:
            stack.append(arrow_html(L))
        stack.append(layer_html(s, i, L))
    points = ''.join(f'<li>{p}</li>' for p in s['new_points'])
    run = ''.join(f'<p>{r}</p>' for r in s['run'])
    cmds = f'<pre class="cmd"><code>{html.escape(s["cmds"])}</code></pre>' if s['cmds'] else ''
    files = ', '.join(f'<code>{BLOCKS[b][0]}</code>' for b, _ in s['blocks'][:1])
    return f'''
<section class="step" id="{s["id"]}" data-step="{s["n"]}">
  <header class="step-head">
    <span class="num">{s["n"]}</span>
    <div><h2>{s["title"]}</h2><p class="stack">{s["stack"]} · {files}</p></div>
  </header>
  <p class="goal">{s["goal"]}</p>
  <div class="step-grid">
    <div class="code-col">{code}</div>
    <div class="side">
      <figure class="view-fig">
        <figcaption class="label">What the browser shows</figcaption>
        {view_html(s["view"])}
      </figure>
      <figure class="layers-fig">
        <figcaption class="label">Layers, top to bottom <span class="hint">Click a layer to light up its code</span></figcaption>
        <div class="stack-diagram" role="group" aria-label="Layers for step {s["n"]}">{''.join(stack)}</div>
      </figure>
    </div>
  </div>
  <div class="notes">
    <div class="note"><h3>What the code does</h3><ul>{points}</ul></div>
    <div class="note"><h3>Run it</h3>{run}{cmds}</div>
    <div class="note try"><h3>Try it</h3><p>{s["tryit"]}</p></div>
  </div>
</section>'''


# ---------------------------------------------------------------- comparison
ROADS = [('Plain Vue', 'Steps 1–2', 1), ('NiceGUI', 'Step 3', 2), ('Hand-built', 'Step 4', 3), ('Vue + Quasar', 'Step 5', 4)]


def loc(block):
    return sum(1 for l in RAW[block].split('\n') if l.strip())


def compare_html():
    head = '<div class="mx-h"></div>' + ''.join(
        f'<div class="mx-h"><b>{n}</b><span>{s}</span></div>' for n, s, _ in ROADS)
    body = ''
    for r, row in enumerate(ROWS):
        body += f'<div class="mx-row">{row}</div>'
        for _, _, si in ROADS:
            L = STEPS[si]['layers'][r]
            body += f'<div class="mx-cell {L["role"]}"><b>{html.escape(L["name"])}</b></div>'
    facts = [
        ('You write', ['HTML, CSS', 'Python', 'Python, HTML, JS', 'HTML, CSS, JS']),
        ('Needs to run', ['A browser', 'Python + nicegui', 'Python + fastapi + uvicorn', 'A browser']),
        ('Python changes the page after load', ['No', 'Yes, over a websocket', 'No', 'No']),
        ('Lines of code (non-blank)', [str(loc('s2')), str(loc('s3')), str(loc('s4')), str(loc('s5'))]),
    ]
    for label, vals in facts:
        body += f'<div class="mx-row">{label}</div>' + ''.join(f'<div class="mx-fact">{v}</div>' for v in vals)
    return f'<div class="matrix" role="table" aria-label="Which layers each road uses">{head}{body}</div>'


nav = ''.join(f'<a href="#{s["id"]}"><span>{s["n"]}</span>{s["title"]}</a>' for s in STEPS)
nav += '<a href="#compare"><span>6</span>Compare the roads</a>'

page = (HERE / 'template.html').read_text()
page = page.replace('<!--NAV-->', nav)
page = page.replace('<!--STEPS-->', ''.join(step_html(s) for s in STEPS))
page = page.replace('<!--COMPARE-->', compare_html())
page = page.replace('<!--HERO_VIEW-->', view_html(dict(url='', pad=16, count=2, bb=True)))
page = page.replace('/*RAW*/', json.dumps(RAW).replace('</', '<\\/'))
out = ROOT / 'docs' / 'index.html'
out.write_text(page)
print(f'wrote {out.relative_to(ROOT)} ({len(page):,} bytes)')
