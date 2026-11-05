# Project commands. `./run` (or `uv run just`) lists them; `./run <name>` runs one.
# Everything runs inside the uv environment, with the versions pinned in uv.lock.
# Optional .env file: XREF_CHROMIUM=/path/to/chromium, XREF_NPM_DIR=/path/to/npm/packages

set dotenv-load := true
set shell := ["bash", "-euo", "pipefail", "-c"]

# list the commands
default:
    @just --list --unsorted

# install everything: Python packages, git hooks, Chromium for screenshots and browser tests
setup:
    uv sync
    uv run prek install
    uv run playwright install chromium

# screenshot every column and compare the pixels (after changing a column file)
shoot:
    uv run python tutorial/shoot.py

# build the site into docs/
build:
    uv run python tutorial/build.py

# build the site, then serve it on http://localhost:8000 and open the browser (Ctrl+C stops)
serve port="8000": build
    @echo "Serving docs/ on http://localhost:{{ port }}  (Ctrl+C stops)"
    (sleep 1; uv run python -m webbrowser -t "http://localhost:{{ port }}/" > /dev/null 2>&1 || true) &
    uv run python -m http.server {{ port }} --bind 127.0.0.1 --directory docs

# list the steps with their numbers, folders and column files
steps:
    @uv run python tutorial/steps.py

# run the NiceGUI column of a step, for example: ./run nicegui 1.1
nicegui num="1.1":
    @f="$(uv run python tutorial/steps.py {{ quote(num) }} nicegui)" && uv run python "$f"

# open an HTML column of a step in the browser, for example: ./run open 1.1 vue
open num="1.1" col="quasar":
    @f="$(uv run python tutorial/steps.py {{ quote(num) }} {{ quote(col) }})" && echo "Opening $f" \
      && uv run python -m webbrowser -t "file://$f"

# fast tests (no browser)
test *args:
    uv run pytest -m "not browser" {{ args }}

# browser tests in headless Chromium
test-browser *args:
    uv run pytest -m browser {{ args }}

# lint and format check
lint:
    uv run ruff check
    uv run ruff format --check

# format and fix what ruff can fix
fmt:
    uv run ruff format
    uv run ruff check --fix

# write requirements.txt from uv.lock (for students who use plain pip)
reqs:
    uv export --format requirements.txt --no-dev --no-hashes --frozen --quiet -o requirements.txt

# fail if requirements.txt does not match uv.lock
check-reqs:
    diff <(uv export --format requirements.txt --no-dev --no-hashes --frozen --quiet | grep -v '^#') \
         <(grep -v '^#' requirements.txt) > /dev/null \
      || { echo "requirements.txt is out of date: run just reqs"; exit 1; }

# fail if docs/ is out of date
check-docs:
    uv run python tutorial/build.py --check

# everything CI runs
ci: lint check-reqs test test-browser check-docs

# update all pinned packages, then rebuild the lock and requirements.txt
upgrade:
    uv lock --upgrade
    just reqs
