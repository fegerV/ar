# Contributing Guide

<cite>
**Referenced Files in This Document**   
- [CONTRIBUTING.md](file://CONTRIBUTING.md)
- [PR_DESCRIPTION.md](file://PR_DESCRIPTION.md)
- [COMMIT_MESSAGE.txt](file://COMMIT_MESSAGE.txt)
- [.pre-commit-config.yaml](file://vertex-ar/.pre-commit-config.yaml)
- [pyproject.toml](file://vertex-ar/pyproject.toml)
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)
- [pytest.ini](file://pytest.ini)
- [test_files/run_tests.sh](file://test_files/run_tests.sh)
- [docs/development/testing.md](file://docs/development/testing.md)
- [docs/development/setup.md](file://docs/development/setup.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Contribution Workflow](#contribution-workflow)
3. [Development Environment Setup](#development-environment-setup)
4. [Coding Standards](#coding-standards)
5. [Code Formatting and Pre-commit Hooks](#code-formatting-and-pre-commit-hooks)
6. [Commit Message Conventions](#commit-message-conventions)
7. [Pull Request Review Process](#pull-request-review-process)
8. [Testing Requirements](#testing-requirements)
9. [Documentation Updates](#documentation-updates)
10. [Issue Reporting and Feature Requests](#issue-reporting-and-feature-requests)
11. [Onboarding for New Contributors](#onboarding-for-new-contributors)
12. [Community Engagement](#community-engagement)

## Introduction

This guide provides comprehensive information for developers contributing to the AR backend project. It covers the complete contribution workflow, coding standards, testing requirements, and community practices. The project follows a structured development process with clear guidelines to ensure code quality, maintainability, and effective collaboration among contributors.

The AR backend is a FastAPI-based application that enables augmented reality experiences through portrait uploads, multimedia binding, and AR scene rendering. The codebase emphasizes clean architecture, comprehensive testing, and automated quality checks to maintain high standards across all contributions.

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L1-L103)
- [docs/development/setup.md](file://docs/development/setup.md#L1-L800)

## Contribution Workflow

The contribution workflow follows a structured Git branching model to ensure organized development and code quality. Contributors should follow these steps when making changes to the codebase.

### Fork-Branch-Pull Request Process

The project uses a Git Flow-inspired workflow with the following branching strategy:

1. **Main branches**:
   - `main`: Production-ready code
   - `develop`: Integration branch for features and fixes

2. **Feature and fix branches**:
   - `feature/<description>`: For new functionality
   - `fix/<description>`: For bug fixes
   - `hotfix/<description>`: For urgent production fixes

3. **Workflow steps**:
   - Fork the repository to your personal GitHub account
   - Clone your fork locally: `git clone https://github.com/your-org/vertex-ar.git`
   - Create a new branch from `develop`: `git checkout -b feature/your-feature-name`
   - Make your changes and commit following the commit message conventions
   - Push your branch to your fork: `git push origin feature/your-feature-name`
   - Create a Pull Request (PR) targeting the `develop` branch

Before submitting a PR, ensure your branch is up-to-date with the latest changes from the upstream `develop` branch:

```bash
git checkout develop
git pull upstream develop
git checkout feature/your-feature-name
git merge develop
```

Resolve any conflicts and test your changes thoroughly before submitting the PR.

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L38-L45)
- [docs/development/setup.md](file://docs/development/setup.md#L403-L431)

## Development Environment Setup

Proper environment setup is essential for consistent development and testing across all contributors.

### Prerequisites

- Python 3.11 or higher
- Git
- Docker and Docker Compose (optional)
- Virtual environment tool (venv, virtualenv, or conda)

### Setup Steps

1. **Clone and create virtual environment**:
```bash
git clone https://github.com/your-org/vertex-ar.git
cd vertex-ar
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with appropriate values for your development environment
```

4. **Create necessary directories**:
```bash
cd vertex-ar
mkdir -p storage static templates
mkdir -p storage/ar_content storage/nft-markers storage/qr-codes
```

5. **Run the application**:
```bash
uvicorn vertex-ar.app.main:app --reload
```

The application will be available at http://localhost:8000. For detailed setup instructions, refer to the full development guide in the documentation.

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L9-L32)
- [docs/development/setup.md](file://docs/development/setup.md#L32-L122)

## Coding Standards

The project adheres to strict coding standards to ensure code consistency, readability, and maintainability across the codebase.

### Python Style Guide

The codebase follows PEP 8 with specific project extensions:

- **Line length**: Maximum 127 characters
- **Indentation**: 4 spaces (no tabs)
- **Encoding**: UTF-8
- **Imports**: Grouped and sorted in the following order:
  1. Standard library imports
  2. Third-party library imports
  3. Local application imports

### Naming Conventions

```python
# Variables and functions: snake_case
user_name = "John"
def get_user_data():
    pass

# Classes: PascalCase
class UserManager:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 10 * 1024 * 1024

# Private: _leading_underscore
def _internal_function():
    pass
```

### Type Hints and Docstrings

All functions must include type hints and Google-style docstrings:

```python
from typing import Optional, List, Dict, Any

def create_user(
    username: str,
    password: str,
    is_admin: bool = False
) -> Dict[str, Any]:
    """Create a new user.
    
    Args:
        username: The username
        password: Plain text password
        is_admin: Whether user is admin
        
    Returns:
        User dictionary with metadata
        
    Raises:
        ValueError: If username already exists
    """
    pass
```

### Error Handling

Use specific exceptions and avoid bare except clauses:

```python
# GOOD: Specific exception handling
try:
    user = database.get_user(username)
except sqlite3.DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(
        status_code=500,
        detail="Database error occurred"
    )

# AVOID: Bare except
try:
    do_something()
except:  # This is discouraged
    pass
```

**Section sources**
- [docs/development/setup.md](file://docs/development/setup.md#L225-L395)

## Code Formatting and Pre-commit Hooks

The project uses automated code formatting and quality checks to maintain consistent code style and catch potential issues early.

### Pre-commit Configuration

The project includes a comprehensive pre-commit configuration in `.pre-commit-config.yaml` that runs multiple code quality checks before each commit:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: debug-statements
      - id: check-docstring-first

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3
        args: [--line-length=127]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black, --line-length=127]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=127, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports, --no-strict-optional]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, app/, -f, json, -o, bandit-report.json]
        pass_filenames: false

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [tests/, --tb=short, -q]

      - id: safety-check
        name: safety-check
        entry: safety
        language: system
        args: [check, --json, --output, safety-report.json]
        pass_filenames: false
        always_run: true
```

### Installation and Usage

To install the pre-commit hooks:

```bash
# Install pre-commit if not already installed
pip install pre-commit

# Install the hooks in your local repository
pre-commit install
```

The hooks will automatically run on every commit, checking for:
- Code formatting (Black)
- Import sorting (isort)
- Code style (flake8)
- Type checking (mypy)
- Security issues (bandit)
- Dependency vulnerabilities (safety)
- Test execution (pytest)

### Configuration Files

The project uses `pyproject.toml` for tool configuration, which defines settings for Black, isort, mypy, and coverage:

```toml
[tool.black]
line-length = 127
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 127

[tool.mypy]
python_version = "3.11"
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
```

**Section sources**
- [vertex-ar/.pre-commit-config.yaml](file://vertex-ar/.pre-commit-config.yaml#L1-L66)
- [vertex-ar/pyproject.toml](file://vertex-ar/pyproject.toml#L1-L64)
- [vertex-ar/requirements-dev.txt](file://vertex-ar/requirements-dev.txt#L1-L46)

## Commit Message Conventions

The project follows the Conventional Commits specification to ensure consistent and meaningful commit messages that can be used for generating changelogs and understanding the nature of changes.

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature or functionality
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting changes (white-space, formatting, etc.)
- `refactor`: Code refactoring (no new features or bug fixes)
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks, dependency updates, or configuration changes

### Scope

The scope should indicate the module or component affected by the change:
- `auth`: Authentication-related changes
- `database`: Database operations
- `storage`: Storage functionality
- `api`: API endpoints
- `nft`: NFT marker generation
- `ar`: AR functionality
- `ui`: User interface changes

### Examples

```bash
git commit -m "feat(auth): add two-factor authentication"
git commit -m "fix(database): prevent SQL injection in user queries"
git commit -m "docs(api): update authentication endpoint documentation"
git commit -m "test(nft): add unit tests for marker generation"
git commit -m "refactor(storage): extract storage interface"
git commit -m "chore(dependencies): update pytest to version 7.0"
```

### Best Practices

- Use the imperative mood ("add" not "added" or "adds")
- Capitalize the first letter of the description
- Do not end the description with a period
- Include a body for complex changes explaining the motivation and implementation
- Reference related issues in the footer (e.g., "Closes #123")

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L42-L44)
- [docs/development/setup.md](file://docs/development/setup.md#L435-L462)
- [COMMIT_MESSAGE.txt](file://COMMIT_MESSAGE.txt#L1-L70)

## Pull Request Review Process

The pull request review process ensures code quality, adherence to standards, and knowledge sharing among team members.

### PR Creation Guidelines

When creating a pull request, follow these guidelines:

1. **Target branch**: Always target the `develop` branch unless specifically instructed otherwise
2. **Descriptive title**: Use the conventional commit format for the PR title
3. **Detailed description**: Include:
   - Problem being solved
   - Solution approach
   - Any trade-offs or alternatives considered
   - Screenshots or logs for visual or performance changes
   - Testing steps performed

4. **Checklist**: Ensure all items from the author checklist are completed:
   - [ ] Code passes pytest and linters
   - [ ] CHANGELOG and documentation updated
   - [ ] Tests added/updated
   - [ ] No conflicts with `develop`
   - [ ] No secrets or user data committed

### Review Requirements

- **Minimum reviewers**: At least one team member must approve the PR
- **Code coverage**: Changes must not reduce overall test coverage below the project threshold
- **CI status**: All continuous integration checks must pass
- **Documentation**: Any user-facing changes must be documented

### Reviewer Responsibilities

Reviewers should:
- Check for adherence to coding standards
- Verify test coverage and quality
- Assess performance implications
- Consider security aspects
- Ensure proper error handling
- Validate documentation updates
- Provide constructive feedback

### Merge Criteria

A PR can be merged when:
- It has at least one approval from a team member
- All CI checks are passing
- The author has addressed all feedback
- The changes align with project goals and architecture
- Documentation is complete and accurate

The PR template in `PR_DESCRIPTION.md` provides a comprehensive structure for documenting changes, including problem description, solution, testing results, and impact assessment.

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L71-L87)
- [PR_DESCRIPTION.md](file://PR_DESCRIPTION.md#L1-L159)

## Testing Requirements

Comprehensive testing is a critical requirement for all contributions to ensure code quality and prevent regressions.

### Test Structure

The project has a well-organized test structure with different categories:

```bash
test_files/
├── unit/               # Unit tests (isolated component testing)
├── integration/        # Integration tests (component interactions)
├── performance/        # Performance tests (load and stress testing)
├── assets/             # Test data files
├── conftest.py         # Shared pytest configuration
└── README.md           # Test documentation
```

### Test Categories

| Category | Purpose | Location |
|--------|---------|---------|
| Unit | Isolated business logic, validators | `test_files/unit/` |
| Integration | Complete API/storage scenarios | `test_files/integration/` |
| E2E/UX | Admin panel, AR viewer | `test_files/integration/` |
| Security | Rate limiting, blocking, validation | `test_files/integration/` |
| Performance | Generation time, load capacity | `test_files/performance/` |
| Documentation | README/CHANGELOG/ROADMAP accuracy | `test_files/integration/` |

### Running Tests

The project provides multiple ways to run tests:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=vertex-ar --cov-report=term-missing

# Run specific test file
pytest test_files/integration/test_api_endpoints.py

# Run tests with specific marker
pytest -m "integration"

# Run performance tests
./test_files/run_performance_tests.sh

# Run the comprehensive test suite
./test_files/run_tests.sh all
```

The `run_tests.sh` script provides additional options:
- `fast`: Run fast tests only (excludes slow tests)
- `coverage`: Generate coverage report
- `verbose`: Verbose output
- `watch`: Run in watch mode (re-run on file changes)
- `failed`: Run only failed tests
- `unit`: Run only unit tests
- `integration`: Run only integration tests
- `performance`: Run only performance tests

### Test Coverage Goals

- **Overall coverage**: ≥ 78%
- **Critical paths**: 100% (authentication, content upload, marker generation, AR viewing)
- **New features**: Must include tests for happy path and edge cases
- **Bug fixes**: Must include regression tests

### Test Writing Guidelines

When adding new tests:
- Follow the same structure and patterns as existing tests
- Use descriptive test names
- Include comprehensive docstrings
- Test both success and failure cases
- Use fixtures for shared setup/teardown
- Mock external dependencies when appropriate
- Ensure tests are independent and repeatable

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L49-L59)
- [docs/development/testing.md](file://docs/development/testing.md#L1-L166)
- [pytest.ini](file://pytest.ini#L1-L70)
- [test_files/run_tests.sh](file://test_files/run_tests.sh#L1-L103)

## Documentation Updates

Keeping documentation up-to-date is essential for maintaining a healthy codebase and onboarding new contributors.

### Documentation Locations

The project maintains documentation in the `docs/` directory with the following structure:

- `docs/api/`: API reference and examples
- `docs/architecture/`: System architecture and design decisions
- `docs/development/`: Development guides and testing information
- `docs/guides/`: User and administrator guides
- `docs/mobile/`: Mobile application integration
- `docs/releases/`: Release notes and roadmap

### Required Documentation Updates

For each contribution, update the following documentation:

1. **CHANGELOG.md**: Add an entry describing the change, including:
   - Type of change (feature, fix, breaking change)
   - Affected components
   - User impact
   - Upgrade instructions (if applicable)

2. **Relevant documentation files**: Update any guides, API documentation, or architecture documents affected by the change.

3. **Code comments and docstrings**: Ensure all new or modified code has appropriate comments and docstrings.

4. **README files**: Update any relevant README files in affected modules.

### Documentation Standards

- Use clear, concise language
- Include examples and code snippets where appropriate
- Use consistent terminology
- Organize content logically with headings and subheadings
- Include diagrams for complex workflows or architectures
- Keep documentation up-to-date with code changes

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L65-L67)
- [docs/development/setup.md](file://docs/development/setup.md#L6-L15)

## Issue Reporting and Feature Requests

Effective issue reporting and feature requests help the team prioritize work and understand user needs.

### Bug Reports

When reporting a bug, include the following information:

1. **Title**: Clear and descriptive
2. **Description**: Detailed explanation of the problem
3. **Steps to reproduce**: Step-by-step instructions to reproduce the issue
4. **Expected behavior**: What should happen
5. **Actual behavior**: What actually happens
6. **Environment**: OS, browser, Python version, etc.
7. **Logs and screenshots**: Relevant error messages, stack traces, or screenshots
8. **Severity**: Impact on users or system

### Feature Requests

When requesting a new feature, include:

1. **Title**: Clear description of the desired feature
2. **Motivation**: Why the feature is needed
3. **Use cases**: Specific scenarios where the feature would be used
4. **Proposed solution**: Suggested implementation approach
5. **Alternatives considered**: Other solutions that were evaluated
6. **Impact**: How the feature would affect existing functionality
7. **Priority**: Importance and urgency

### Issue Templates

The project should use GitHub issue templates to standardize reporting. While specific templates are not visible in the current codebase, contributors should follow the structure outlined above to ensure comprehensive issue reports.

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L97-L100)

## Onboarding for New Contributors

The onboarding process helps new contributors become productive quickly and understand project conventions.

### Getting Started

1. **Read the documentation**: Start with `CONTRIBUTING.md` and `docs/development/setup.md`
2. **Set up the development environment**: Follow the setup instructions
3. **Run the tests**: Verify your environment is working correctly
4. **Explore the codebase**: Understand the project structure and key components
5. **Join the community**: Connect with other contributors through available channels

### First Contribution

New contributors are encouraged to start with "good first issue" labeled tasks, which are typically:
- Small bug fixes
- Documentation improvements
- Test enhancements
- Minor feature additions

### Learning Resources

- `docs/development/setup.md`: Comprehensive development guide
- `docs/development/architecture.md`: System architecture overview
- `docs/development/testing.md`: Testing practices and guidelines
- Example pull requests: Study recent PRs to understand the expected quality and format

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L1-L103)
- [docs/development/setup.md](file://docs/development/setup.md#L1-L800)

## Community Engagement

Active community engagement fosters collaboration, knowledge sharing, and project growth.

### Communication Channels

- **GitHub Issues**: For reporting bugs and requesting features
- **GitHub Discussions**: For general questions and design discussions
- **Discord**: For real-time communication and quick questions
- **Email**: For security-related issues (security@vertex-ar.example.com)

### Best Practices

- Be respectful and professional in all communications
- Respond to questions and feedback in a timely manner
- Provide constructive criticism
- Acknowledge and appreciate contributions
- Share knowledge and help others learn

### Contribution Recognition

The project values all contributions and recognizes contributors through:
- Contributor lists in documentation
- Special acknowledgments for significant contributions
- Regular updates on project progress and achievements

By following these guidelines, contributors can help maintain a positive, productive, and inclusive community around the AR backend project.

**Section sources**
- [CONTRIBUTING.md](file://CONTRIBUTING.md#L97-L100)