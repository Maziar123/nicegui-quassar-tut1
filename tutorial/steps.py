"""Find steps by number. Used by the `run` shortcut and the justfile.

python tutorial/steps.py                 list every step: number, name, folder, column files
python tutorial/steps.py 1.1             print the step's folder
python tutorial/steps.py 1.1 nicegui     print the path of one column file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model  # noqa: E402


def main(argv: list[str]) -> int:
    site = model.load_site()
    steps = {st.num: st for sec in model.load_sections(site) for st in sec.steps}
    if not argv:
        for st in steps.values():
            cols = ', '.join(f'{cid}={c.file}' for cid, c in st.code.items())
            print(f'{st.num:5} {st.name:30} {model.rel(st.dir)}  ({cols})')
        return 0
    st = steps.get(argv[0])
    if st is None:
        print(f'no step {argv[0]!r}. Steps: {", ".join(steps) or "none"}', file=sys.stderr)
        return 1
    if len(argv) == 1:
        print(st.dir)
        return 0
    f = model.column_file(st.dir, argv[1])
    if f is None:
        print(f'step {st.num} has no {argv[1]!r} column. Columns: {", ".join(st.code)}', file=sys.stderr)
        return 1
    print(f)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
