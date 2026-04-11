# ArtMentorAI Project

[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-purple.json)](https://github.com/copier-org/copier)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

A Python project



## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker Desktop (for Qdrant vector database)

### Install Dependencies

```bash
uv sync
```


### Build Package

```bash
uv build
# or: pip install .
```

### Start Qdrant (Vector Database)

```bash
docker compose up -d
```

### Run the Server

```bash
uv run artmentorai-project
```

The API will be available at `http://127.0.0.1:8000` with docs at `/docs`.

## 📚 Documentation

- **MVP API contracts (stable)**: see `docs/api-contracts.md`
