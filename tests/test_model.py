"""Tests for tutorial/model.py and a build smoke test.  Run:  python -m pytest"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tutorial'))
import build  # noqa: E402
import model  # noqa: E402

LINES = ['<div id="app">', '  <div class="box">', '  </div>', '</div>']


@pytest.mark.parametrize(
    'marker, line, expected',
    [
        ('box', '  <div class="box">', True),  # contains
        ('=</div>', '  </div>', True),  # equal after trimming
        ('==</div>', '  </div>', False),  # exactly equal
        ('==  </div>', '  </div>', True),
        ('nothing', '<div>', False),
    ],
)
def test_hit(marker, line, expected):
    assert model.hit(line, marker) is expected


def test_find_single_and_range():
    assert model.find(LINES, ['class="box"'], 'x') == (2, 2)
    assert model.find(LINES, ['<div id="app">', '=</div>'], 'x') == (1, 3)  # first trimmed "</div>" from the start
    assert model.find(LINES, ['<div id="app">', '==</div>'], 'x') == (1, 4)


@pytest.mark.parametrize('marks', [['missing'], ['<div id="app">', 'missing'], [], ['a', 'b', 'c']])
def test_find_fails_loudly(marks):
    with pytest.raises(model.ContentError):
        model.find(LINES, marks, 'file.html')


def test_label():
    assert model.label([(5, 5), (1, 3)]) == 'L1–3, L5'


def test_merge_translation():
    base = {'name': 'One box', 'cross': [{'idea': 'A', 'say': 'a'}, {'idea': 'B', 'say': 'b'}], 'n': 1}
    over = {'name': 'Ein Kasten', 'cross': [{'say': 'ä'}]}
    out = model.merge(base, over)
    assert out['name'] == 'Ein Kasten'
    assert out['cross'] == [{'idea': 'A', 'say': 'ä'}, {'idea': 'B', 'say': 'b'}]  # item by item, rest kept
    assert out['n'] == 1
    assert base['cross'][0]['say'] == 'a'  # base untouched


def test_strings_are_attributes_not_dict_methods():
    t = model.strings('en', 'en')
    assert t.copy_code == 'Copy'
    assert not callable(getattr(t, 'copy', None))  # a dict would return dict.copy here


def test_content_loads_and_markers_resolve():
    site = model.load_site()
    sections = model.load_sections(site)
    steps = [s for sec in sections for s in sec.steps]
    assert steps, 'no steps found'
    for st in steps:
        for x in st.cross:
            assert x.refs, f'{st.num} cross-comment {x.n} points nowhere'
            for ref in x.refs.values():
                assert ref.builtin or ref.ranges


def test_bad_language_code_is_refused(monkeypatch):
    real = model.tomllib.loads
    monkeypatch.setattr(
        model.tomllib, 'loads', lambda s: {**real(s), 'languages': ['en', '']} if 'languages' in s else real(s)
    )
    with pytest.raises(model.ContentError):
        model.load_site()


def test_build_smoke(tmp_path):
    build.build(tmp_path)
    (tmp_path / 'CNAME').write_text('keep me', encoding='utf-8')  # added by hand after the first build
    written = build.build(tmp_path)
    index = (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert (tmp_path / 'CNAME').read_text(encoding='utf-8') == 'keep me'  # the build only replaces what it owns
    assert (tmp_path / 'assets' / 'site.css').is_file()
    assert 'built-in method' not in index and 'Undefined' not in index
    for f in written:
        html = f.read_text(encoding='utf-8')
        for ref in re.findall(r'(?:href|src)="(?![a-z]+:)([^"#]+)', html):  # every local link and asset exists
            assert (f.parent / ref).resolve().exists(), f'{f.name}: broken {ref}'
    # building twice gives the same pages
    first = {f: f.read_text(encoding='utf-8') for f in written}
    build.build(tmp_path)
    assert {f: f.read_text(encoding='utf-8') for f in written} == first


# ---------------------------------------------------------------- regressions from the code review
def test_rows_keep_leading_blank_lines():
    code = model.Code(file='a.py', ext='.py', text='\n\nx = 1\n')
    assert code.nlines == 3 and len(code.rows) == 3  # row n is line n


def make_step(tmp_path, cross_toml):
    d = tmp_path / 'step'
    d.mkdir()
    (d / 'vue.html').write_text('<div id="app">\n</div>\n', encoding='utf-8')
    (d / 'step.toml').write_text(
        f'name = "T"\nintro = ["x"]\n\n[[cross]]\nidea = "I"\n{cross_toml}\n', encoding='utf-8'
    )
    return d


@pytest.mark.parametrize(
    'spec',
    [
        'vue = { at = ["ab"] }',  # a string where a range list belongs
        'vue = { hint = "no at, no builtin" }',
        'vue = { at = [["app"]], builtin = "both" }',
        'vue = "just text"',
        'vue = { at = [[""]] }',
    ],
)
def test_bad_cross_spec_is_a_clear_error(tmp_path, spec):
    with pytest.raises(model.ContentError):
        model.load_step(make_step(tmp_path, spec), '9.9', model.load_site())


def test_good_cross_spec(tmp_path):
    st = model.load_step(
        make_step(tmp_path, 'vue = { at = [["app", "=</div>"]], hint = "h" }'), '9.9', model.load_site()
    )
    assert st.cross[0].refs['vue'].ranges == [(1, 2)]


def test_failed_build_keeps_the_old_site(tmp_path, monkeypatch):
    build.build(tmp_path)
    before = (tmp_path / 'index.html').read_text(encoding='utf-8')

    def broken(site):
        raise model.ContentError('bad marker')

    monkeypatch.setattr(model, 'load_sections', broken)
    with pytest.raises(model.ContentError):
        build.build(tmp_path)
    assert (tmp_path / 'index.html').read_text(encoding='utf-8') == before  # nothing was deleted
    assert (tmp_path / 'steps').is_dir()
    assert not list(tmp_path.parent.glob('.xref-build-*'))  # temp folder cleaned up


def test_refuses_a_folder_it_does_not_own(tmp_path):
    (tmp_path / 'important.txt').write_text('mine', encoding='utf-8')
    with pytest.raises(model.ContentError):
        build.build(tmp_path)
    assert (tmp_path / 'important.txt').read_text(encoding='utf-8') == 'mine'


def test_removed_language_folder_is_cleaned_up(tmp_path):
    build.build(tmp_path)
    (tmp_path / 'fa').mkdir()  # pretend an earlier build made docs/fa/
    (tmp_path / 'fa' / 'index.html').write_text('old', encoding='utf-8')
    manifest = tmp_path / build.MANIFEST
    manifest.write_text(manifest.read_text(encoding='utf-8').replace('"assets"', '"assets", "fa"'), encoding='utf-8')
    build.build(tmp_path)
    assert not (tmp_path / 'fa').exists()


def test_manifest_cannot_point_outside(tmp_path):
    build.build(tmp_path)
    (tmp_path / build.MANIFEST).write_text('{"owned": ["..", "/etc", "a/b", "index.html"]}', encoding='utf-8')
    assert build.owned_entries(tmp_path) == ['index.html']


# ---------------------------------------------------------------- Markdown (tutorial/mdrender.py)
import mdrender  # noqa: E402


def fake_fence(**kw):
    return (
        f'<FENCE {kw["kind"]} {kw["lang"]} title={kw["title"]!r} marked={sorted(kw["marked"])} rows={len(kw["rows"])}>'
    )


@pytest.mark.parametrize(
    'info, kind, lang',
    [
        ('css', 'code', 'css'),
        ('mermaid', 'mermaid', 'mermaid'),
        ('html preview', 'html', 'html'),
        ('html', 'code', 'html'),
        ('', 'code', ''),
        ('nosuchlang', 'code', 'nosuchlang'),
    ],
)
def test_fence_kinds(info, kind, lang):
    out = mdrender.Markdown(fence_html=fake_fence).block(f'```{info}\na\nb\n```\n')
    assert f'<FENCE {kind} {lang} ' in out and 'rows=2' in out


def test_fence_info_title_and_marked_lines():
    out = mdrender.Markdown(fence_html=fake_fence).block('```css title="my file.css" hl=1,3-4\n1\n2\n3\n4\n```\n')
    assert "title='my file.css'" in out and 'marked=[1, 3, 4]' in out


def test_bad_fence_info_is_an_error():
    with pytest.raises(ValueError):
        mdrender.Markdown(fence_html=fake_fence).block('```css hl=x-y\na\n```\n')


def test_headings_move_down_inside_a_step():
    md = mdrender.Markdown(fence_html=fake_fence)
    out = md.block('# Title\n\n## Sub\n')  # inside the index: a step title is h3, so # is h4
    assert '<h4 class="md-h1">Title</h4>' in out and '<h5 class="md-h2">Sub</h5>' in out
    out = md.block('# Title\n\n## Sub\n', top=2)  # on a step's own page: the title is h1, so # is h2
    assert '<h2 class="md-h1">Title</h2>' in out and '<h3 class="md-h2">Sub</h3>' in out


def test_inline_markdown_keeps_kbd_and_code():
    out = mdrender.Markdown(fence_html=fake_fence).inline('Press <kbd>C</kbd> to see `box-sizing`.')
    assert out == 'Press <kbd>C</kbd> to see <code>box-sizing</code>.'


def test_mermaid_lexer_highlights():
    rows = mdrender.highlight_rows('flowchart LR\n  A["x"] --> B\n', 'mermaid')
    assert len(rows) == 2
    assert '<span class="tk-k">flowchart</span>' in rows[0] and '<span class="tk-kc">LR</span>' in rows[0]
    assert '<span class="tk-o">--&gt;</span>' in rows[1]


def test_markdown_blocks_and_translations(tmp_path, monkeypatch):
    d = make_step(tmp_path, 'vue = { builtin = "b" }')
    (d / '2-b.md').write_text('# B', encoding='utf-8')
    (d / '1-a.md').write_text('# A', encoding='utf-8')
    (d / '1-a.fa.md').write_text('# A in Persian', encoding='utf-8')
    site = model.load_site()
    st = model.load_step(d, '9.9', site)
    assert [(b.name, b.text) for b in st.blocks] == [('1-a', '# A'), ('2-b', '# B')]  # file order, no translations
    site.lang = 'fa'
    st = model.load_step(d, '9.9', site)
    assert st.blocks[0].text == '# A in Persian' and st.blocks[1].text == '# B'  # fallback to English


# ---------------------------------------------------------------- regressions from the second audit
import ast  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402

import steps  # noqa: E402


def test_pygments_classes_are_prefixed():
    """Pygments' short names (sr, no, cp...) clashed with site classes: .sr hid regex literals."""
    rows = mdrender.highlight_rows('const r = /a+b/g;\n', 'js') + model.Code('a.py', '.py', 'x = 1\n').rows
    classes = set(re.findall(r'class="([^"]+)"', ''.join(rows)))
    assert classes and all(c.startswith('tk-') for c in classes), classes


