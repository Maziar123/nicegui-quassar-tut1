"""Browser tests: the built site in headless Chromium.  Run:  python -m pytest -m browser

Needs Chromium for Playwright (`playwright install chromium`), or XREF_CHROMIUM=/path/to/chromium.
Skipped when no browser can start. External requests (fonts, CDN) are blocked so results do not depend
on the network. Set XREF_NPM_DIR to unpacked npm packages (DIR/mermaid/...) to also test drawing Mermaid.
Expected highlight lines come from model.py, so every new step is checked without editing this file.
"""

import os
import re
from pathlib import Path

import build
import model
import pytest

pytestmark = pytest.mark.browser
playwright = pytest.importorskip('playwright.sync_api')
CDN = re.compile(r'https://cdn\.jsdelivr\.net/npm/(@?[^@/]+)@[^/]+/(.+)')
SIZES = [(1920, 1080), (1440, 900), (390, 844)]


@pytest.fixture(scope='module')
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp('site') / 'docs'
    build.build(out)
    return out


@pytest.fixture(scope='module')
def browser():
    with playwright.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=os.environ.get('XREF_CHROMIUM') or None)
        except Exception as e:  # no browser installed: skip, do not fail
            pytest.skip(f'Chromium is not available: {str(e).splitlines()[0]}')
        yield b
        b.close()


def serve_offline(route):
    """Block the network; serve jsDelivr files from XREF_NPM_DIR when it is set."""
    npm = os.environ.get('XREF_NPM_DIR')
    m = CDN.match(route.request.url)
    f = Path(npm) / m.group(1) / m.group(2) if npm and m else None
    if f and f.is_file():
        route.fulfill(body=f.read_bytes(), headers={'content-type': 'text/javascript'})
    else:
        route.abort()


@pytest.fixture
def open_page(browser, site):
    pages = []

    def opener(path='index.html', size=(1440, 900), zoom=None, hash=''):
        pg = browser.new_page(viewport={'width': size[0], 'height': size[1]})
        pg.errors = []
        pg.on('pageerror', lambda e: pg.errors.append(str(e)))
        pg.route(re.compile(r'^https?://.*'), serve_offline)
        if zoom:
            # runs in every frame, also the sandboxed preview iframe, where localStorage throws
            pg.add_init_script(f"try {{ localStorage.setItem('xref-zoom', '{zoom}') }} catch (e) {{}}")
        pg.goto((site / path).as_uri() + hash)
        pg.wait_for_timeout(150)
        pages.append(pg)
        return pg

    yield opener
    for pg in pages:
        pg.close()


def steps():
    site = model.load_site()
    return [st for sec in model.load_sections(site) for st in sec.steps]


# ---------------------------------------------------------------- layout
@pytest.mark.parametrize('path', ['index.html', 'steps/1-1.html'])
@pytest.mark.parametrize('size', SIZES)
@pytest.mark.parametrize('zoom', [1, 1.6])
def test_no_sideways_scroll_and_no_errors(open_page, path, size, zoom):
    pg = open_page(path, size, zoom)
    assert pg.evaluate('document.documentElement.scrollWidth') <= size[0]
    assert pg.errors == []


SCROLL_TO_EACH_PART = """async () => {
  const out = [];
  for (const el of document.querySelectorAll('#summary, .section, .step')) {
    const y = Math.min(Math.round(el.getBoundingClientRect().top + scrollY),
                       document.documentElement.scrollHeight - innerHeight);
    scrollTo(0, y);
    await new Promise(r => setTimeout(r, 250));
    out.push([el.id, y, Math.round(scrollY)]);
  }
  return out;
}"""


@pytest.mark.parametrize('path', ['index.html', 'steps/1-1.html'])
@pytest.mark.parametrize('size', [(390, 844), (800, 600), (1440, 900)])
def test_page_stays_where_it_is_scrolled(open_page, path, size):
    """Regression: the sticky rail once pulled the window back whenever the active rail link changed
    (scrollIntoView on narrow screens). Visit every part so the active link changes each time."""
    pg = open_page(path, size)
    moved = [(part, want, got) for part, want, got in pg.evaluate(SCROLL_TO_EACH_PART) if abs(got - want) > 2]
    assert moved == [], f'window snapped back: {moved}'
    pg.mouse.wheel(0, 400)
    pg.wait_for_timeout(200)
    assert pg.errors == []


def test_malformed_hash_does_not_stop_the_script(open_page):
    pg = open_page(hash='#100%')
    pg.keyboard.press('2')
    assert pg.errors == []
    assert pg.evaluate('document.querySelector(".sbs .col[data-col=nicegui]").classList.contains("gone")')


