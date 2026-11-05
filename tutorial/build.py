"""Builds the tutorial site in docs/ from content/ and tutorial/templates/.

Run from anywhere:  python tutorial/build.py

Output
  docs/index.html            summary + every section, each step embedded
  docs/steps/<n>-<n>.html    each step on its own page
  docs/assets/               shared site.css, site.js and the step screenshots
  docs/<lang>/...            the same for every extra language in site.toml

Input
  content/site.toml                      title, lead, columns, languages
  content/NN-name/section.toml           a section: name, about, planned steps
  content/NN-name/NN-name/step.toml      a step: name, intro, notes, cross-comments
  content/NN-name/NN-name/step.html      optional: override blocks of templates/step.html
  content/NN-name/NN-name/picture.svg    the one picture next to the intro
  content/NN-name/NN-name/quasar*.html, nicegui*.py, vue*.html   runnable column files
  content/NN-name/NN-name/shots/         made by tutorial/shoot.py
  tutorial/i18n/<lang>.toml              UI strings
Any *.toml can have a translation next to it: step.fa.toml overrides step.toml for "fa".
"""
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import HtmlLexer, PythonLexer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTENT = ROOT / 'content'
DOCS = ROOT / 'docs'
LEXERS = {'.html': HtmlLexer, '.py': PythonLexer}
LANG_LABEL = {'.html': 'HTML', '.py': 'Python'}


def fail(msg):
    sys.exit(f'build failed: {msg}')


