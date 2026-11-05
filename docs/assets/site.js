// Shared behaviour for every page (index and one page per step).
// Page data comes from <script id="page-data" type="application/json">: column ids and UI strings.
(() => {
  let DATA = { cols: [], ui: {} };
  try { DATA = JSON.parse(document.getElementById('page-data').textContent); } catch (e) {}
  const COLS = DATA.cols;
  const T = DATA.ui;
  const root = document.documentElement;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const behavior = () => reduced.matches ? 'auto' : 'smooth';

  // ---------- theme: auto -> light -> dark (head script already applied the saved one)
  const THEMES = ['auto', 'light', 'dark'];
  const themeBtn = document.querySelector('[data-tool="theme"]');
  // icons as inline SVG, so they never depend on a font having the glyph
  const ICON = {
    auto: '<circle cx="8" cy="8" r="6"/><path d="M8 2a6 6 0 0 1 0 12z" fill="currentColor"/>',
    light: '<circle cx="8" cy="8" r="3"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.4 1.4M11.6 11.6 13 13M3 13l1.4-1.4M11.6 4.4 13 3"/>',
    dark: '<path d="M13 9.5A5.5 5.5 0 0 1 6.5 3a5.5 5.5 0 1 0 6.5 6.5z" fill="currentColor"/>',
  };
  function applyTheme(t) {
    if (t === 'auto') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', t);
    if (themeBtn) {
      const label = T['theme_' + t] || t;
      themeBtn.innerHTML = `<svg width="1.1em" height="1.1em" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">${ICON[t]}</svg> `;
      themeBtn.append(label);
      themeBtn.setAttribute('aria-label', (T.theme || 'Theme') + ': ' + label);
    }
  }
  let theme = THEMES.includes(store.get('xref-theme')) ? store.get('xref-theme') : 'auto';
  applyTheme(theme);
  themeBtn?.addEventListener('click', () => {
    theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
    store.set('xref-theme', theme);
    applyTheme(theme);
    document.dispatchEvent(new Event('xref:look'));   // diagrams redraw in the new colours
  });

  // ---------- text size: --z from 0.8 to 1.6
  const ZMIN = 0.8, ZMAX = 1.6, ZSTEP = 0.1;
  let zoom = Number(store.get('xref-zoom')) || 1;
  function applyZoom(z) {
    zoom = Math.min(ZMAX, Math.max(ZMIN, Math.round(z * 10) / 10));
    root.style.setProperty('--z', zoom);
    store.set('xref-zoom', String(zoom));
    document.dispatchEvent(new Event('xref:look'));   // diagrams redraw at the new size
  }
  applyZoom(zoom);
  document.querySelector('[data-tool="font-down"]')?.addEventListener('click', () => applyZoom(zoom - ZSTEP));
  document.querySelector('[data-tool="font-reset"]')?.addEventListener('click', () => applyZoom(1));
  document.querySelector('[data-tool="font-up"]')?.addEventListener('click', () => applyZoom(zoom + ZSTEP));

  // ---------- columns: toggles (wide screens) and tabs (narrow screens)
  const narrow = matchMedia('(max-width: 1100px)');
  let hidden = new Set();
  try { hidden = new Set(JSON.parse(store.get('xref-hidden') || '[]').filter(c => COLS.includes(c))); } catch (e) {}
  if (hidden.size >= COLS.length) hidden.clear();
  let tab = COLS.includes(store.get('xref-tab')) ? store.get('xref-tab') : COLS[0];

  function applyCols() {
    const n = narrow.matches;
    document.querySelectorAll('[data-col]').forEach(el => {
      if (el.matches('.toggle, .tab')) return;
      const c = el.dataset.col;
      el.classList.toggle('gone', n ? !!el.closest('.sbs') && c !== tab : hidden.has(c));
    });
    document.querySelectorAll('.toggle').forEach(b => b.setAttribute('aria-pressed', String(!hidden.has(b.dataset.col))));
    document.querySelectorAll('.tab').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.col === tab)));
    document.querySelectorAll('.xc').forEach(x => x.style.setProperty('--nc', n ? COLS.length : COLS.length - hidden.size));
  }
  function toggleCol(c) {
    if (!hidden.has(c) && COLS.length - hidden.size <= 1) return;   // keep at least one column
    hidden.has(c) ? hidden.delete(c) : hidden.add(c);
    store.set('xref-hidden', JSON.stringify([...hidden]));
    applyCols();
  }
  function setTab(c) { tab = c; store.set('xref-tab', c); applyCols(); }
  document.querySelectorAll('.toggle').forEach(b => b.addEventListener('click', () => toggleCol(b.dataset.col)));
  document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.col)));
  narrow.addEventListener('change', applyCols);
  applyCols();

  // ---------- copy buttons
  // data-copy="<column>": the step's <script class="raw"> holds every column's code.
  // data-copy-src: a Markdown fence; its own <script class="src"> holds the code.
  function sourceOf(btn) {
    try {
      if (btn.hasAttribute('data-copy-src')) return JSON.parse(btn.closest('figure').querySelector('script.src').textContent);
      return JSON.parse(btn.closest('.step').querySelector('script.raw').textContent)[btn.dataset.copy] || '';
    } catch (e) { return ''; }
  }
  document.querySelectorAll('.copy').forEach(btn => btn.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(sourceOf(btn)); btn.textContent = T.copied || 'Copied'; }
    catch (e) {
      const pre = (btn.closest('.col') || btn.closest('figure')).querySelector('pre');
      const r = document.createRange(); r.selectNodeContents(pre);
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
      btn.textContent = T.press_ctrl_c || 'Press Ctrl+C';
    }
    setTimeout(() => { btn.textContent = T.copy_code || 'Copy'; }, 1800);
  }));

  // ---------- code + preview blocks (```mermaid, ```html preview): Both / Code / Preview
  function setView(fig, view) {
    fig.dataset.view = view;
    fig.querySelectorAll('.cp-views button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
  }
  document.querySelectorAll('.cp').forEach(fig =>
    fig.querySelectorAll('.cp-views button').forEach(b => b.addEventListener('click', () => setView(fig, b.dataset.view))));

  // ---------- Mermaid: loaded only when the page has a diagram; pinned URL from content/site.toml
  const diagrams = [...document.querySelectorAll('.cp[data-kind="mermaid"]')];
  const darkMedia = matchMedia('(prefers-color-scheme: dark)');
  const isDark = () => root.dataset.theme === 'dark' || (root.dataset.theme !== 'light' && darkMedia.matches);
  let mermaid = null, drawing = 0;
  function failed(fig, msg) {
    fig.querySelector('.mermaid-out').innerHTML = '';
    const p = document.createElement('p'); p.className = 'small'; p.textContent = msg;
    fig.querySelector('.mermaid-out').append(p);
    setView(fig, 'code');
  }
  async function drawDiagrams() {
    if (!mermaid) return;
    const run = ++drawing;                                   // a newer redraw cancels an older one
    const font = getComputedStyle(document.body);
    mermaid.initialize({
      startOnLoad: false, securityLevel: 'strict', theme: isDark() ? 'dark' : 'default',
      fontFamily: font.fontFamily, themeVariables: { fontSize: font.fontSize },   // grows on a TV and with A+
    });
    for (const [i, fig] of diagrams.entries()) {
      let src = '';
      try { src = JSON.parse(fig.querySelector('script.src').textContent); } catch (e) {}
      try {
        const { svg, bindFunctions } = await mermaid.render(`mmd-${i}-${run}`, src);
        if (run !== drawing) return;
        const out = fig.querySelector('.mermaid-out');
        out.innerHTML = svg;
        bindFunctions?.(out);
        const vb = out.querySelector('svg')?.viewBox?.baseVal;          // natural size, used on small screens
        if (vb && vb.width) out.style.setProperty('--natural', `${Math.round(vb.width)}px`);
      } catch (e) {
        failed(fig, T.diagram_error || 'This diagram has an error.');
      }
    }
  }
  if (diagrams.length && DATA.libs && DATA.libs.mermaid) {
    import(DATA.libs.mermaid)
      .then(mod => { mermaid = mod.default; drawDiagrams(); })
      .catch(() => diagrams.forEach(fig => failed(fig, T.diagram_offline || 'The diagram needs internet to draw.')));
    document.addEventListener('xref:look', drawDiagrams);
    darkMedia.addEventListener('change', () => { if (!root.dataset.theme) drawDiagrams(); });
  }

  // ---------- cross-comments: light up matching lines in every column
  const pinned = new Map();   // step id -> pinned row
  function clear(step) {
    step.querySelectorAll('.code.has-hl').forEach(c => c.classList.remove('has-hl'));
    step.querySelectorAll('.ln.hl').forEach(l => l.classList.remove('hl'));
    step.querySelectorAll('.mks i.on').forEach(i => i.classList.remove('on'));
  }
  function show(step, row) {
    clear(step);
    const num = row.dataset.n;
    let first = null;
    Object.entries(JSON.parse(row.dataset.refs)).forEach(([c, ranges]) => {
      const code = step.querySelector(`.code[data-code="${c}"]`);
      if (!code || !ranges.length) return;
      code.classList.add('has-hl');
      ranges.forEach(([a, z]) => {
        for (let n = a; n <= z; n++) {
          const ln = code.querySelector(`.ln[data-n="${n}"]`);
          if (!ln) continue;
          ln.classList.add('hl');
          ln.querySelectorAll('.mks i').forEach(i => { if (i.textContent === num) i.classList.add('on'); });
          if (!first && !ln.closest('.gone')) first = ln;
        }
      });
    });
    return first;
  }
  function pin(step, row, scroll) {
    step.querySelectorAll('.xrow').forEach(r => r.setAttribute('aria-pressed', 'false'));
    if (!row) { pinned.delete(step.id); clear(step); return; }
    row.setAttribute('aria-pressed', 'true');
    pinned.set(step.id, row);
    const first = show(step, row);
    if (scroll && first) {
      const r = first.getBoundingClientRect();
      if (r.top < 90 || r.bottom > innerHeight) first.scrollIntoView({ block: 'center', behavior: behavior() });
    }
  }
  document.querySelectorAll('.step').forEach(step => {
    const restore = () => { const p = pinned.get(step.id); p ? show(step, p) : clear(step); };
    step.querySelectorAll('.xrow').forEach(row => {
      row.addEventListener('mouseenter', () => show(step, row));
      row.addEventListener('mouseleave', restore);
      row.addEventListener('focus', () => show(step, row));
      row.addEventListener('blur', restore);
      row.addEventListener('click', () => pin(step, pinned.get(step.id) === row ? null : row, false));
    });
  });
  function pinFromHash(id, smooth) {
    const row = id && document.getElementById(id);
    if (!row || !row.classList.contains('xrow')) return false;
    row.scrollIntoView({ block: 'center', behavior: smooth ? behavior() : 'auto' });
    pin(row.closest('.step'), row, false);
    return true;
  }
  document.querySelectorAll('a[data-x]').forEach(a => a.addEventListener('click', e => {
    if (pinFromHash(a.dataset.x, true)) { e.preventDefault(); history.replaceState(null, '', '#' + a.dataset.x); }
  }));
  let hash = location.hash.slice(1);
  try { hash = decodeURIComponent(hash); } catch (e) {}   // a malformed hash (#100%) must not stop the script
  pinFromHash(hash, false);

  // ---------- where am I: rail highlight + current step
  const targets = [...document.querySelectorAll('#summary, .section, .step')];
  const rail = document.querySelector('.rail');
  const railLinks = new Map([...document.querySelectorAll('.rail a[data-target]')].map(a => [a.dataset.target, a]));
  let current = null, active = null;
  // Keep the active link visible by scrolling the rail only. scrollIntoView() would also scroll
  // the window, and with the sticky rail on narrow screens that locked the page in place.
  function revealInRail(a) {
    if (!rail) return;
    const r = rail.getBoundingClientRect(), l = a.getBoundingClientRect();
    if (rail.scrollWidth > rail.clientWidth && (l.left < r.left || l.right > r.right))          // narrow: horizontal bar
      rail.scrollTo({ left: rail.scrollLeft + l.left - r.left - rail.clientWidth / 3 });
    else if (rail.scrollHeight > rail.clientHeight && (l.top < r.top || l.bottom > r.bottom))  // wide: vertical list
      rail.scrollTo({ top: rail.scrollTop + l.top - r.top - rail.clientHeight / 3 });
  }
  function track() {
    if (!targets.length) return;
    const line = innerHeight * 0.3;
    let at = targets[0];
    for (const t of targets) if (t.getBoundingClientRect().top <= line) at = t;
    current = at.classList.contains('step') ? at : null;
    const a = railLinks.get(at.id) || railLinks.get(document.body.dataset.page);
    if (a === active) return;                            // nothing changed: touch nothing
    active?.classList.remove('on');
    active = a || null;
    if (a) { a.classList.add('on'); revealInRail(a); }
  }
  let ticking = false;
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; track(); }); } }, { passive: true });
  track();

  // ---------- keyboard
  const steps = [...document.querySelectorAll('.step')];
  addEventListener('keydown', e => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.closest('input, textarea, select, [contenteditable]')) return;
    const k = e.key;
    const i = Number(k);
    if (Number.isInteger(i) && i >= 1 && i <= COLS.length) {
      narrow.matches ? setTab(COLS[i - 1]) : toggleCol(COLS[i - 1]);
      return;
    }
    if (k === 'c' || k === 'C') {
      const step = current || steps[0];
      const rows = step ? [...step.querySelectorAll('.xrow')] : [];
      if (!rows.length) return;
      const at = rows.indexOf(pinned.get(step.id));
      const next = e.shiftKey ? (at <= 0 ? rows.length - 1 : at - 1) : (at + 1) % rows.length;
      pin(step, rows[next], true);
      e.preventDefault();
    } else if (k === ']' || k === '[') {
      const at = current ? steps.indexOf(current) : -1;
      const to = steps[k === ']' ? at + 1 : at - 1];
      if (to) { to.scrollIntoView({ block: 'start', behavior: behavior() }); e.preventDefault(); return; }
      // a single-step page: follow its previous / next link to the other step pages
      const link = document.body.classList.contains('step-page') &&
        document.querySelector(k === ']' ? '.prevnext a.next' : '.prevnext a.prev');
      if (link) location.href = link.href;
    } else if (k === 'Escape') {
      steps.forEach(s => pin(s, null));
    }
  });
})();
