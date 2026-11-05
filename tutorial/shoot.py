"""Screenshots every column of every step and compares the pixels.

Run from anywhere:  python tutorial/shoot.py [--npm-dir DIR] [--chromium PATH]

For each step folder in content/ it renders quasar.html, nicegui_app.py and
vue.html in headless Chromium, saves shots/<column>.png and writes
shots/result.json with the pixel difference against the first column.
tutorial/build.py reads those files. Run this after changing a column file.

--npm-dir DIR   Serve CDN files (cdn.jsdelivr.net, unpkg.com) from unpacked npm
                packages instead of the network: DIR/vue/..., DIR/quasar/...
                Use it when the CDN is blocked. The files are the same ones the
                CDN serves, because both CDNs mirror the npm registry.
--chromium PATH Use this Chromium binary instead of Playwright's own.

Needs: pip install playwright  (and once: playwright install chromium)
"""
import argparse
import base64
import json
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date
from importlib.metadata import version
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model  # noqa: E402

ROOT = model.ROOT
VIEW = {'width': 480, 'height': 180}   # CSS px; enough for the examples, same for every column
SCALE = 2                              # device pixels per CSS px, sharp on 4K / 8K screens
CDN = re.compile(r'https://(?:cdn\.jsdelivr\.net/npm|unpkg\.com)/(@?[^@/]+)@[^/]+/(.+)')

# Runs a NiceGUI column file with show=False, reload=False and a chosen port.
NICEGUI_RUNNER = '''
import runpy, sys
from nicegui import ui
_run = ui.run
def run(*a, **k):
    k.update(show=False, reload=False, port=int(sys.argv[2]))
    _run(*a, **k)
ui.run = run
runpy.run_path(sys.argv[1], run_name='__main__')
'''

COMPARE_JS = '''async ([a, b]) => {
  const load = src => new Promise((ok, err) => { const i = new Image(); i.onload = () => ok(i); i.onerror = err; i.src = src; });
  const [ia, ib] = await Promise.all([load(a), load(b)]);
  if (ia.width !== ib.width || ia.height !== ib.height) return -1;
  const px = img => { const c = new OffscreenCanvas(img.width, img.height); const x = c.getContext('2d');
    x.drawImage(img, 0, 0); return x.getImageData(0, 0, img.width, img.height).data; };
  const da = px(ia), db = px(ib);
  let n = 0;
  for (let i = 0; i < da.length; i += 4)
    if (da[i] !== db[i] || da[i + 1] !== db[i + 1] || da[i + 2] !== db[i + 2] || da[i + 3] !== db[i + 3]) n++;
  return n;
}'''


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_http(url, proc, log, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            log.seek(0)
            raise RuntimeError(f'NiceGUI exited early:\n{log.read()}')
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f'{url} did not answer in {timeout} s')


def route_cdn(page, npm_dir):
    def handle(route):
        m = CDN.match(route.request.url)
        f = npm_dir / m.group(1) / m.group(2) if m else None
        if f and f.is_file():
            ctype = 'text/css' if f.suffix == '.css' else 'text/javascript'
            route.fulfill(body=f.read_bytes(), headers={'content-type': ctype, 'access-control-allow-origin': '*'})
        else:
            route.abort()
    page.route(re.compile(r'https://(cdn\.jsdelivr\.net|unpkg\.com)/.*'), handle)


def render(browser, url, npm_dir):
    page = browser.new_page(viewport=VIEW, device_scale_factor=SCALE)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('requestfailed', lambda r: errors.append(f'{r.url}: {r.failure}'))
    if npm_dir:
        route_cdn(page, npm_dir)
    page.goto(url, wait_until='networkidle')
    page.wait_for_timeout(300)
    if errors:
        raise RuntimeError(f'{url}:\n  ' + '\n  '.join(errors))
    libs = page.evaluate('''async () => {
      const out = {};
      if (window.Quasar && Quasar.version) out.quasar = Quasar.version;
      // Vue stores the app on its mount element, which also works for ES-module pages
      const app = document.querySelector('[data-v-app]');
      const v = (app && app.__vue_app__ && app.__vue_app__.version) || (window.Vue && Vue.version);
      if (v) out.vue = v;
      return out;
    }''')
    png = page.screenshot()
    page.close()
    return png, libs


def shoot_step(browser, step, npm_dir, columns):
    shots = step / 'shots'
    shots.mkdir(exist_ok=True)
    pngs, libs = {}, {}
    for col in columns:
        f = model.column_file(step, col)
        if not f:
            continue
        if f.suffix == '.py':
            port = free_port()
            log = tempfile.TemporaryFile('w+')   # a file, not a pipe: a full pipe would block the server
            proc = subprocess.Popen([sys.executable, '-c', NICEGUI_RUNNER, str(f), str(port)],
                                    cwd=step, stdout=log, stderr=subprocess.STDOUT, text=True)
            try:
                wait_http(f'http://127.0.0.1:{port}/', proc, log)
                pngs[col], libs[col] = render(browser, f'http://127.0.0.1:{port}/', None)
            finally:
                proc.terminate()
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                log.close()
            libs[col]['nicegui'] = version('nicegui')
        else:
            pngs[col], libs[col] = render(browser, f.as_uri(), npm_dir)
        (shots / f'{col}.png').write_bytes(pngs[col])

    first = next(iter(pngs))
    page = browser.new_page()
    uri = lambda b: 'data:image/png;base64,' + base64.b64encode(b).decode()
    diff = {c: page.evaluate(COMPARE_JS, [uri(pngs[first]), uri(pngs[c])]) for c in pngs if c != first}
    page.close()
    result = {
        'tested': date.today().isoformat(),
        'view': VIEW, 'scale': SCALE,
        'compared_to': first,
        'diff_pixels': diff,
        'libraries': libs,
        'npm_dir_used': bool(npm_dir),
    }
    (shots / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    same = all(v == 0 for v in diff.values())
    print(f'{step.relative_to(ROOT)}: {", ".join(pngs)} -> {"identical" if same else diff}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--npm-dir', type=Path)
    ap.add_argument('--chromium')
    args = ap.parse_args()
    site = model.load_site()
    steps = model.step_dirs()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium) if args.chromium else p.chromium.launch()
        for step in steps:
            shoot_step(browser, step, args.npm_dir, site.column_ids)
        browser.close()


if __name__ == '__main__':
    main()