# ------------------------------------------------------------ toml + languages
def merge(base, over):
    """Deep merge: dicts merge, lists of tables merge item by item, anything else is replaced."""
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = merge(base[k], v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(over, list) and all(isinstance(x, dict) for x in base + over):
        return [merge(b, o) for b, o in zip(base, over)] + base[len(over):]
    return over


def load_toml(path, lang, default):
    data = tomllib.loads(path.read_text())
    tr = path.with_name(f'{path.stem}.{lang}.toml')
    if lang != default and tr.is_file():
        data = merge(data, tomllib.loads(tr.read_text()))
    return data


def strings(lang, default):
    t = tomllib.loads((HERE / 'i18n' / f'{default}.toml').read_text())
    f = HERE / 'i18n' / f'{lang}.toml'
    if lang != default:
        if not f.is_file():
            fail(f'no UI strings for language {lang!r}: add tutorial/i18n/{lang}.toml')
        t.update(tomllib.loads(f.read_text()))
    clash = sorted(k for k in t if hasattr(dict, k))
    if clash:
        fail(f'i18n keys {clash} clash with dict methods; rename them (Jinja would find the method)')
    return t


# ------------------------------------------------------------ markers
def hit(line, marker):
    if marker.startswith('=='):
        return line == marker[2:]
    if marker.startswith('='):
        return line.strip() == marker[1:]
    return marker in line


def find(lines, marks, where):
    start, end = (list(marks) + [None])[:2]
    i = next((n for n, l in enumerate(lines) if hit(l, start)), None)
    if i is None:
        fail(f'{where}: no line matches {start!r}')
    if end is None:
        return [i + 1, i + 1]
    j = next((n for n in range(i, len(lines)) if hit(lines[n], end)), None)
    if j is None:
        fail(f'{where}: no line after {start!r} matches {end!r}')
    return [i + 1, j + 1]


def label(ranges):
    return ', '.join(f'L{a}' if a == b else f'L{a}–{b}' for a, b in sorted(ranges))


# ------------------------------------------------------------ content
def load(lang, default, cols):
    col_ids = [c['id'] for c in cols]
    sections = []
    for sdir in sorted(p for p in CONTENT.iterdir() if (p / 'section.toml').is_file()):
        sec = load_toml(sdir / 'section.toml', lang, default)
        sec.update(n=len(sections) + 1, id=f'sec-{len(sections) + 1}', steps=[])
        for tdir in sorted(p for p in sdir.iterdir() if (p / 'step.toml').is_file()):
            sec['steps'].append(load_step(tdir, sec, lang, default, col_ids))
        sec['planned_steps'] = [
            {'num': f'{sec["n"]}.{len(sec["steps"]) + k + 1}', 'name': name, 'ready': False}
            for k, name in enumerate(sec.get('planned', []))]
        sections.append(sec)
    # previous / next across all sections, planned steps included
    flat = [s for sec in sections for s in sec['steps'] + sec['planned_steps']]
    for i, s in enumerate(flat):
        s['prev'] = flat[i - 1] if i > 0 else None
        s['next'] = flat[i + 1] if i + 1 < len(flat) else None
    return sections


def load_step(tdir, sec, lang, default, col_ids):
    st = load_toml(tdir / 'step.toml', lang, default)
    k = len(sec['steps']) + 1
    st.update(num=f'{sec["n"]}.{k}', id=f's{sec["n"]}-{k}', slug=f'{sec["n"]}-{k}', ready=True, dir=tdir, section=sec)
    st.setdefault('columns', {})
    where = tdir.relative_to(ROOT)
    pic = tdir / 'picture.svg'
    st['picture'] = re.sub(r'<\?xml.*?\?>', '', pic.read_text()).strip() if pic.is_file() else ''
    st['template'] = f'{tdir.relative_to(CONTENT).as_posix()}/step.html' if (tdir / 'step.html').is_file() else 'step.html'

    st['code'], st['raw'] = {}, {}
    for cid in col_ids:
        files = [f for f in sorted(tdir.glob(f'{cid}*.*')) if f.suffix in LEXERS]
        if not files:
            continue
        f = files[0]
        text = f.read_text()
        rows = highlight(text, LEXERS[f.suffix](), HtmlFormatter(nowrap=True)).rstrip('\n').split('\n')
        st['code'][cid] = {'file': f.name, 'lang': LANG_LABEL[f.suffix], 'lines': text.rstrip('\n').split('\n'),
                           'rows': [Markup(r or ' ') for r in rows], 'marks': {}}
        st['code'][cid]['nlines'] = len(st['code'][cid]['lines'])
        st['raw'][cid] = text

    for n, x in enumerate(st.get('cross', []), 1):
        x['n'], x['refs'], x['ranges'] = n, {}, {}
        for cid in col_ids:
            spec = x.get(cid)
            if spec is None:
                continue
            if 'builtin' in spec:
                x['refs'][cid] = {'builtin': spec['builtin']}
                x['ranges'][cid] = []
                continue
            if cid not in st['code']:
                fail(f'{where}: cross-comment {n} points at {cid}, but the step has no {cid} file')
            code = st['code'][cid]
            ranges = [find(code['lines'], m, f'{where}/{code["file"]} cross-comment {n}') for m in spec['at']]
            x['refs'][cid] = {'label': label(ranges), 'hint': spec.get('hint', '')}
            x['ranges'][cid] = ranges
            for a, b in ranges:
                for ln in range(a, b + 1):
                    marks = code['marks'].setdefault(ln, [])
                    if n not in marks:
                        marks.append(n)

    st['shots'] = load_shots(tdir, st['slug'], col_ids)
    if not st['shots']:
        print(f'warning: {where} has no screenshots yet. Run: python tutorial/shoot.py')
    return st


def load_shots(tdir, slug, col_ids):
    res = tdir / 'shots' / 'result.json'
    if not res.is_file():
        return None
    r = json.loads(res.read_text())
    out = DOCS / 'assets' / 'shots'
    out.mkdir(parents=True, exist_ok=True)
    imgs = {}
    for cid in col_ids:
        src = tdir / 'shots' / f'{cid}.png'
        if src.is_file():
            shutil.copyfile(src, out / f'{slug}-{cid}.png')
            imgs[cid] = f'shots/{slug}-{cid}.png'
    diff = r['diff_pixels']
    return {'same': all(v == 0 for v in diff.values()), 'diff': diff, 'imgs': imgs,
            'w': r['view']['width'], 'h': r['view']['height'], 'scale': r['scale'], 'date': r['tested'],
            'compared_to': r['compared_to'], 'libraries': r['libraries']}


def tested_versions(sections, cols):
    found = {}
    for sec in sections:
        for st in sec['steps']:
            for cid, libs in (st['shots'] or {}).get('libraries', {}).items():
                found.setdefault(cid, libs)
    for c in cols:
        v = found.get(c['id'], {})
        if c['id'] == 'nicegui' and v:
            c['tested'] = f'NiceGUI {v["nicegui"]} (Vue {v.get("vue", "?")}, Quasar {v.get("quasar", "?")})'
        elif c['id'] == 'quasar' and v:
            c['tested'] = f'Quasar {v.get("quasar", "?")} + Vue {v.get("vue", "?")}'
        elif c['id'] == 'vue' and found.get('quasar', {}).get('vue'):
            c['tested'] = f'Vue {found["quasar"]["vue"]}'


# ------------------------------------------------------------ render
def build(lang, default, site_base):
    site = load_toml(CONTENT / 'site.toml', lang, default) if lang != default else site_base
    t = strings(lang, default)
    cols = [dict(c) for c in site['column']]
    sections = load(lang, default, cols)
    tested_versions(sections, cols)
    steps = [st for sec in sections for st in sec['steps']]
    step_ids = {st['id']: st for st in steps}
    out = DOCS if lang == default else DOCS / lang
    up = '' if lang == default else '../'

    env = Environment(loader=FileSystemLoader([HERE / 'templates', CONTENT]), autoescape=True,
                      undefined=StrictUndefined, trim_blocks=False, lstrip_blocks=False)
    common = dict(site=site, t=t, lang=lang, cols=cols, cols_by_id={c['id']: c for c in cols}, sections=sections,
                  page_data={'cols': [c['id'] for c in cols], 'ui': {k: t[k] for k in (
                      'copy_code', 'copied', 'press_ctrl_c', 'theme', 'theme_auto', 'theme_light', 'theme_dark')}})

    def render_step(st, mode, href, step_link, step_page_href, assets):
        tpl = env.get_template(st['template'])
        return Markup(tpl.render(**common, step=st, sec=st['section'], mode=mode, href=href, step_link=step_link,
                                 step_page_href=step_page_href, assets=assets))

    # index page
    href = lambda target: f'#{target}'
    assets = f'{up}assets/'
    ctx = dict(href=href, assets=assets, step_link=lambda s: f'#{s["id"]}',
               step_page_href=lambda s: f'steps/{s["slug"]}.html')
    html = {st['id']: render_step(st, 'index', **ctx) for st in steps}
    xref_rows = [(st, x) for st in steps for x in st.get('cross', [])]
    out.mkdir(parents=True, exist_ok=True)
    page = env.get_template('index.html').render(**common, **ctx, page_id='summary', step_html=html, xref_rows=xref_rows)
    (out / 'index.html').write_text(page)
    written = [out / 'index.html']

    # one page per step
    (out / 'steps').mkdir(exist_ok=True)
    for st in steps:
        def href(target, st=st):
            if target in step_ids and target != st['id']:
                return f'{step_ids[target]["slug"]}.html'
            if target == st['id'] or target.startswith(st['id'] + '-x'):
                return f'#{target}'
            return f'../index.html#{target}'
        ctx = dict(href=href, assets=f'../{up}assets/', step_link=lambda s: f'{s["slug"]}.html',
                   step_page_href=lambda s: f'{s["slug"]}.html')
        one = {st['id']: render_step(st, 'page', **ctx)}
        page = env.get_template('step_page.html').render(**common, **ctx, page_id=st['id'], step=st,
                                                          sec=st['section'], step_html=one)
        f = out / 'steps' / f'{st["slug"]}.html'
        f.write_text(page)
        written.append(f)
    return written, len(sections), len(steps)


def main():
    site = tomllib.loads((CONTENT / 'site.toml').read_text())
    langs = site.get('languages', ['en'])
    default = langs[0]
    (DOCS / 'assets').mkdir(parents=True, exist_ok=True)
    for name in ('site.css', 'site.js'):
        shutil.copyfile(HERE / 'assets' / name, DOCS / 'assets' / name)
    for lang in langs:
        written, nsec, nstep = build(lang, default, site)
        size = sum(f.stat().st_size for f in written)
        print(f'[{lang}] wrote {len(written)} pages ({size:,} bytes). Sections: {nsec}. Steps ready: {nstep}.')
        for f in written:
            print(f'  {f.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
