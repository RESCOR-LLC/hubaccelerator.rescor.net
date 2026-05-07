# Contributing to HubAccelerator

Thank you for your interest in HubAccelerator. This is a small, single-author project and contributions are welcome — bug reports, feature requests, documentation improvements, and pull requests all help.

## Reporting issues

For non-security issues, file a [GitHub issue](https://github.com/RESCOR-LLC/hubaccelerator.rescor.net/issues). A good issue includes:

- What you were trying to do
- What you expected to happen
- What actually happened (full error message and stack trace if available)
- Your environment: operating system, Python version, AWS region, Security Hub configuration (single-account vs Org delegated admin, aggregator yes/no)
- The HubAccelerator version (commit hash or release tag)

For security issues, see [SECURITY.md](SECURITY.md). Please do not file public issues for vulnerabilities.

## Proposing changes

Pull requests welcome. The shape of a good PR:

1. Open an issue first if you're proposing a non-trivial change. We'll discuss the approach before you spend time coding.
2. Fork the repo, branch from `main`, and keep the branch focused on one logical change.
3. Match the existing code style (see "Style" below). Run the linter before submitting.
4. Add or update tests for the changed behaviour. PRs that change behaviour without test coverage will get bounced.
5. Update the README or other docs if you change user-visible behaviour.
6. Open the PR against `main`. The CI workflow will run lint and tests on it.

## Development setup

```bash
git clone https://github.com/RESCOR-LLC/hubaccelerator.rescor.net.git
cd hubaccelerator.rescor.net
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

The `[dev]` extra installs `pytest`, `moto` (AWS mocking), and `ruff` (linter) — see `pyproject.toml`.

To run the test suite:

```bash
pytest
```

To run the linter:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
```

## Style

- Python: follow PEP 8 with a line length of 100 characters. The project uses `ruff` for both linting and formatting; the configuration lives in `pyproject.toml`.
- Public APIs (anything callable from outside the module) need docstrings. Internal helpers can skip them but should have descriptive names.
- Logging: use the existing `logging` setup. New log messages should be at the right level (DEBUG for diagnostic detail, INFO for milestones, WARNING for recoverable problems, ERROR for genuine failures). Don't print to stdout.
- AWS calls: always use the existing `objects.py` abstractions where possible. New AWS-API call sites should handle pagination, transient errors, and the opt-in-region case (see `InvalidClientTokenId` handling).

## Testing AWS-touching code

HubAccelerator tests should not require live AWS credentials. Use [`moto`](https://docs.getmoto.org/) to mock the AWS APIs the code calls. Pattern:

```python
import boto3
from moto import mock_aws
import pytest
from hubaccelerator.exporter import export_findings

@mock_aws
def test_export_handles_empty_aggregator():
    securityhub = boto3.client("securityhub", region_name="us-east-1")
    securityhub.enable_security_hub()
    # ... exercise the function and assert
```

If you need to test against multiple regions or against multiple AWS partitions (commercial vs GovCloud), parametrize with `pytest.mark.parametrize`. The CI workflow runs the suite across the supported Python versions (3.9-3.12+).

## What kinds of changes are likely to be accepted

- Bug fixes with reproducer + test.
- Coverage of additional Security Hub providers/integrations (Azure, GCP — currently low-coverage; see `tests/integration/`).
- Performance improvements with measurements showing the win.
- Documentation improvements (clearer examples, fixed typos, better troubleshooting).
- New CLI flags or configuration options that fit cleanly with existing ones.

## What kinds of changes are unlikely to be accepted

- Whole-tool rewrites in a different language. Submit those as your own project.
- Changes that lock the tool to a single AWS partition (commercial only, or GovCloud only) — partition-agnostic is a design goal.
- Changes that remove the CSV-as-the-canonical-format model. The point of HubAccelerator is "the analyst edits a spreadsheet"; if you want a database-backed workflow, that is a different tool.
- Adding RESCOR-specific logic to the open-source tool. RESCOR-specific add-ons live elsewhere.

## License

By contributing, you agree your contributions will be licensed under the GNU Affero General Public License v3.0, the same license as the rest of the project. See [LICENSE](LICENSE).
