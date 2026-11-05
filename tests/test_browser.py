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
CDN = re.compile(r'https://cdn\.jsdelivr\.net/npm/((?:@[^/@]+/)?[^@/]+)(?:@[^/]+)?/(.+)')  # as in shoot.py
SIZES = [(1920, 1080), (1440, 900), (390, 844)]
SETTLED = """[...document.querySelectorAll('.cpv[data-kind="mermaid"]')].every(f =>
    f.querySelector('.mermaid-out svg') || f.dataset.view === 'code')"""


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
        except Exception as e:  # no browser: skip locally, but fail in CI (a broken install must not pass)
            msg = f'Chromium is not available: {str(e).splitlines()[0]}'
            pytest.fail(msg) if os.environ.get('CI') else pytest.skip(msg)
        yield b
        b.close()


def serve_offline(route, npm=None):
    """Block the network; serve jsDelivr files from npm (XREF_NPM_DIR) when given."""
    m = CDN.match(route.request.url)
    f = Path(npm) / m.group(1) / m.group(2) if npm and m else None
    if f and f.is_file():
        route.fulfill(body=f.read_bytes(), headers={'content-type': 'text/javascript'})
    else:
        route.abort()


@pytest.fixture
def open_page(browser, site):
    pages = []

    def opener(path='index.html', size=(1440, 900), zoom=None, hash='', offline=False):
        # reduced motion: the site then scrolls instantly (no smooth scroll to wait for)
        pg = browser.new_page(viewport={'width': size[0], 'height': size[1]}, reduced_motion='reduce')
        pg.errors = []
        pg.on('pageerror', lambda e: pg.errors.append(str(e)))
        # console errors too, except the requests this test blocks on purpose (fonts, CDN)
        pg.on(
            'console',
            lambda m: (
                pg.errors.append(m.text)
                if m.type == 'error' and 'net::ERR_' not in m.text and 'Failed to load resource' not in m.text
                else None
            ),
        )
        npm = None if offline else os.environ.get('XREF_NPM_DIR')
        pg.route(re.compile(r'^https?://.*'), lambda route: serve_offline(route, npm))
        if zoom:
            # runs in every frame, also the sandboxed preview iframe, where localStorage throws
            pg.add_init_script(f"try {{ localStorage.setItem('xref-zoom', '{zoom}') }} catch (e) {{}}")
        pg.goto((site / path).as_uri() + hash)
        # Mermaid draws after load and changes the page height: wait until every diagram has settled
        # (drawn, or fallen back to its code), or clicks land on the wrong row
        pg.wait_for_function(SETTLED, timeout=20000)
        pg.wait_for_timeout(150)
        pages.append(pg)
        return pg

    yield opener
    for pg in pages:
        pg.close()


def steps():
    site = model.load_site()
    return [st for sec in model.load_sections(site) for st in sec.steps]


# the index and every step's own page, so a new step is checked without editing this file
PAGES = ['index.html'] + [f'steps/{st.slug}.html' for st in steps()]


# ---------------------------------------------------------------- layout
@pytest.mark.parametrize('path', PAGES)
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


@pytest.mark.parametrize('path', PAGES)
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
    for path in PAGES:
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
    pg = open_page(offline=True)
    if not pg.locator('.cpv[data-kind="mermaid"]').count():
        pytest.skip('no Mermaid block')
    pg.wait_for_function('document.querySelector(".cpv[data-kind=mermaid]").dataset.view === "code"', timeout=5000)
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
    frames = pg.locator('.cpv[data-kind="html"] iframe')
    if not frames.count():
        pytest.skip('no HTML preview block')
    assert frames.first.get_attribute('sandbox') == ''  # no scripts, no same-origin
    assert pg.frame_locator('.cpv[data-kind="html"] iframe').first.locator('body').inner_text().strip()


