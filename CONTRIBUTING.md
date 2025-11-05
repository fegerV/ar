# Contributing to Vertex AR

Thank you for your interest in contributing to Vertex AR! This guide will help you get started with contributing to the project.

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Git
- Docker (optional, for containerized development)
- Basic knowledge of FastAPI, AR.js, and web technologies

### Development Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/your-username/vertex-ar.git
   cd vertex-ar
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   cd vertex-ar
   python main.py
   ```

## 📋 Development Workflow

### Branch Strategy

We use Git Flow branching model:

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical fixes for production

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Making Changes

1. **Code Style**
   - Follow PEP 8 for Python code
   - Use Black for code formatting
   - Use isort for import sorting
   - Add type hints where appropriate

2. **Testing**
   - Write unit tests for new functionality
   - Ensure all tests pass
   - Maintain test coverage above 70%

3. **Documentation**
   - Update API documentation for new endpoints
   - Add inline comments for complex logic
   - Update relevant documentation files

### Commit Guidelines

Use conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

Examples:
```bash
git commit -m "feat(api): add batch NFT marker generation"
git commit -m "fix(auth): resolve JWT token expiration issue"
git commit -m "docs: update API documentation"
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vertex-ar --cov-report=html

# Run specific test file
pytest tests/test_api_endpoints.py

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_api_endpoints.py    # API endpoint tests
├── test_ar_functionality.py # AR functionality tests
├── test_auth.py             # Authentication tests
├── test_nft_generation.py   # NFT marker generation tests
└── test_storage.py          # Storage system tests
```

### Writing Tests

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **API Tests**: Test HTTP endpoints
4. **Performance Tests**: Ensure performance requirements

Example test:
```python
import pytest
from fastapi.testclient import TestClient
from vertex_ar.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## 📝 Code Review Process

### Pull Request Process

1. **Create Pull Request**
   - Push your feature branch to your fork
   - Create a PR from your branch to `develop`
   - Fill out the PR template completely

2. **PR Requirements**
   - Clear description of changes
   - Link to relevant issues
   - Tests pass
   - Documentation updated
   - Code follows style guidelines

3. **Review Process**
   - At least one approval required
   - Address all review comments
   - Ensure CI/CD checks pass
   - Merge when approved

### Code Review Guidelines

When reviewing code:
- Check for correctness and logic
- Verify test coverage
- Ensure documentation is updated
- Check for security vulnerabilities
- Verify performance implications

## 🏗️ Project Structure

```
vertex-ar/
├── vertex-ar/                # Main application
│   ├── main.py              # FastAPI application
│   ├── models/              # Data models
│   ├── api/                 # API routes
│   ├── services/            # Business logic
│   ├── utils/               # Utility functions
│   ├── templates/           # HTML templates
│   ├── static/              # Static files
│   └── tests/               # Application tests
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── tests/                  # Test suite
├── docker-compose.yml      # Docker configuration
├── requirements.txt        # Python dependencies
└── README.md              # Project documentation
```

## 🐛 Bug Reports

### Reporting Bugs

1. **Search existing issues** - Check if the bug is already reported
2. **Use bug report template** - Fill out all required information
3. **Provide reproduction steps** - Clear steps to reproduce the issue
4. **Include environment details** - OS, Python version, etc.
5. **Add logs/screenshots** - Any relevant debugging information

### Bug Report Template

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 20.04]
- Python version: [e.g., 3.9.7]
- Vertex AR version: [e.g., 1.1.0]

## Additional Context
Any other relevant information
```

## 💡 Feature Requests

### Proposing Features

1. **Discuss in issues** - Open an issue for discussion
2. **Provide use case** - Explain why the feature is needed
3. **Consider implementation** - Suggest possible approaches
4. **Check roadmap** - Verify it aligns with project goals

### Feature Request Template

```markdown
## Feature Description
Clear description of the proposed feature

## Use Case
Why is this feature needed?

## Proposed Solution
How should it work?

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Any other relevant information
```

## 📚 Documentation

### Documentation Types

- **API Documentation**: Endpoint specifications and examples
- **User Guides**: How-to guides for end users
- **Developer Documentation**: Technical documentation for developers
- **Architecture Documentation**: System design and architecture

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add screenshots and diagrams where helpful
- Keep documentation up to date with code changes
- Use markdown formatting consistently

## 🔒 Security

### Security Guidelines

- Never commit secrets or API keys
- Follow secure coding practices
- Report security vulnerabilities privately
- Use HTTPS for all communications
- Validate all input data

### Reporting Security Issues

For security vulnerabilities, please email:
📧 security@vertex-ar.example.com

## 📞 Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Discord**: [Vertex AR Community](https://discord.gg/vertexar)

### Resources

- [Documentation](../docs/README.md)
- [API Reference](docs/api/endpoints.md)
- [Architecture Guide](docs/development/architecture.md)
- [FAQ](../README.md#faq)

## 🏆 Recognition

Contributors are recognized in:
- README.md contributors section
- CHANGELOG.md for significant contributions
- Release notes for major contributions

## 📄 License

By contributing to Vertex AR, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Vertex AR! 🎉

If you have any questions, don't hesitate to ask in our [Discord community](https://discord.gg/vertexar) or open a discussion.