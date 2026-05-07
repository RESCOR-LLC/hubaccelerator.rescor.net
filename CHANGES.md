# Changelog

All notable changes to HubAccelerator are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/) loosely; the project does not
yet emit semantic-version releases, so changes are dated rather than versioned.

## 2026-05-07 — Open-source publication readiness

Repository prepared for public release on GitHub. No functional changes to the
exporter or updater; everything in this entry is licensing, documentation,
testing, and CI scaffolding so the public release lands in a defensible state.

### Added

- `LICENSE` at repo root containing the canonical GNU AGPL-3.0 text.
- `SECURITY.md` describing the vulnerability-disclosure process and threat-model
  expectations.
- `CONTRIBUTING.md` covering issue reporting, PR shape, development setup,
  style, and the boundaries of what changes are likely to be accepted.
- `tests/` directory with pytest + moto-based test suite:
  - `test_smoke.py` — module imports and entry-point shape.
  - `test_unit.py` — pure-function and object behaviour
    (`getFilters`, `InputDiscriminator`, `env`, `error_code`).
  - `test_integration.py` — moto-mocked AWS integration tests, including
    multi-CSP fixtures (Azure-via-Wiz, GCP-via-Prisma) to verify the
    Finding/CSV pipeline handles non-AWS-native resources without choking.
- `.github/workflows/ci.yml` — GitHub Actions CI running ruff + pytest across
  Python 3.9 / 3.10 / 3.11 / 3.12 plus a `cdk synth` sanity check.
- `.github/CODEOWNERS` — single-owner stub (extend as the project grows).
- `docs/diagrams/architecture.d2` — overall system architecture diagram
  (D2 source + rendered SVG), complementing the three existing flow-specific
  diagrams (scheduled-export, cli-export, bulk-update).
- `[project.optional-dependencies]` `dev` extra in `pyproject.toml`
  (pytest, pytest-cov, moto, ruff) — installable via `pip install -e ".[dev]"`.
- `[tool.pytest.ini_options]` and `[tool.ruff]` configuration in
  `pyproject.toml` for consistent local-and-CI tooling.

### Changed

- README license section updated from "All Rights Reserved" to AGPL-3.0
  (resolving an internal contradiction with `pyproject.toml` and
  `cdk/package.json`, both of which already declared AGPL-3.0).
- Author byline in README updated from generic `RESCOR LLC` link to direct
  LinkedIn profile.

### Removed

- `archive/` directory (historical patches and a one-off `prepare.py`
  superseded by the CDK-driven Lambda packaging). Recoverable from git
  history if needed.
- `docs/legacy/` directory — three Office documents (pptx / docx / pdf)
  using the tool's old name ("CSV Manager for Security Hub") and carrying
  document-property metadata from a prior author context. Content was
  superseded by the current README; removed rather than retained as a
  cleaner public-release surface.

## Earlier history

See git log for changes prior to public-release preparation.
