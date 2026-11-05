"""Builds the tutorial site from content/ and tutorial/templates/.

Run from anywhere:  python tutorial/build.py [--out DIR] [--check]     (default DIR: docs/)
--check builds into a temporary folder and fails when DIR differs (the git hook and CI use it).

Output (all generated, never edit by hand)
  DIR/index.html            summary + every section, each step embedded
  DIR/steps/<s>-<n>.html    each step on its own page
  DIR/assets/               site.css, site.js and the screenshots the pages use
  DIR/<lang>/...            the same pages for every extra language in content/site.toml

Safety: everything is rendered into a temporary folder first and swapped in only when the
whole build worked, so a failed build never leaves a half-empty docs/. DIR/.xref-build.json
lists what the build owns; those entries are replaced, a language removed from site.toml is
cleaned up, and every other file in DIR (a CNAME, say) is kept. A non-empty DIR the build
does not own is refused. Content loading lives in model.py; this file only renders.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mdrender  # noqa: E402
import model  # noqa: E402

TEMPLATES = model.HERE / 'templates'
ASSETS = model.HERE / 'assets'
MANIFEST = '.xref-build.json'
DEFAULT_OUT = model.ROOT / 'docs'
LEGACY_OWNED = ['index.html', 'steps', 'assets']  # docs/ before the manifest existed
SAFE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')
UI_KEYS_FOR_JS = (
    'copy_code',
    'copied',
    'press_ctrl_c',
    'theme',
    'theme_auto',
    'theme_light',
    'theme_dark',
    'diagram_offline',
    'diagram_error',
)


def make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader([TEMPLATES, model.CONTENT]),
        autoescape=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def shot_names(st) -> dict[str, str]:
    """Screenshots a page shows: one when all columns match, else one per column."""
    sh = st.shots
    show = [sh.compared_to] if sh.same else list(sh.files)
    return {cid: f'shots/{st.slug}-{cid}.png' for cid in show}


class Links:
    """Every link a template writes goes through here, so it works on both kinds of page."""

    def __init__(self, steps, step=None):
        self.step = step  # None on the index page
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
        if is_default:  # other languages reuse the same files
            for cid, name in st.shots.urls.items():
                (out_root / 'assets' / 'shots').mkdir(parents=True, exist_ok=True)
                shutil.copyfile(st.shots.files[cid], out_root / 'assets' / name)

    # Markdown fences are drawn by the `fence` macro, so their markup lives in the templates too
    fence = env.get_template('macros.html').make_module({'t': t}).fence
    md = mdrender.Markdown(fence_html=fence)
    common = dict(
        site=site,
        t=t,
        lang=lang,
        cols=site.columns,
        sections=sections,
        md=md,
        page_data={'cols': site.column_ids, 'ui': {k: getattr(t, k) for k in UI_KEYS_FOR_JS}, 'libs': site.libs},
    )

    def render_step(st, links, mode, assets):
        try:
            return Markup(
                env.get_template(st.template).render(**common, **links.ctx(assets), step=st, sec=st.section, mode=mode)
            )
        except ValueError as e:  # e.g. a bad code-fence info string in a .md file
            raise model.ContentError(f'{model.rel(st.dir)}: {e}') from None

    written = []
    out.mkdir(parents=True, exist_ok=True)
    links, assets = Links(steps), f'{up}assets/'
    embedded = {st.id: render_step(st, links, 'index', assets) for st in steps}
    (out / 'index.html').write_text(
        env.get_template('index.html').render(
            **common,
            **links.ctx(assets),
            page_id='summary',
            step_html=embedded,
            xref_rows=[(st, x) for st in steps for x in st.cross],
        )
    )
    written.append(out / 'index.html')

    (out / 'steps').mkdir(parents=True, exist_ok=True)
    for st in steps:
        links, assets = Links(steps, st), f'../{up}assets/'
        page = env.get_template('step_page.html').render(
            **common,
            **links.ctx(assets),
            page_id=st.id,
            step=st,
            sec=st.section,
            step_html={st.id: render_step(st, links, 'page', assets)},
        )
        f = out / 'steps' / f'{st.slug}.html'
        f.write_text(page)
        written.append(f)

    if is_default:
        for st in steps:
            where = model.rel(st.dir)
            if not st.shots:
                print(f'warning: {where} has no screenshots yet. Run: python tutorial/shoot.py')
            elif st.shots.stale:
                print(
                    f'warning: {where}: {site.names(st.shots.stale)} changed after the screenshots. '
                    'Run: python tutorial/shoot.py'
                )
    return written


def owned_entries(out_root: Path) -> list[str]:
    """Top-level names in out_root that an earlier build wrote."""
    f = out_root / MANIFEST
    if f.is_file():
        names = json.loads(f.read_text()).get('owned', [])
    elif out_root == DEFAULT_OUT:
        names = LEGACY_OWNED
    else:
        names = []
    return [n for n in names if SAFE_NAME.fullmatch(n)]  # never a path, never ".."


def check_out(out_root: Path):
    if not out_root.exists() or out_root == DEFAULT_OUT or (out_root / MANIFEST).is_file():
        return
    if any(out_root.iterdir()):
        raise model.ContentError(
            f'{out_root} is not empty and was not made by this build. Use an empty folder, or docs/.'
        )


def build(out_root: Path) -> list[Path]:
    out_root = out_root.resolve()
    check_out(out_root)
    site = model.load_site()
    out_root.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='.xref-build-', dir=out_root.parent))
    try:
        (tmp / 'assets').mkdir()
        for name in ('site.css', 'site.js'):
            shutil.copyfile(ASSETS / name, tmp / 'assets' / name)
        env = make_env()
        written = []
        for lang in site.languages:
            pages = build_language(lang, tmp, env)
            print(f'[{lang}] {len(pages)} pages')
            written += [out_root / f.relative_to(tmp) for f in pages]
        # everything rendered: swap it in
        new = sorted(p.name for p in tmp.iterdir())
        out_root.mkdir(exist_ok=True)
        for name in set(owned_entries(out_root)) | set(new):
            target = out_root / name
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()
        for name in new:
            shutil.move(tmp / name, out_root / name)
        (out_root / MANIFEST).write_text(json.dumps({'owned': new}, indent=2) + '\n')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return written


def files_under(root: Path, names) -> dict[str, bytes]:
    out = {}
    for name in names:
        p = root / name
        for f in [p] if p.is_file() else sorted(p.rglob('*')) if p.is_dir() else []:
            if f.is_file():
                out[f.relative_to(root).as_posix()] = f.read_bytes()
    return out


def stale_files(out_root: Path) -> list[str]:
    """Build into a temporary folder and list every file that differs from out_root ([] = up to date)."""
    with tempfile.TemporaryDirectory(prefix='xref-check-') as d:
        fresh = Path(d) / 'site'
        build(fresh)
        names = {p.name for p in fresh.iterdir()} | set(owned_entries(out_root)) | {MANIFEST}
        want, have = files_under(fresh, names), files_under(out_root, names)
    return sorted(k for k in want.keys() | have.keys() if want.get(k) != have.get(k))


def main():
    ap = argparse.ArgumentParser(description='Build the tutorial site.')
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT, help='output folder (default: docs/)')
    ap.add_argument('--check', action='store_true', help='do not write: fail if the output folder is out of date')
    args = ap.parse_args()
    out = args.out.resolve()
    try:
        if args.check:
            diff = stale_files(out)
            if diff:
                sys.exit(
                    f'{model.rel(out)} is out of date ({len(diff)} files): run python tutorial/build.py\n  '
                    + '\n  '.join(diff[:20])
                )
            print(f'{model.rel(out)} is up to date')
            return
        written = build(out)
    except model.ContentError as e:
        sys.exit(f'build failed: {e}')
    for f in written:
        print(f'  {f.relative_to(model.ROOT) if f.is_relative_to(model.ROOT) else f}')


if __name__ == '__main__':
    main()
