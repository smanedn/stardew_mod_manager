# Contributing to Stardew Valley Mod Manager

Thank you for considering contributing to **Stardew Valley Mod Manager (SVMM)**!

## Development Setup

1. Clone the repository and create a virtual environment:
   ```bash
   git clone https://github.com/smanedn/stardew_mod_manager.git
   cd stardew_mod_manager
   python -m venv .venv
   ```
2. Activate the virtual environment and install development dependencies:
   - **Windows (PowerShell):**
     ```powershell
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements-dev.txt
     ```
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     pip install -r requirements-dev.txt
     ```

## Code Style & Checks

Before opening a pull request, make sure both linting and tests pass:

```bash
ruff check .
pytest -v
```

- Keep `src/core/` (business logic) decoupled from `src/ui/` (`customtkinter` widgets).
- Add or update unit tests in `tests/` for any changes to `src/core/`.
- Preserve existing type hints and follow the Ruff configuration in `pyproject.toml`.

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New features
- `fix:` — Bug fixes
- `docs:` — Documentation changes
- `ci:` — CI/CD workflow changes
- `test:` — Adding or updating tests
- `chore:` — Maintenance and tooling updates

## Reporting Issues & Suggesting Features

Please use the GitHub issue templates in `.github/ISSUE_TEMPLATE/` when reporting bugs or requesting features, and include your OS, Python version, and SMAPI version if relevant.
