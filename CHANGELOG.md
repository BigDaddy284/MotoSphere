# Changelog

All notable changes to this project are documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Repository baseline: `.gitignore`, `.gitattributes`, `.editorconfig`,
  README, document stubs (DATA_SOURCES.md, DATABASE.md, TESTING.md,
  CHANGELOG.md) and the repository check suite in `tests/repo` (FND-001).
- Backend Python project skeleton (`backend/`): uv project with a committed
  lock file, `motosphere` package and pytest suite (FND-002).
- Backend linting and formatting with ruff, including security rules (FND-003).
