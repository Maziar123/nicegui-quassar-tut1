"""The content model: reads content/ into typed objects.

Shared by build.py (renders pages) and shoot.py (screenshots). Templates see these objects,
so attribute names here are the names templates use. Dataclasses (not dicts) keep a content key
from ever colliding with a dict method in Jinja (t.copy once rendered "<built-in method copy>").
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import HtmlLexer, PythonLexer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTENT = ROOT / 'content'
I18N = HERE / 'i18n'
LEXERS = {'.html': HtmlLexer, '.py': PythonLexer}
LANG_LABEL = {'.html': 'HTML', '.py': 'Python'}
# Pygments token classes get a prefix: its short names (sr, no, cp, nt...) clashed with site classes
TOKEN_PREFIX = 'tk-'
LANG_CODE = re.compile(r'[a-z]{2,3}(-[A-Za-z0-9]{2,8})?')


class ContentError(Exception):
    """Something in content/ is wrong. The message names the file."""


def rel(path: Path) -> str:
    """Path for messages: relative to the repo when inside it."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


# ------------------------------------------------------------------ toml + languages
def merge(base, over):
    """Deep merge for translations: tables merge key by key, lists of tables item by item,
    anything else is replaced by the translation."""
    if isinstance(base, dict) and isinstance(over, dict):
        return {**base, **{k: merge(base[k], v) if k in base else v for k, v in over.items()}}
    if isinstance(base, list) and isinstance(over, list) and all(isinstance(x, dict) for x in base + over):
        # zip stops at the shorter list on purpose: the rest of either list is added after
        return [merge(b, o) for b, o in zip(base, over, strict=False)] + base[len(over) :] + over[len(base) :]
    return over


def read_toml(path: Path, lang: str, default: str) -> dict:
    """Read path, then merge path.<lang>.toml over it when lang is not the default.
    A syntax error names the file it is in (the translation, not the English file)."""
    data = parse_toml(path)
    tr = path.with_name(f'{path.stem}.{lang}.toml')
    if lang != default and tr.is_file():
        data = merge(data, parse_toml(tr))
    return data


def parse_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as e:
        raise ContentError(f'{rel(path)}: {e}') from None


def strings(lang: str, default: str) -> SimpleNamespace:
    """UI strings as attributes (t.copy_code). A missing key falls back to the default language."""
    t = tomllib.loads((I18N / f'{default}.toml').read_text(encoding='utf-8'))
    if lang != default:
        f = I18N / f'{lang}.toml'
        if not f.is_file():
            raise ContentError(f'no UI strings for language {lang!r}: add tutorial/i18n/{lang}.toml')
        t.update(tomllib.loads(f.read_text(encoding='utf-8')))
    return SimpleNamespace(**t)


# ------------------------------------------------------------------ markers
def hit(line: str, marker: str) -> bool:
    """'==x': line is exactly x. '=x': line is x after trimming. 'x': line contains x."""
    if marker.startswith('=='):
        return line == marker[2:]
    if marker.startswith('='):
        return line.strip() == marker[1:]
    return marker in line


def find(lines: list[str], marks: list[str], where: str) -> tuple[int, int]:
    """1-based (first, last) line of a [start] or [start, end] marker range."""
    if not 1 <= len(marks) <= 2:
        raise ContentError(f'{where}: a range is ["start"] or ["start", "end"], got {marks!r}')
    start, end = marks[0], (marks[1] if len(marks) == 2 else None)
    i = next((n for n, line in enumerate(lines) if hit(line, start)), None)
    if i is None:
        raise ContentError(f'{where}: no line matches {start!r}')
    if end is None:
        return i + 1, i + 1
    j = next((n for n in range(i, len(lines)) if hit(lines[n], end)), None)
    if j is None:
        raise ContentError(f'{where}: no line after {start!r} matches {end!r}')
    return i + 1, j + 1


def label(ranges) -> str:
    return ', '.join(f'L{a}' if a == b else f'L{a}–{b}' for a, b in sorted(ranges))


# ------------------------------------------------------------------ objects
@dataclass
class Column:
    id: str
    name: str
    what: str = ''
    lang: str = ''
    needs: str = ''
    tested: str = ''  # filled from the screenshots' library versions