# ---------------------------------------------------------------- accessibility (axe-core)
@pytest.mark.parametrize('path', PAGES)
@pytest.mark.parametrize('scheme', ['light', 'dark'])
@pytest.mark.parametrize('size', [(1920, 1080), (390, 844)])
def test_accessibility_has_no_serious_problems(browser, site, path, scheme, size):
    """axe-core: contrast, names and labels, heading order, one h1 per page, landmarks.
    Fails on serious and critical problems; moderate ones are printed (pytest -s) but allowed."""
    axe_mod = pytest.importorskip('axe_playwright_python.sync_playwright')
    pg = browser.new_page(viewport={'width': size[0], 'height': size[1]}, color_scheme=scheme)
    pg.route(re.compile(r'^https?://.*'), lambda r: r.abort())
    pg.goto((site / path).as_uri())
    pg.wait_for_timeout(300)
    violations = axe_mod.Axe().run(pg).response['violations']
    pg.close()
    report = [
        f'[{v["impact"]}] {v["id"]}: {v["help"]} -> ' + ', '.join(n['target'][0] for n in v['nodes'][:4])
        for v in violations
    ]
    print('\n'.join(report))
    serious = [r for r, v in zip(report, violations, strict=True) if v['impact'] in ('serious', 'critical')]
    assert serious == []


# ---------------------------------------------------------------- regressions from the second audit
def test_broken_mermaid_leaves_nothing_behind(open_page):
    """A syntax error once left a 'Syntax error in text' box at the end of the page, one more per redraw."""
    if not os.environ.get('XREF_NPM_DIR'):
        pytest.skip('set XREF_NPM_DIR to a folder with mermaid/ from npm to test drawing')
    pg = open_page(size=(1920, 1080))
    pg.wait_for_selector('.mermaid-out svg', timeout=15000)
    pg.evaluate("""() => { const s = document.querySelector('.cpv[data-kind="mermaid"] script.src');
        s.textContent = JSON.stringify('flowchart LR\\n  A --> --> B (((');
        document.dispatchEvent(new Event('xref:look')); }""")
    pg.wait_for_function('document.querySelector(".cpv[data-kind=mermaid]").dataset.view === "code"', timeout=10000)
    pg.click('[data-tool="theme"]')  # one more redraw
    pg.wait_for_timeout(800)
    stray = pg.evaluate('[...document.body.children].filter(e => /^d?mmd-/.test(e.id)).map(e => e.id)')
    assert stray == []
    assert 'error' in pg.locator('.mermaid-out').first.inner_text()


def test_bracket_keys_move_by_position(open_page):
    """Regression: from a section header, ] once jumped back to the first step of the page."""
    pg = open_page(size=(1920, 1080))
    tops = '[...document.querySelectorAll(".step")].map(s => Math.round(s.getBoundingClientRect().top))'
    ids = pg.evaluate('[...document.querySelectorAll(".step")].map(s => s.id)')
    at_top = lambda n: -2 < pg.evaluate(tops)[n] < 120  # noqa: E731
    # from the last section's header, ] goes to the first step after it
    first_after = pg.evaluate('[...document.querySelectorAll(".section")].at(-1).querySelector(".step").id')
    pg.evaluate('[...document.querySelectorAll(".section")].at(-1).scrollIntoView()')
    pg.wait_for_timeout(200)
    pg.keyboard.press(']')
    pg.wait_for_timeout(300)
    assert at_top(ids.index(first_after)), 'did not go to the next step after the section header'
    # from the last step, ] stays
    pg.evaluate('[...document.querySelectorAll(".step")].at(-1).scrollIntoView()')
    pg.wait_for_timeout(200)
    y = pg.evaluate('scrollY')
    pg.keyboard.press(']')
    pg.wait_for_timeout(300)
    assert abs(pg.evaluate('scrollY') - y) < 2
    # [ walks up through every step
    for n in range(len(ids) - 2, -1, -1):
        pg.keyboard.press('[')
        pg.wait_for_timeout(300)
        assert at_top(n), f'{ids[n]} not at the top after ['


def test_selecting_code_copies_only_the_code(open_page):
    """The copy fallback selects the whole <pre>; cross-comment numbers must not come along."""
    pg = open_page()
    st = steps()[0]
    cid, code = next(iter(st.code.items()))
    text = pg.evaluate(f"""() => {{ const pre = document.querySelector('#{st.id} pre[data-code="{cid}"]');
        const r = document.createRange(); r.selectNodeContents(pre);
        const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); return sel.toString(); }}""")
    lines = [line.strip() for line in text.strip('\n').split('\n')]
    assert lines == [line.strip() for line in code.lines]
