# Continuous Integration

Geomora uses two GitHub Actions workflows.

## Required pull-request workflow

`.github/workflows/ci.yml` runs without SketchUp, model downloads, or cloud API
calls. Its required checks are:

- `python-tests` — full pytest suite on Python 3.11 and 3.12;
- `ruby-tests` — the SketchUp-free reconstruction contract suite on Ruby 3.2 and 3.3;
- `static-contracts` — Python compile, Ruby syntax, and Workspace JavaScript syntax;
- `reconstruction-contracts` — Draft 7 IR schema, GT audit, deterministic five-photo reconstruction, artifact validation, and an attached truthful RC-G0 report;
- `package-smoke` — RBZ build and required-file inspection.

`ruby-full-suite-debt` reports existing failures in legacy presentation/interior
tests and is intentionally non-blocking. Tests move into `tests/run_ci_tests.rb`
as their contracts are repaired. Do not hide a new reconstruction regression in
the debt job.

RC-G0 is currently not passed by the deterministic baseline. Required CI checks
that the pipeline and artifacts remain complete; `--report-only` changes only
the process exit code and never changes the report's `passed` value.

## Benchmark workflow

`.github/workflows/reconstruction-benchmark.yml` runs weekly or manually. It
uploads deterministic reconstruction artifacts plus RC-G0 and RC-G1 reports.
It uses no live VLM evidence and does not tune thresholds.

## Branch protection

After the first workflow run, repository administrators must require these
checks on `master` (or `main`):

1. `python-tests (3.11)` and `python-tests (3.12)`
2. `ruby-tests (3.2)` and `ruby-tests (3.3)`
3. `static-contracts`
4. `reconstruction-contracts`
5. `package-smoke`

Also require a pull request, an up-to-date branch, and at least one review.
Creating a workflow file alone does not protect a branch.