def test_all_text_files_are_read_and_written_as_utf8():
    """On Windows the default is cp1252, which cannot write the page's 'A−' (U+2212)."""
    bad = []
    for f in sorted((ROOT / 'tutorial').glob('*.py')) + sorted((ROOT / 'tests').glob('*.py')):
        for node in ast.walk(ast.parse(f.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') in ('read_text', 'write_text'):
                if not any(k.arg == 'encoding' for k in node.keywords):
                    bad.append(f'{f.name}:{node.lineno}')
    assert bad == []


def test_a_broken_translation_names_its_own_file(tmp_path):
    (tmp_path / 'step.toml').write_text('name = "ok"\n', encoding='utf-8')
    (tmp_path / 'step.fa.toml').write_text('name = = broken\n', encoding='utf-8')
    with pytest.raises(model.ContentError, match=r'step\.fa\.toml'):
        model.read_toml(tmp_path / 'step.toml', 'fa', 'en')


def test_a_broken_site_toml_is_a_content_error(tmp_path, monkeypatch):
    (tmp_path / 'site.toml').write_text('title = = broken\n', encoding='utf-8')
    monkeypatch.setattr(model, 'CONTENT', tmp_path)
    with pytest.raises(model.ContentError, match=r'site\.toml'):
        model.load_site()


def test_a_column_added_after_the_screenshots_is_stale(tmp_path):
    d = make_step(tmp_path, 'vue = { builtin = "b" }')
    (d / 'quasar.html').write_text('<p>q</p>\n', encoding='utf-8')
    (d / 'shots').mkdir()
    (d / 'shots' / 'quasar.png').write_bytes(b'png')
    result = {
        'tested': '2026-11-05',
        'view': {'width': 1, 'height': 1},
        'scale': 1,
        'compared_to': 'quasar',
        'diff_pixels': {},
        'libraries': {},
        'sources': {'quasar': model.file_hash(d / 'quasar.html')},
    }
    (d / 'shots' / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    shots = model.load_shots(d, ['quasar', 'nicegui', 'vue'])
    assert shots.stale == ['vue']  # vue.html exists but was never shot


def test_column_file_prefers_the_exact_name(tmp_path):
    for name in ('vue-old.html', 'vue.html', 'vuex.html', 'nicegui_app.py'):
        (tmp_path / name).write_text('x', encoding='utf-8')
    assert model.column_file(tmp_path, 'vue').name == 'vue.html'
    assert model.column_file(tmp_path, 'nicegui').name == 'nicegui_app.py'
    assert model.column_file(tmp_path, 'quasar') is None


def test_a_failed_swap_restores_the_old_site(tmp_path, monkeypatch):
    build.build(tmp_path)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    real_move, calls = shutil.move, []

    def flaky_move(src, dst):
        if '.xref-build-' in str(src):  # a new entry moving into the site
            calls.append(dst)
            if len(calls) == 2:  # the second one fails half-way
                raise OSError('disk full')
        return real_move(src, dst)

    monkeypatch.setattr(build.shutil, 'move', flaky_move)
    with pytest.raises(OSError):
        build.build(tmp_path)
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert after == before
    assert not list(tmp_path.parent.glob('.xref-*'))


def test_links_work_on_both_kinds_of_page():
    site = model.load_site()
    st = [s for sec in model.load_sections(site) for s in sec.steps]
    index, page = build.Links(st), build.Links(st, st[0])
    assert index.href('sec-1') == '#sec-1' and index.step_page(st[0]) == f'steps/{st[0].slug}.html'
    assert page.href(st[0].id) == f'#{st[0].id}' and page.href(f'{st[0].id}-x1') == f'#{st[0].id}-x1'
    assert page.href('summary') == '../index.html#summary' and page.step_link(st[0]) == f'{st[0].slug}.html'


def test_two_languages_link_to_each_other(tmp_path, monkeypatch):
    i18n = tmp_path / 'i18n'
    shutil.copytree(model.I18N, i18n)
    (i18n / 'xx.toml').write_text('name = "Test"\ndir = "rtl"\nsummary = "XX"\n', encoding='utf-8')
    monkeypatch.setattr(model, 'I18N', i18n)
    real = model.tomllib.loads
    monkeypatch.setattr(
        model.tomllib, 'loads', lambda s: {**real(s), 'languages': ['en', 'xx']} if 'languages' in s else real(s)
    )
    out = tmp_path / 'docs'
    build.build(out)
    xx = (out / 'xx' / 'index.html').read_text(encoding='utf-8')
    assert '<html lang="xx" dir="rtl">' in xx
    for page, html in [
        ('index.html', (out / 'index.html').read_text(encoding='utf-8')),
        ('xx/index.html', xx),
        ('xx/steps/1-1.html', (out / 'xx/steps/1-1.html').read_text(encoding='utf-8')),
    ]:
        alts = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', html))
        assert set(alts) == {'en', 'xx'}, page
        for href in alts.values():
            assert ((out / page).parent / href).resolve().is_file(), f'{page}: {href}'
    assert 'XX' in xx and '>Test<' in (out / 'index.html').read_text(encoding='utf-8')  # switcher shows names


def test_steps_finder(capsys):
    assert steps.main(['1.1', 'nicegui']) == 0
    assert capsys.readouterr().out.strip().endswith('nicegui_app.py')
    assert steps.main(['9.9']) == 1
    assert steps.main(['1.1', 'react']) == 1


def test_cdn_pattern_handles_scoped_and_unversioned_packages():
    shoot = pytest.importorskip('shoot')
    m = shoot.CDN.match('https://cdn.jsdelivr.net/npm/@quasar/extras@1.16.0/roboto-font/roboto-font.css')
    assert m and m.group(1) == '@quasar/extras' and m.group(2) == 'roboto-font/roboto-font.css'
    m = shoot.CDN.match('https://unpkg.com/vue/dist/vue.esm-browser.prod.js')
    assert m and m.group(1) == 'vue' and m.group(2) == 'dist/vue.esm-browser.prod.js'
