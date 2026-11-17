# Changelog

All notable changes to this project are documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Hosting model: GitHub Pages only, with no server. The architecture and task
  list were re-planned around a scheduled data pipeline and published data
  files (owner decision, 2026-11-17).
- Visual identity: the owner's Graphite theme and Sky Classic icon style are
  the design references (`docs/design/`).

### Added

- Repository baseline: `.gitignore`, `.gitattributes`, `.editorconfig`,
  README, document stubs (DATA_SOURCES.md, DATABASE.md, TESTING.md,
  CHANGELOG.md) and the repository check suite in `tests/repo` (FND-001).
- Backend Python project skeleton (`backend/`): uv project with a committed
  lock file, `motosphere` package and pytest suite (FND-002).
- Backend linting and formatting with ruff, including security rules (FND-003).
- Backend static type checking with mypy in strict mode (FND-004).
- Backend settings module with environment variable and `.env` configuration
  (FND-005).
- Backend logging configuration: single line format with UTC timestamps and
  escaped line breaks (FND-006).
- API application factory and health endpoint `GET /api/health` (FND-007).
- `python -m motosphere` starts the API server (FND-008).
- Frontend project skeleton (`frontend/`): Vite, React and TypeScript in strict
  mode (FND-009).
- Frontend unit testing with Vitest and Testing Library (FND-010).
- Frontend linting with oxlint (React, accessibility and security rules) and
  formatting with Prettier (FND-011).
- Browser tests with Playwright against the built application, with an
  automatic page health check (FND-012).
- Dark theme design tokens and base styles, with automatic contrast checks
  (FND-013).
- The owner's Graphite theme: charcoal surfaces, sky-blue accent and Segoe UI
  font stack (FND-023).
- Application shell layout: top bar, sections panel, globe stage and details
  panel (FND-014).
- Section navigation: the nine sections listed in the sections panel,
  selectable by mouse or keyboard (FND-025).
- Collapsible side panels: buttons in the top bar close and open the sections
  and details panels, remembered for the session (FND-015).
- Current date in the top bar, in the language and time zone of the user's
  browser, changing at midnight (FND-026).
- Pipeline command line: `python -m motosphere <command>`, with a `version`
  command (FND-020).
- `export` command: writes the published data manifest, `manifest.json`,
  atomically and deterministically (FND-021).
- Application icon: the owner's approved design as the page icon, with a
  small version for browser tabs, an ICO fallback and a touch icon (FND-024).
- Frontend manifest reader: fetches and checks the published data manifest,
  with a plain result for every failure (FND-016).
- `npm run data`: exports the published data for local development; the
  browser tests run against freshly exported data (FND-027).
- Data status in the top bar: when the published data was updated, or that it
  is unavailable (FND-028).
- Browser tests can name the page problems they expect; the data status is
  tested with a missing manifest and a failed request (FND-029).
- `python scripts/check.py`: one command that runs every gate in order and
  reports which passed (FND-017).

### Removed

- The API server and its health endpoint, the `MOTOSPHERE_API_HOST` and
  `MOTOSPHERE_API_PORT` settings and the `fastapi`, `uvicorn` and `httpx2`
  dependencies, following the GitHub Pages hosting decision (FND-020).
