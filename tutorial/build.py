"""Builds the tutorial site from content/ and tutorial/templates/.

Run from anywhere:  python tutorial/build.py [--out DIR]     (default DIR: docs/)

Output (all generated, never edit by hand)
  DIR/index.html            summary + every section, each step embedded
  DIR/steps/<s>-<n>.html    each step on its own page
  DIR/assets/               site.css, site.js and the screenshots the pages use
  DIR/<lang>/...            the same pages for every extra language in content/site.toml

The build owns DIR/index.html, DIR/steps/, DIR/assets/ and DIR/<lang>/ and rewrites them
from scratch each time, so a removed step leaves nothing behind. Content loading lives in
model.py; this file only renders.
"""
import argparse
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model  # noqa: E402

TEMPLATES = model.HERE / 'templates'
ASSETS = model.HERE / 'assets'
UI_KEYS_FOR_JS = ('copy_code', 'copied', 'press_ctrl_c', 'theme', 'theme_auto', 'theme_light', 'theme_dark')


def make_env() -> Environment:
    return Environment(loader=FileSystemLoader([TEMPLATES, model.CONTENT]), autoescape=True,
                       undefined=StrictUndefined, keep_trailing_newline=True)


def shot_names(st) -> dict[str, str]:
    """Screenshots a page shows: one when all columns match, else one per column."""
    sh = st.shots
    show = [sh.compared_to] if sh.same else list(sh.files)
    return {cid: f'shots/{st.slug}-{cid}.png' for cid in show}


class Links:
    """Every link a template writes goes through here, so it works on both kinds of page."""

    def __init__(self, steps, step=None):
        self.step = step                         # None on the index page
        self.by_id = {s.id: s for s in steps}

    def href(self, target: str) -> str:
        if self.step is None:
            return f'#{target}'
        if target in self.by_id and target != self.step.id:
            return f'{self.by_id[target].slug}.html'
        if target == self.step.id or target.startswith(self.step.id + '-x'):
            return f'#{target}'
        return f'../index.html#{target}'

    def step_link(self, s) -> str:
        return f'#{s.id}' if self.step is None else f'{s.slug}.html'

    def step_page(self, s) -> str:
        return f'steps/{s.slug}.html' if self.step is None else f'{s.slug}.html'

    def ctx(self, assets: str) -> dict:
        return dict(href=self.href, step_link=self.step_link, step_page_href=self.step_page, assets=assets)


def build_language(lang: str, out_root: Path, env: Environment) -> list[Path]:
    site = model.load_site(lang)
    t = model.strings(lang, site.default_lang)
    sections = model.load_sections(site)
    model.fill_tested(site, sections)
    steps = [s for sec in sections for s in sec.steps]
    is_default = lang == site.default_lang
    out = out_root if is_default else out_root / lang
    up = '' if is_default else '../'

    for st in (s for s in steps if s.shots):
        st.shots.urls = shot_names(st)
        if is_default:                           # other languages reuse the same files
            for cid, name in st.shots.urls.items():
                (out_root / 'assets' / 'shots').mkdir(parents=True, exist_ok=True)
                shutil.copyfile(st.shots.files[cid], out_root / 'assets' / name)

    common = dict(site=site, t=t, lang=lang, cols=site.columns, sections=sections,
                  page_data={'cols': site.column_ids, 'ui': {k: getattr(t, k) for k in UI_KEYS_FOR_JS}})

    def render_step(st, links, mode, assets):
        return Markup(env.get_template(st.template).render(**common, **links.ctx(assets), step=st, sec=st.section, mode=mode))

    written = []
    out.mkdir(parents=True, exist_ok=True)
    links, assets = Links(steps), f'{up}assets/'
    embedded = {st.id: render_step(st, links, 'index', assets) for st in steps}
    (out / 'index.html').write_text(env.get_template('index.html').render(
        **common, **links.ctx(assets), page_id='summary', step_html=embedded,
        xref_rows=[(st, x) for st in steps for x in st.cross]))
    written.append(out / 'index.html')

    (out / 'steps').mkdir(parents=True, exist_ok=True)
    for st in steps:
        links, assets = Links(steps, st), f'../{up}assets/'
        page = env.get_template('step_page.html').render(
            **common, **links.ctx(assets), page_id=st.id, step=st, sec=st.section,
            step_html={st.id: render_step(st, links, 'page', assets)})
        f = out / 'steps' / f'{st.slug}.html'
        f.write_text(page)
        written.append(f)

    if is_default:
        for st in steps:
            if not st.shots:
                print(f'warning: {st.dir.relative_to(model.ROOT)} has no screenshots yet. Run: python tutorial/shoot.py')
    return written


def clean(out_root: Path, languages: list[str]):
    """Remove only what the build owns, so other files in docs/ (a CNAME, say) survive."""
    for p in [out_root / 'steps', out_root / 'assets', *(out_root / lang for lang in languages[1:])]:
        if p.is_dir():
            shutil.rmtree(p)
    (out_root / 'index.html').unlink(missing_ok=True)


def build(out_root: Path) -> list[Path]:
    site = model.load_site()
    clean(out_root, site.languages)
    (out_root / 'assets').mkdir(parents=True)
    for name in ('site.css', 'site.js'):
        shutil.copyfile(ASSETS / name, out_root / 'assets' / name)
    env = make_env()
    written = []
    for lang in site.languages:
        pages = build_language(lang, out_root, env)
        print(f'[{lang}] {len(pages)} pages')
        written += pages
    return written


def main():
    ap = argparse.ArgumentParser(description='Build the tutorial site.')
    ap.add_argument('--out', type=Path, default=model.ROOT / 'docs', help='output folder (default: docs/)')
    out = ap.parse_args().out.resolve()
    try:
        written = build(out)
    except model.ContentError as e:
        sys.exit(f'build failed: {e}')
    for f in written:
        print(f'  {f.relative_to(model.ROOT) if f.is_relative_to(model.ROOT) else f}')


if __name__ == '__main__':
    main()
