# Contributing to Charger Project

Thank you for your interest in contributing to the Charger Project! This document provides guidelines and instructions for contributing.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Branch Strategy](#branch-strategy)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)

---

## Code of Conduct

- Be respectful and professional
- Focus on constructive feedback
- Help others learn and grow
- Follow project guidelines

---

## Getting Started

### Prerequisites

- Python 3.13+
- Git
- Raspberry Pi (for hardware testing)
- ESP32 (for hardware testing)

### Setup

1. **Clone the repository:**
   ```bash
   git clone git@github.com:CaiserSz/orge1.git
   cd charger
   ```

2. **Set up virtual environment:**
   ```bash
   python3 -m venv env
   source env/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   # Create .env locally (DO NOT commit secrets)
   # Example (placeholders):
   #   SECRET_API_KEY=******            # required for API auth in development
   #   TEST_API_USER_ID=TEST001         # optional, used by tests/dev flows
   #
   # Recommended:
   #   - Prefer exporting environment variables in your shell/systemd for production
   #   - Keep .env local only (it is gitignored)
   ```

---

## Development Workflow

### 1. Create a Branch

Always create a new branch for your work:

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bug fix branch
git checkout -b fix/your-bug-fix-name

# Documentation branch
git checkout -b docs/your-doc-update
```

### 2. Make Changes

- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation as needed

### 3. Test Your Changes

- Run existing tests: `pytest`
- Test manually if needed
- Ensure no regressions

### 4. Commit Your Changes

Follow the [Commit Message Guidelines](#commit-message-guidelines).

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```
type(scope): subject

[optional body]

[optional footer]
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Test changes
- **chore**: Maintenance tasks
- **security**: Security fixes
- **perf**: Performance improvements

### Scope

Optional scope indicating the area of the codebase:
- `api`: API changes
- `esp32`: ESP32 bridge changes
- `meter`: Meter module changes
- `tests`: Test changes
- `docs`: Documentation changes

### Examples

```bash
feat(api): Add authentication endpoint
fix(esp32): Fix state transition bug
docs: Update README with new features
test(api): Add integration tests for charge endpoints
chore: Update dependencies
security(api): Fix API key exposure vulnerability
```

### Rules

- First line should be ≤ 72 characters
- Use imperative mood ("Add" not "Added")
- No period at the end
- Reference issues/PRs in footer if applicable

---

## Branch Strategy

### Main Branches

- **main**: Production-ready code
  - Always deployable
  - Protected branch (requires PR)
  - Tagged with version numbers

### Supporting Branches

- **feature/***: New features
  - Branch from: `main`
  - Merge to: `main`
  - Naming: `feature/description`

- **fix/***: Bug fixes
  - Branch from: `main`
  - Merge to: `main`
  - Naming: `fix/description`

- **docs/***: Documentation updates
  - Branch from: `main`
  - Merge to: `main`
  - Naming: `docs/description`

- **hotfix/***: Critical production fixes
  - Branch from: `main`
  - Merge to: `main`
  - Naming: `hotfix/description`

---

## Pull Request Process

### Before Submitting

1. ✅ Code follows project style
2. ✅ Tests pass (`pytest`)
3. ✅ Documentation updated
4. ✅ Commit messages follow guidelines
5. ✅ No merge conflicts

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (please describe)

## Testing
- [ ] Tests pass locally
- [ ] Manual testing completed
- [ ] No breaking changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages follow guidelines
- [ ] No merge conflicts
```

### Review Process

1. PR is reviewed by maintainers
2. Address review comments
3. Once approved, PR is merged
4. Delete feature branch after merge

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api_endpoints.py

# Run with coverage
pytest --cov=api --cov=esp32
```

### Writing Tests

- Write tests for new features
- Maintain ≥70% code coverage
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

---

## Documentation

### Code Documentation

- Use docstrings for functions/classes
- Follow Google/NumPy style
- Include type hints

### Documentation Files

- Update `project_info_20251208_145614.md` for major changes
- Update `README.md` for user-facing changes
- Update `CHANGELOG.md` for version releases
- Update `docs/workspace_index.md` for new files

---

## Git Hooks

The project includes git hooks for quality assurance:

### Pre-commit Hook

- Python syntax check
- Trailing whitespace check
- Large file check (>10MB)

### Commit-msg Hook

- Conventional commits format validation
- Commit message length check

Hooks are automatically installed in `.git/hooks/`.

---

## Questions?

If you have questions or need help:

1. Check existing documentation
2. Review closed issues/PRs
3. Create a new issue with your question

---

**Thank you for contributing!** 🎉

