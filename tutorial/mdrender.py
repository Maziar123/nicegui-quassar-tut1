"""Markdown for content: CommonMark + tables, with Pygments-highlighted code fences
and "code + preview" blocks.

Fence info string:  ```<lang> [preview] [title="file.css"] [hl=2,4-5] [height=220]
  ```css title="vue.html" hl=2      highlighted code, a title, line 2 marked
  ```mermaid                        Mermaid: code and the drawn diagram side by side
  ```html preview height=200        HTML: code and a live, sandboxed preview (no scripts)

The HTML of a fence is not built here: it comes from the `fence` macro in
templates/macros.html, passed in as `fence_html`, so all markup lives in templates.
"""

from __future__ import annotations

import shlex
from collections.abc import Callable

from markdown_it import MarkdownIt
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import RegexLexer, words
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.token import Comment, Keyword, Name, Operator, Punctuation, String, Text, Whitespace
from pygments.util import ClassNotFound


class MermaidLexer(RegexLexer):
    """Small Mermaid lexer (Pygments has none). Covers keywords, directions, arrows, labels, comments."""

    name = 'Mermaid'
    aliases = ['mermaid', 'mmd']
    tokens = {
        'root': [
            (r'%%.*?$', Comment.Single),
            (
                words(
                    (
                        'flowchart',
                        'graph',
                        'sequenceDiagram',
                        'classDiagram',
                        'stateDiagram-v2',
                        'stateDiagram',
                        'erDiagram',
                        'gantt',
                        'pie',
                        'journey',
                        'mindmap',
                        'timeline',
                        'gitGraph',
                        'quadrantChart',
                        'block-beta',
                        'architecture-beta',
                        'subgraph',
                        'end',
                        'direction',
                        'participant',
                        'actor',
                        'note',
                        'loop',
                        'alt',
                        'else',
                        'opt',
                        'par',
                        'and',
                        'rect',
                        'title',
                        'section',
                        'style',
                        'classDef',
                        'class',
                        'click',
                        'linkStyle',
                        'as',
                        'over',
                        'left of',
                        'right of',
                    ),
                    prefix=r'(?<![\w-])',
                    suffix=r'(?![\w-])',
                ),
                Keyword,
            ),
            (r'(?<![\w-])(TB|TD|BT|RL|LR)(?![\w-])', Keyword.Constant),
            (r'"[^"\n]*"', String.Double),
            (r'\[[^\]\n]*\]|\([^)\n]*\)|\{[^}\n]*\}', String),
            (r'\|[^|\n]*\|', String),  # edge label: -->|yes|
            (r'<-->|<==>|-\.->|-\.-|-->>|->>|-->|---|==>|===|->|--[xo]|~~~|-x|-\)', Operator),
            (r':::?', Operator),
            (r'[;:,&]', Punctuation),
            (r'\s+', Whitespace),
            (r'[\w.#]+', Name),
            (r'.', Text),
        ]
    }


LABEL = {
    'html': 'HTML',
    'css': 'CSS',
    'js': 'JavaScript',
    'javascript': 'JavaScript',
    'python': 'Python',
    'py': 'Python',
    'toml': 'TOML',
    'bash': 'Bash',
    'sh': 'Shell',
    'json': 'JSON',
    'mermaid': 'Mermaid',
}


def lexer_for(lang: str):
    if lang in MermaidLexer.aliases:
        return MermaidLexer(stripnl=False)
    try:
        return get_lexer_by_name(lang, stripnl=False) if lang else TextLexer(stripnl=False)
    except ClassNotFound:
        return TextLexer(stripnl=False)


def highlight_rows(code: str, lang: str) -> list[str]:
    """Highlighted HTML, one string per line (stripnl=False keeps leading blank lines)."""
    html = highlight(code, lexer_for(lang), HtmlFormatter(nowrap=True))
    return [r or ' ' for r in html.rstrip('\n').split('\n')]


def parse_lines(spec: str) -> set[int]:
    """'2,4-5' -> {2, 4, 5}"""
    out = set()
    for part in filter(None, spec.split(',')):
        a, _, b = part.partition('-')
        out.update(range(int(a), int(b or a) + 1))
    return out


def parse_info(info: str) -> tuple[str, set[str], dict[str, str]]:
    """'css title="a b.css" hl=2' -> ('css', set(), {'title': 'a b.css', 'hl': '2'})"""
    parts = shlex.split(info) if info.strip() else []
    lang = parts[0].lower() if parts else ''
    flags, attrs = set(), {}
    for p in parts[1:]:
        k, eq, v = p.partition('=')
        (attrs.__setitem__(k, v) if eq else flags.add(k))
    return lang, flags, attrs


class Markdown:
    """One renderer per language. `fence_html(**kw)` renders a fence (the template macro)."""

    def __init__(self, fence_html: Callable[..., str], heading_shift: int = 3):
        self.fence_html = fence_html
        self.shift = heading_shift
        self.md = MarkdownIt('commonmark', {'html': True}).enable(['table', 'strikethrough'])
        self.md.add_render_rule('fence', self._fence)

    def _fence(self, tokens, idx, options, env):  # a bound method: markdown-it passes no renderer
        tok = tokens[idx]
        try:
            lang, flags, attrs = parse_info(tok.info)
            marked = parse_lines(attrs.get('hl', ''))
            height = int(attrs.get('height', 220))
        except ValueError as e:
            raise ValueError(f'bad code fence info {tok.info!r}: {e}') from None
        code = tok.content
        kind = (
            'mermaid' if lang in MermaidLexer.aliases else 'html' if lang == 'html' and 'preview' in flags else 'code'
        )
        return str(
            self.fence_html(
                kind=kind,
                lang=lang,
                label=LABEL.get(lang, lang.upper() or 'Text'),
                rows=highlight_rows(code, lang),
                raw=code,
                marked=marked,
                title=attrs.get('title', ''),
                height=height,
            )
        )

    def block(self, text: str) -> Markup:
        """A Markdown block. Headings move down by `heading_shift` (# -> h4 inside a step)."""
        tokens = self.md.parse(text)
        for t in tokens:
            if t.type in ('heading_open', 'heading_close'):
                t.tag = f'h{min(6, int(t.tag[1]) + self.shift)}'
        return Markup(self.md.renderer.render(tokens, self.md.options, {}))

    def inline(self, text: str) -> Markup:
        """One line of Markdown (code spans, emphasis, links, inline HTML like <kbd>)."""
        return Markup(self.md.renderInline(text))