@dataclass
class Site:
    lang: str
    default_lang: str
    languages: list[str]
    title: str
    subtitle: str
    lead: list[str]
    how_to_read: list[str]
    setup: str
    setup_note: str
    columns: list[Column]
    hero: dict[str, str] = field(default_factory=dict)  # column id -> one line of code
    libs: dict[str, str] = field(default_factory=dict)  # pinned browser libraries, e.g. mermaid -> URL

    @property
    def column_ids(self) -> list[str]:
        return [c.id for c in self.columns]

    def column(self, cid: str) -> Column:
        return next(c for c in self.columns if c.id == cid)

    def names(self, ids) -> str:
        return ', '.join(self.column(cid).name for cid in ids)


@dataclass
class Code:
    file: str
    ext: str
    text: str
    marks: dict[int, list[int]] = field(default_factory=dict)  # line -> cross-comment numbers

    @property
    def lines(self) -> list[str]:
        return self.text.rstrip('\n').split('\n')

    @property
    def nlines(self) -> int:
        return len(self.lines)

    @property
    def lang(self) -> str:
        return LANG_LABEL[self.ext]

    @property
    def rows(self) -> list[str]:
        """Highlighted HTML, one string per line. Pygments closes and reopens spans at line ends.
        stripnl=False keeps leading blank lines, so row n is always line n."""
        html = highlight(
            self.text, LEXERS[self.ext](stripnl=False), HtmlFormatter(nowrap=True, classprefix=TOKEN_PREFIX)
        )
        rows = [r or ' ' for r in html.rstrip('\n').split('\n')]
        if len(rows) != self.nlines:
            raise ContentError(f'{self.file}: highlighting gave {len(rows)} rows for {self.nlines} lines')
        return rows


@dataclass
class Ref:
    """Where one cross-comment lands in one column: line ranges, or 'built in'."""

    ranges: list[tuple[int, int]] = field(default_factory=list)
    hint: str = ''
    builtin: str = ''

    @property
    def label(self) -> str:
        return label(self.ranges)


@dataclass
class Cross:
    n: int
    idea: str
    say: str
    refs: dict[str, Ref]

    @property
    def ranges(self) -> dict[str, list]:
        return {cid: [list(r) for r in ref.ranges] for cid, ref in self.refs.items()}


@dataclass
class Note:
    note: str = ''
    run: str = ''  # a shell command
    open: str = ''  # a file to open in the browser


@dataclass
class Shots:
    same: bool
    diff: dict[str, int]
    files: dict[str, Path]  # column id -> png in content/
    w: int
    h: int
    scale: int
    date: str
    compared_to: str
    libraries: dict[str, dict]
    stale: list[str] = field(default_factory=list)  # columns whose file changed after the screenshot
    clicks: list = field(default_factory=list)  # [x, y] clicks made before the screenshot
    urls: dict[str, str] = field(default_factory=dict)  # column id -> path under docs/assets/, set by build


@dataclass
class MdBlock:
    """A Markdown file of a step (content/<section>/<step>/<name>.md), shown in the extra block."""

    name: str
    text: str


@dataclass
class Planned:
    num: str
    name: str
    ready = False
    prev: object = None
    next: object = None


@dataclass
class Step:
    num: str
    id: str
    slug: str
    name: str
    dir: Path
    template: str
    intro: list[str]
    picture: str
    picture_caption: str
    try_it: str
    notes: dict[str, Note]
    code: dict[str, Code]
    cross: list[Cross]
    shots: Shots | None
    blocks: list[MdBlock] = field(default_factory=list)
    section: Section = None
    ready = True
    prev: object = None
    next: object = None

    def note(self, cid: str) -> Note:
        return self.notes.get(cid, Note())

    @property
    def raw(self) -> dict[str, str]:
        return {cid: c.text for cid, c in self.code.items()}


@dataclass
class Section:
    n: int
    id: str
    name: str
    about: str
    steps: list[Step]
    planned: list[Planned]

    @property
    def total(self) -> int:
        return len(self.steps) + len(self.planned)