# ---------------------------------------------------------------- cross-comments
@pytest.mark.parametrize('st', steps(), ids=lambda s: s.num)
def test_every_cross_comment_lights_its_lines(open_page, st):
    pg = open_page(size=(1920, 1080))
    for x in st.cross:
        pg.click(f'#{st.id}-x{x.n}')
        lit = pg.evaluate(f"""Object.fromEntries([...document.querySelectorAll('#{st.id} .sbs .code')].map(c =>
            [c.dataset.code, [...c.querySelectorAll('.ln.hl')].map(l => +l.dataset.n)]))""")
        for cid, ref in x.refs.items():
            want = sorted({n for a, b in ref.ranges for n in range(a, b + 1)})
            assert lit.get(cid, []) == want, f'{st.num} cross-comment {x.n}, column {cid}'
    assert pg.errors == []


def test_c_key_steps_through_cross_comments(open_page):
    pg = open_page(size=(1920, 1080))
    pg.evaluate('scrollTo(0, document.querySelector(".step").getBoundingClientRect().top + scrollY)')
    pg.wait_for_timeout(100)
    pg.keyboard.press('c')
    pg.keyboard.press('c')
    pressed = pg.evaluate('[...document.querySelector(".step").querySelectorAll(".xrow")].map(r => r.ariaPressed)')
    assert pressed[:2] == ['false', 'true']


# ---------------------------------------------------------------- top bar
def test_column_toggle_and_text_size_and_theme(open_page):
    pg = open_page()
    pg.keyboard.press('2')
    assert pg.evaluate('document.querySelector(".sbs .col[data-col=nicegui]").offsetParent') is None
    before = pg.evaluate('parseFloat(getComputedStyle(document.body).fontSize)')
    pg.click('[data-tool="font-up"]')
    assert pg.evaluate('parseFloat(getComputedStyle(document.body).fontSize)') > before
    seen = []
    for _ in range(3):
        pg.click('[data-tool="theme"]')
        seen.append(pg.evaluate('document.documentElement.dataset.theme || "auto"'))
    assert seen == ['light', 'dark', 'auto']


def test_local_links_resolve(open_page, site):
    for path in ['index.html', 'steps/1-1.html']:
        pg = open_page(path)
        hrefs = pg.evaluate(
            '[...document.querySelectorAll("a[href], img[src], link[href], script[src]")].map(e => '
            'e.getAttribute("href") || e.getAttribute("src"))'
        )
        for h in hrefs:
            if re.match(r'^[a-z]+:|^#', h):
                continue
            target = (site / path).parent / h.split('#')[0]
            assert target.resolve().exists(), f'{path}: broken {h}'


# ---------------------------------------------------------------- Markdown blocks
def test_mermaid_without_network_shows_the_code(open_page):
    if os.environ.get('XREF_NPM_DIR'):
        pytest.skip('XREF_NPM_DIR is set: Mermaid can load')
    pg = open_page()
    if not pg.locator('.cp[data-kind="mermaid"]').count():
        pytest.skip('no Mermaid block')
    pg.wait_for_function('document.querySelector(".cp[data-kind=mermaid]").dataset.view === "code"', timeout=5000)
    assert 'internet' in pg.locator('.mermaid-out').first.inner_text()


def test_mermaid_draws_and_follows_the_theme(open_page):
    if not os.environ.get('XREF_NPM_DIR'):
        pytest.skip('set XREF_NPM_DIR to a folder with mermaid/ from npm to test drawing')
    pg = open_page(size=(1920, 1080))
    pg.wait_for_selector('.mermaid-out svg', timeout=15000)
    node = 'document.querySelector(".mermaid-out svg .node rect, .mermaid-out svg .node polygon")'
    fill = f'getComputedStyle({node}).fill'
    light = pg.evaluate(fill)
    pg.click('[data-tool="theme"]')
    pg.click('[data-tool="theme"]')  # auto -> light -> dark
    pg.wait_for_function(f'{fill} !== {light!r}', timeout=10000)


def test_html_preview_is_sandboxed_and_renders(open_page):
    pg = open_page()
    frames = pg.locator('.cp[data-kind="html"] iframe')
    if not frames.count():
        pytest.skip('no HTML preview block')
    assert frames.first.get_attribute('sandbox') == ''  # no scripts, no same-origin
    assert pg.frame_locator('.cp[data-kind="html"] iframe').first.locator('body').inner_text().strip()
