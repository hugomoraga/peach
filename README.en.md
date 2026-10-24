<p align="center">
  <img src="resources/videodrome-logo.png" alt="Videodrome" width="96">
</p>

<h1 align="center">Videodrome</h1>

<p align="center">A personal film library in Spanish: local disk, cloud drives and the creators you follow, all in one place.</p>

---

## What this is

**Videodrome** is a personal fork of [Peach](https://github.com/peach-mitao/peach), the
original application by [peach-mitao](https://github.com/peach-mitao). All of the
application's work — the ledger, the scraping, the player, the library, the system
tray — is Peach's. What this fork changes is the language: **the interface is in
Spanish** and the code is called `videodrome`.

Peach is free software under the **AGPL-3.0-or-later**. This fork is too.

### Credits and licence

- **Peach**, by [peach-mitao](https://github.com/peach-mitao) and everyone who has
  contributed to it. Copyright (C) its authors. Licensed under
  [AGPL-3.0-or-later](LICENSE).
- **Videodrome**, this fork. It changes the name, the language of the interface and the
  packaging; the engine is Peach's.
- The Spanish translation and the pipeline that applies it are this fork's work
  (`tools/i18n/`).

The source of both is public: [peach-mitao/peach](https://github.com/peach-mitao/peach) and
[hugomoraga/peach](https://github.com/hugomoraga/peach).

AGPL-3.0 requires that whoever receives the program can obtain its source, and that
the interface shows a legal notice. That is why the `.app` ships the licence inside it
and this README states the origin.

## How to use it

It is a desktop application for macOS (there is a Windows build as well). The system
tray is the hub: from there you open the interface in the browser, configure the drives
and start the jobs.

```bash
# build the Spanish interface, package and install
tools/build_and_install.sh

# build only
tools/build_and_install.sh --build-only
```

When it finishes the app is installed at `/Applications/Videodrome.app` and the data
lives in `~/Library/Application Support/Videodrome/peach-data`.

## How it is built

The real difference from Peach is that **the code is not translated here**.

- The source tree (`src/`, `frontend/src/`, `web/`) stays in Chinese, exactly as it
  comes from upstream.
- The translation lives in `tools/i18n/glossary.zh-es.json`: 5,400 messages with their
  Spanish translation. `npm --prefix frontend run build` applies it to an isolated copy
  (`.i18n/es/`) and publishes the result into `web/dist/`.
- The backend translates while serving, with `PEACH_LOCALE=es`, and only over interface
  fields: content tags, genres and titles are left alone.

That way, taking upstream's changes is a `git fetch upstream && git rebase upstream/master`
with no conflicts: the only thing to review is the new strings.

### Quality gates

The build refuses to go on if something is wrong:

| Gate | What it guards |
| --- | --- |
| `tools/i18n/coverage.py` | A new interface string cannot go in untranslated without review |
| `tools/i18n/validate.py` | Placeholders (`${n}`, `{count}`) are not broken |
| `tools/i18n/check_data.py` | Stored values (tags, genres, length bands) arrive untouched |
| `tools/i18n/verify_es.mjs` | In a real browser the page is Spanish, with not one Chinese character |
| `frontend/test/**` | 1,651 behaviour tests, none of them depending on the language |

## Requirements

- macOS with Python 3.14 or newer (`uv`), Node 24 and the dependencies from `uv sync --locked --all-extras`
- Windows: `scripts/build_windows.ps1`

## Layout

```
src/videodrome/      the engine (Peach's code, renamed)
frontend/src/        the interface (Peach's code, in Chinese)
web/                 the static pages and the published bundle
tools/i18n/          the translation catalogue and the pipeline
docs/                upstream's documentation
openspec/            this fork's work plans
```

## Documentation

- [`tools/i18n/README.md`](tools/i18n/README.md) — the translation pipeline, how to
  update the glossary and what is not translated.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — running the app.
- [`docs/TESTING.md`](docs/TESTING.md) — how it is tested.