# ------------------------------------------------------------------ loading
def load_site(lang: str | None = None) -> Site:
    raw = parse_toml(CONTENT / 'site.toml')
    languages = raw.get('languages', ['en'])
    # Codes become folder names that the build deletes and rewrites (docs/<code>/), so be strict.
    bad = [c for c in languages if not isinstance(c, str) or not LANG_CODE.fullmatch(c) or c in ('steps', 'assets')]
    if not languages or bad or len(set(languages)) != len(languages):
        raise ContentError(
            f'content/site.toml: languages must be distinct codes like "en" or "pt-BR", got {languages!r}'
        )
    default = languages[0]
    lang = lang or default
    d = read_toml(CONTENT / 'site.toml', lang, default)
    cols = [Column(**{k: c[k] for k in ('id', 'name', 'what', 'lang', 'needs') if k in c}) for c in d['column']]
    return Site(
        lang=lang,
        default_lang=default,
        languages=languages,
        title=d['title'],
        subtitle=d['subtitle'],
        lead=d['lead'],
        how_to_read=d['how_to_read'],
        setup=d['setup'],
        setup_note=d['setup_note'],
        columns=cols,
        hero=d.get('hero', {}),
        libs=d.get('libs', {}),
    )


def section_dirs() -> list[Path]:
    return sorted(p for p in CONTENT.iterdir() if (p / 'section.toml').is_file())


def step_dirs(section_dir: Path | None = None) -> list[Path]:
    dirs = [section_dir] if section_dir else section_dirs()
    return [p for d in dirs for p in sorted(d.iterdir()) if (p / 'step.toml').is_file()]


def column_file(step_dir: Path, cid: str) -> Path | None:
    """The runnable file of one column: <id>.html / <id>.py, or <id>_<anything> (nicegui_app.py).
    Exact rule, so vue-old.html or vuex.html is never taken for vue.html."""
    found = [
        f
        for f in sorted(step_dir.iterdir())
        if f.is_file() and f.suffix in LEXERS and (f.stem == cid or f.stem.startswith(cid + '_'))
    ]
    return next((f for f in found if f.stem == cid), found[0] if found else None)


def load_sections(site: Site) -> list[Section]:
    sections = []
    for n, sdir in enumerate(section_dirs(), 1):
        d = read_toml(sdir / 'section.toml', site.lang, site.default_lang)
        sec = Section(n=n, id=f'sec-{n}', name=d['name'], about=d.get('about', ''), steps=[], planned=[])
        for k, tdir in enumerate(step_dirs(sdir), 1):
            st = load_step(tdir, f'{n}.{k}', site)
            st.section = sec
            sec.steps.append(st)
        sec.planned = [
            Planned(num=f'{n}.{len(sec.steps) + k}', name=name) for k, name in enumerate(d.get('planned', []), 1)
        ]
        sections.append(sec)
    flat = [s for sec in sections for s in sec.steps + sec.planned]
    for i, s in enumerate(flat):
        s.prev = flat[i - 1] if i else None
        s.next = flat[i + 1] if i + 1 < len(flat) else None
    return sections


