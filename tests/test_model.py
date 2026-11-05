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
    (tmp_path / 'CNAME').write_text('keep me')
    written = build.build(tmp_path)
    index = (tmp_path / 'index.html').read_text()
    assert (tmp_path / 'CNAME').read_text() == 'keep me'              # the build only removes what it owns
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
