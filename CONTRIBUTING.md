# Contributing to Geomora

Thank you for your interest in contributing to Geomora.

## Getting Started

1. Fork the repository and clone your fork locally.
2. Follow the [Developer Setup](README.md#developer-setup) in the README.
3. Create a branch for your change:

   ```bash
   git checkout -b your-topic-branch
   ```

## Development Workflow

- **Ruby plugin tests** (no SketchUp required):

  ```bash
  ruby tests/run_tests.rb
  ```

- **Python backend tests**:

  ```bash
  cd backend
  python -m pytest
  ```

- For SketchUp integration changes, verify manually in SketchUp after installing via RBZ or symlink.

## Pull Requests

1. Keep changes focused — one logical change per pull request when possible.
2. Update documentation if behavior, setup steps, or public APIs change.
3. Ensure relevant tests pass before opening a PR.
4. Describe what changed, why, and how you tested it.

## Code Style

- Match the style of surrounding code in each file.
- Prefer small, readable changes over large refactors unless discussed first.
- Ruby: follow existing module layout under `plugin/geomora/`.
- Python: follow existing patterns under `backend/`.

## Reporting Issues

When filing an issue, please include:

- SketchUp version (for plugin issues)
- Operating system
- Steps to reproduce
- Expected vs. actual behavior
- Relevant logs or screenshots when available

## License

By contributing to Geomora, you agree that your contributions will be licensed under the [MIT License](LICENSE).