def load_step(tdir: Path, num: str, site: Site) -> Step:
    d = read_toml(tdir / 'step.toml', site.lang, site.default_lang)
    where = rel(tdir)
    for key in ('name', 'intro'):
        if key not in d:
            raise ContentError(f'{where}/step.toml: missing "{key}"')

    code = {}
    for cid in site.column_ids:
        f = column_file(tdir, cid)
        if f:
            code[cid] = Code(file=f.name, ext=f.suffix, text=f.read_text(encoding='utf-8'))

    cross = []
    for n, x in enumerate(d.get('cross', []), 1):
        refs = {}
        for cid in site.column_ids:
            spec = x.get(cid)
            if spec is None:
                continue
            here = f'{where}/step.toml cross-comment {n} ({cid})'
            if not isinstance(spec, dict) or ('at' in spec) == ('builtin' in spec):
                raise ContentError(f'{here}: write {{ at = [["start"]], hint = "..." }} or {{ builtin = "..." }}')
            if 'builtin' in spec:
                if not isinstance(spec['builtin'], str):
                    raise ContentError(f'{here}: builtin must be text')
                refs[cid] = Ref(builtin=spec['builtin'])
                continue
            at = spec['at']
            if (
                not isinstance(at, list)
                or not at
                or not all(isinstance(m, list) and m and all(isinstance(x_, str) and x_ for x_ in m) for m in at)
            ):
                raise ContentError(
                    f'{here}: at must be a list of ranges like [["start"], ["start", "end"]], got {at!r}'
                )
            if cid not in code:
                raise ContentError(f'{where}: cross-comment {n} points at {cid}, but there is no {cid} file')
            c = code[cid]
            ranges = [find(c.lines, m, f'{where}/{c.file} cross-comment {n}') for m in at]
            refs[cid] = Ref(ranges=ranges, hint=spec.get('hint', ''))
            for a, b in ranges:
                for ln in range(a, b + 1):
                    if n not in c.marks.setdefault(ln, []):
                        c.marks[ln].append(n)
        if 'idea' not in x:
            raise ContentError(f'{where}/step.toml cross-comment {n}: missing "idea"')
        cross.append(Cross(n=n, idea=x['idea'], say=x.get('say', ''), refs=refs))

    pic = tdir / 'picture.svg'
    s, k = num.split('.')
    blocks = []
    for f in sorted(tdir.glob('*.md')):
        if '.' in f.stem:  # why.fa.md is a translation of why.md, not a block of its own
            continue
        tr = f.with_name(f'{f.stem}.{site.lang}.md')
        src = tr if site.lang != site.default_lang and tr.is_file() else f
        blocks.append(MdBlock(name=f.stem, text=src.read_text(encoding='utf-8')))
    return Step(
        num=num,
        id=f's{s}-{k}',
        slug=f'{s}-{k}',
        name=d['name'],
        dir=tdir,
        template=f'{tdir.relative_to(CONTENT).as_posix()}/step.html' if (tdir / 'step.html').is_file() else 'step.html',
        intro=d['intro'],
        picture=re.sub(r'<\?xml.*?\?>', '', pic.read_text(encoding='utf-8')).strip() if pic.is_file() else '',
        picture_caption=d.get('picture_caption', ''),
        try_it=d.get('try_it', ''),
        notes={cid: Note(**v) for cid, v in d.get('columns', {}).items()},
        code=code,
        cross=cross,
        shots=load_shots(tdir, site.column_ids),
        blocks=blocks,
    )


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_shots(tdir: Path, col_ids: list[str]) -> Shots | None:
    res = tdir / 'shots' / 'result.json'
    if not res.is_file():
        return None
    r = json.loads(res.read_text(encoding='utf-8'))
    files = {cid: tdir / 'shots' / f'{cid}.png' for cid in col_ids if (tdir / 'shots' / f'{cid}.png').is_file()}
    sources, stale = r.get('sources', {}), []
    for cid in col_ids:
        f = column_file(tdir, cid)
        if cid in sources and (f is None or file_hash(f) != sources[cid]):
            stale.append(cid)  # changed or removed since the screenshot
        elif cid not in sources and f is not None:
            stale.append(cid)  # added after the screenshots were taken
    if 'sources' not in r:  # made before shoot.py recorded hashes: cannot tell, so say so
        stale = list(files)
    diff = r['diff_pixels']
    return Shots(
        same=all(v == 0 for v in diff.values()),
        diff=diff,
        files=files,
        w=r['view']['width'],
        h=r['view']['height'],
        scale=r['scale'],
        date=r['tested'],
        compared_to=r['compared_to'],
        libraries=r['libraries'],
        stale=stale,
        clicks=r.get('clicks', []),
    )


def fill_tested(site: Site, sections: list[Section]) -> None:
    """Column cards show the library versions the screenshots were taken with."""
    found = {}
    for st in (s for sec in sections for s in sec.steps if s.shots):
        for cid, libs in st.shots.libraries.items():
            found.setdefault(cid, libs)
    for c in site.columns:
        v = found.get(c.id, {})
        parts = [f'NiceGUI {v["nicegui"]}'] if 'nicegui' in v else []
        parts += [f'Quasar {v["quasar"]}'] if 'quasar' in v else []
        parts += [f'Vue {v["vue"]}'] if 'vue' in v else []
        c.tested = ' · '.join(parts)
