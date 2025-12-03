# Test Environment Setup

<cite>
**Referenced Files in This Document**   
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)
- [docker-compose.test.yml](file://docker-compose.test.yml)
- [local-guide.md](file://docs/testing/local-guide.md)
- [ide-setup.md](file://docs/testing/ide-setup.md)
- [.env.example](file://vertex-ar/.env.example)
- [run_tests.sh](file://test_files/run_tests.sh)
- [conftest.py](file://test_files/conftest.py)
- [pytest.ini](file://pytest.ini)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document provides comprehensive guidance for setting up a local test environment for the Vertex AR project. It covers dependency configuration, test database initialization, environment variable management, containerized testing with Docker Compose, and IDE-specific configurations for VS Code and PyCharm. The guide also includes step-by-step setup procedures, test fixture configuration, database cleanup strategies, mock services usage, and solutions for common setup issues such as port conflicts, missing binaries, and permission problems.

## Project Structure
The project follows a modular structure with clear separation between application code, tests, documentation, and configuration files. The test environment is primarily configured through dedicated files in specific directories.

```mermaid
graph TD
A[Project Root] --> B[docs/testing]
A --> C[vertex-ar]
A --> D[test_files]
A --> E[scripts]
B --> F[local-guide.md]
B --> G[ide-setup.md]
C --> H[requirements-dev.txt]
C --> I[.env.example]
D --> J[conftest.py]
D --> K[run_tests.sh]
E --> L[quick_test.sh]
```

**Diagram sources**
- [local-guide.md](file://docs/testing/local-guide.md)
- [ide-setup.md](file://docs/testing/ide-setup.md)
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)
- [.env.example](file://vertex-ar/.env.example)
- [conftest.py](file://test_files/conftest.py)
- [run_tests.sh](file://test_files/run_tests.sh)

**Section sources**
- [local-guide.md](file://docs/testing/local-guide.md)
- [ide-setup.md](file://docs/testing/ide-setup.md)

## Core Components
The test environment setup relies on several core components including dependency management through requirements-dev.txt, environment variable configuration via .env files, containerized testing with docker-compose.test.yml, and IDE-specific configurations documented in ide-setup.md. The local-guide.md provides step-by-step instructions for setting up the testing environment, while various scripts automate common testing tasks.

**Section sources**
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)
- [docker-compose.test.yml](file://docker-compose.test.yml)
- [local-guide.md](file://docs/testing/local-guide.md)
- [ide-setup.md](file://docs/testing/ide-setup.md)

## Architecture Overview
The test environment architecture consists of multiple layers including development dependencies, testing infrastructure, configuration management, and IDE integration. The system uses pytest as the primary testing framework with various plugins for coverage, mocking, and performance testing. Environment variables control application behavior during testing, while Docker Compose enables isolated service testing.

```mermaid
graph TD
A[Test Environment] --> B[Development Dependencies]
A --> C[Testing Framework]
A --> D[Configuration]
A --> E[IDE Integration]
B --> F[pytest]
B --> G[black]
B --> H[flake8]
B --> I[mypy]
C --> J[pytest-cov]
C --> K[pytest-mock]
C --> L[pytest-asyncio]
D --> M[.env files]
D --> N[docker-compose.test.yml]
E --> O[VS Code]
E --> P[PyCharm]
```

**Diagram sources**
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)
- [docker-compose.test.yml](file://docker-compose.test.yml)
- [.env.example](file://vertex-ar/.env.example)
- [ide-setup.md](file://docs/testing/ide-setup.md)

## Detailed Component Analysis

### Dependency Configuration
The test environment uses requirements-dev.txt to manage development and testing dependencies. This file includes testing frameworks, code quality tools, security scanners, performance testing tools, and development utilities.

```mermaid
graph TD
A[requirements-dev.txt] --> B[Testing Framework]
A --> C[Code Quality]
A --> D[Security Scanning]
A --> E[Performance Testing]
A --> F[Development Utilities]
B --> G[pytest]
B --> H[pytest-cov]
B --> I[pytest-mock]
C --> J[black]
C --> K[isort]
C --> L[flake8]
D --> M[bandit]
D --> N[safety]
E --> O[locust]
E --> P[psutil]
F --> Q[python-dotenv]
F --> R[watchdog]
```

**Diagram sources**
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)

**Section sources**
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)

### Test Database Initialization
The test environment initializes SQLite databases for testing purposes. The configuration specifies test-friendly database URLs and provides mechanisms for cleaning up test data between test runs.

```mermaid
flowchart TD
Start([Start]) --> CreateDB["Create test database"]
CreateDB --> ConfigureDB["Configure DATABASE_URL"]
ConfigureDB --> RunMigrations["Run database migrations"]
RunMigrations --> SeedData["Seed with test data"]
SeedData --> ExecuteTests["Execute tests"]
ExecuteTests --> Cleanup["Cleanup test database"]
Cleanup --> End([End])
style CreateDB fill:#f9f,stroke:#333
style Cleanup fill:#f96,stroke:#333
```

**Diagram sources**
- [.env.example](file://vertex-ar/.env.example)
- [local-guide.md](file://docs/testing/local-guide.md)
- [run_tests.sh](file://test_files/run_tests.sh)

### Environment Variable Management
Environment variables are managed through .env files, with .env.example serving as a template. The test environment uses specific values optimized for testing, such as disabled rate limiting and debug mode enabled.

```mermaid
classDiagram
class EnvironmentVariables {
+DEBUG : bool
+SECRET_KEY : string
+DATABASE_URL : string
+STORAGE_TYPE : string
+RATE_LIMIT_ENABLED : bool
+LOG_LEVEL : string
}
class EnvFile {
+create_from_template()
+load_from_file()
+override_for_testing()
}
class TestConfig {
+get_database_url()
+is_rate_limiting_enabled()
+get_log_level()
}
EnvFile --> EnvironmentVariables : "contains"
TestConfig --> EnvironmentVariables : "reads"
```

**Diagram sources**
- [.env.example](file://vertex-ar/.env.example)
- [local-guide.md](file://docs/testing/local-guide.md)

### Containerized Testing
The docker-compose.test.yml file defines a minimal Docker Compose configuration for testing isolated services. It includes a test application service and an Nginx proxy service with health checks.

```mermaid
graph TD
A[docker-compose.test.yml] --> B[test-app]
A --> C[nginx-proxy]
B --> D[nginx:alpine]
B --> E[Health Check]
C --> F[nginx:alpine]
C --> G[Volume Mapping]
C --> H[Port Mapping]
C --> I[Health Check]
E --> J["CMD: curl -f http://localhost/"]
H --> K["8080:80"]
I --> L["CMD: curl -f http://localhost/health"]
style B fill:#ccf,stroke:#333
style C fill:#ccf,stroke:#333
```

**Diagram sources**
- [docker-compose.test.yml](file://docker-compose.test.yml)

### IDE Configuration
The ide-setup.md document provides detailed instructions for configuring popular IDEs like VS Code and PyCharm for testing. This includes settings for test discovery, debugging configurations, and task automation.

```mermaid
graph TD
A[IDE Setup] --> B[VS Code]
A --> C[PyCharm]
B --> D[settings.json]
B --> E[launch.json]
B --> F[tasks.json]
C --> G[Python Interpreter]
C --> H[Pytest Configuration]
C --> I[Run Configurations]
D --> J[python.testing.pytestArgs]
E --> K[Debug Tests Configuration]
F --> L[Run All Tests Task]
style D fill:#f9f,stroke:#333
style E fill:#f9f,stroke:#333
style F fill:#f9f,stroke:#333
style G fill:#f9f,stroke:#333
style H fill:#f9f,stroke:#333
style I fill:#f9f,stroke:#333
```

**Diagram sources**
- [ide-setup.md](file://docs/testing/ide-setup.md)

## Dependency Analysis
The test environment has a well-defined dependency structure with clear separation between production and development dependencies. The requirements-dev.txt file extends the core requirements.txt with testing-specific packages.

```mermaid
graph TD
A[requirements.txt] --> B[requirements-dev.txt]
A --> C[fastapi]
A --> D[sqlalchemy]
A --> E[minio]
B --> F[pytest]
B --> G[black]
B --> H[flake8]
B --> I[mypy]
B --> J[bandit]
B --> K[safety]
B --> L[locust]
style A fill:#cfc,stroke:#333
style B fill:#ccf,stroke:#333
```

**Diagram sources**
- [requirements.txt](file://vertex-ar/requirements.txt)
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)

**Section sources**
- [requirements.txt](file://vertex-ar/requirements.txt)
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)

## Performance Considerations
The test environment includes performance testing capabilities through dedicated tools and scripts. The pytest.ini configuration optimizes test execution with parallel execution options and performance monitoring.

```mermaid
flowchart TD
A[Performance Testing] --> B[pytest-xdist]
A --> C[locust]
A --> D[psutil]
A --> E[memory-profiler]
B --> F[Parallel Test Execution]
C --> G[Load Testing]
D --> H[System Monitoring]
E --> I[Memory Profiling]
F --> J["-n auto"]
G --> K[Simulate Concurrent Users]
H --> L[CPU/Memory/Disk Usage]
I --> M[Identify Memory Leaks]
style F fill:#f96,stroke:#333
style G fill:#f96,stroke:#333
style H fill:#f96,stroke:#333
style I fill:#f96,stroke:#333
```

**Diagram sources**
- [requirements-dev.txt](file://vertex-ar/requirements-dev.txt)
- [pytest.ini](file://pytest.ini)
- [run_performance_tests.sh](file://test_files/run_performance_tests.sh)

## Troubleshooting Guide
Common setup issues and their solutions are documented in the local-guide.md file. These include module not found errors, database locking issues, permission problems, and rate limiting conflicts during testing.

```mermaid
graph TD
A[Common Issues] --> B[ModuleNotFoundError]
A --> C[Database Locked]
A --> D[Permission Denied]
A --> E[Rate Limiting]
B --> F[Activate Virtual Environment]
B --> G[Install Dependencies]
C --> H[Remove test_app_data.db]
D --> I[Create Directory]
D --> J[Set Permissions]
E --> K[Disable Rate Limiting]
style B fill:#f96,stroke:#333
style C fill:#f96,stroke:#333
style D fill:#f96,stroke:#333
style E fill:#f96,stroke:#333
```

**Diagram sources**
- [local-guide.md](file://docs/testing/local-guide.md)
- [run_tests.sh](file://test_files/run_tests.sh)

**Section sources**
- [local-guide.md](file://docs/testing/local-guide.md)
- [run_tests.sh](file://test_files/run_tests.sh)

## Conclusion
The test environment setup for Vertex AR is comprehensive and well-documented, providing developers with all necessary tools and configurations for effective testing. The combination of dependency management, environment configuration, containerized testing, and IDE integration creates a robust foundation for both unit and integration testing. By following the documented procedures, developers can quickly establish a functional test environment and begin contributing to the project.