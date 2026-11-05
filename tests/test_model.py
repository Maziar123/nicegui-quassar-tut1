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


@pytest.mark.parametrize('marker, line, expected', [
    ('box', '  <div class="box">', True),            # contains
    ('=</div>', '  </div>', True),                    # equal after trimming
    ('==</div>', '  </div>', False),                  # exactly equal
    ('==  </div>', '  </div>', True),
    ('nothing', '<div>', False),
])
def test_hit(marker, line, expected):
    assert model.hit(line, marker) is expected


def test_find_single_and_range():
    assert model.find(LINES, ['class="box"'], 'x') == (2, 2)
    assert model.find(LINES, ['<div id="app">', '=</div>'], 'x') == (1, 3)   # first trimmed "</div>" from the start
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
    assert out['cross'] == [{'idea': 'A', 'say': 'ä'}, {'idea': 'B', 'say': 'b'}]   # item by item, rest kept
    assert out['n'] == 1
    assert base['cross'][0]['say'] == 'a'                                           # base untouched


def test_strings_are_attributes_not_dict_methods():
    t = model.strings('en', 'en')
    assert t.copy_code == 'Copy'
    assert not callable(getattr(t, 'copy', None))      # a dict would return dict.copy here


def test_content_loads_and_markers_resolve():
    site = model.load_site()
    sections = model.load_sections(site)
    steps = [s for sec in sections for s in sec.steps]
    assert steps, 'no steps found'
    for st in steps:
        for x in st.cross:
            assert x.refs, f'{st.num} cross-comment {x.n} points nowhere'
            for cid, ref in x.refs.items():
                assert ref.builtin or ref.ranges


def test_bad_language_code_is_refused(monkeypatch):
    real = model.tomllib.loads
    monkeypatch.setattr(model.tomllib, 'loads', lambda s: {**real(s), 'languages': ['en', '']} if 'languages' in s else real(s))
    with pytest.raises(model.ContentError):
        model.load_site()


def test_build_smoke(tmp_path):
    build.build(tmp_path)
    (tmp_path / 'CNAME').write_text('keep me')                        # added by hand after the first build
    written = build.build(tmp_path)
    index = (tmp_path / 'index.html').read_text()
    assert (tmp_path / 'CNAME').read_text() == 'keep me'              # the build only replaces what it owns
    assert (tmp_path / 'assets' / 'site.css').is_file()
    assert 'built-in method' not in index and 'Undefined' not in index
    for f in written:
        html = f.read_text()
        for ref in re.findall(r'(?:href|src)="(?![a-z]+:)([^"#]+)', html):   # every local link and asset exists
            assert (f.parent / ref).resolve().exists(), f'{f.name}: broken {ref}'
    # building twice gives the same pages
    first = {f: f.read_text() for f in written}
    build.build(tmp_path)
    assert {f: f.read_text() for f in written} == first


# ---------------------------------------------------------------- regressions from the code review
def test_rows_keep_leading_blank_lines():
    code = model.Code(file='a.py', ext='.py', text='\n\nx = 1\n')
    assert code.nlines == 3 and len(code.rows) == 3          # row n is line n


def make_step(tmp_path, cross_toml):
    d = tmp_path / 'step'
    d.mkdir()
    (d / 'vue.html').write_text('<div id="app">\n</div>\n')
    (d / 'step.toml').write_text(f'name = "T"\nintro = ["x"]\n\n[[cross]]\nidea = "I"\n{cross_toml}\n')
    return d


@pytest.mark.parametrize('spec', [
    'vue = { at = ["ab"] }',                  # a string where a range list belongs
    'vue = { hint = "no at, no builtin" }',
    'vue = { at = [["app"]], builtin = "both" }',
    'vue = "just text"',
    'vue = { at = [[""]] }',
])
def test_bad_cross_spec_is_a_clear_error(tmp_path, spec):
    with pytest.raises(model.ContentError):
        model.load_step(make_step(tmp_path, spec), '9.9', model.load_site())


def test_good_cross_spec(tmp_path):
    st = model.load_step(make_step(tmp_path, 'vue = { at = [["app", "=</div>"]], hint = "h" }'), '9.9', model.load_site())
    assert st.cross[0].refs['vue'].ranges == [(1, 2)]


def test_failed_build_keeps_the_old_site(tmp_path, monkeypatch):
    build.build(tmp_path)
    before = (tmp_path / 'index.html').read_text()

    def broken(site):
        raise model.ContentError('bad marker')
    monkeypatch.setattr(model, 'load_sections', broken)
    with pytest.raises(model.ContentError):
        build.build(tmp_path)
    assert (tmp_path / 'index.html').read_text() == before   # nothing was deleted
    assert (tmp_path / 'steps').is_dir()
    assert not list(tmp_path.parent.glob('.xref-build-*'))   # temp folder cleaned up


def test_refuses_a_folder_it_does_not_own(tmp_path):
    (tmp_path / 'important.txt').write_text('mine')
    with pytest.raises(model.ContentError):
        build.build(tmp_path)
    assert (tmp_path / 'important.txt').read_text() == 'mine'


def test_removed_language_folder_is_cleaned_up(tmp_path):
    build.build(tmp_path)
    (tmp_path / 'fa').mkdir()                                  # pretend an earlier build made docs/fa/
    (tmp_path / 'fa' / 'index.html').write_text('old')
    manifest = tmp_path / build.MANIFEST
    manifest.write_text(manifest.read_text().replace('"assets"', '"assets", "fa"'))
    build.build(tmp_path)
    assert not (tmp_path / 'fa').exists()


def test_manifest_cannot_point_outside(tmp_path):
    build.build(tmp_path)
    (tmp_path / build.MANIFEST).write_text('{"owned": ["..", "/etc", "a/b", "index.html"]}')
    assert build.owned_entries(tmp_path) == ['index.html']
