# ArtMentorAI Project

[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-purple.json)](https://github.com/copier-org/copier)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

A Python project



## Quick local setup

### 1. Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (installs and manages Python **3.12+** for this repo)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (runs **Qdrant** on ports `6333` / `6334`, matching app defaults)

### 2. Clone and install

```bash
git clone https://github.com/maximberchun/ArtMentorAI.git
cd ArtMentorAI
uv sync
```

### 3. Environment

Copy `.env.example` to `.env` and fill in real values (at minimum you need an **OpenRouter** API key and a **Supabase** project URL for the app to start; other keys depend on the features you use).

- **Unix/macOS:** `cp .env.example .env`
- **Windows (PowerShell):** `Copy-Item .env.example .env`

See `.env.example` for all variables. If you are not using web search locally, set `WEB_SEARCH_ENABLED=false` so a Serper key is not required.

### 4. Start Qdrant

```bash
docker compose up -d
```

Wait until the `qdrant` container is healthy (first run may download the image). Data is stored under `./qdrant_data`.

### 5. Run the API

```bash
uv run artmentorai-project
```

- API: `http://127.0.0.1:8000` (or the `HOST` / `PORT` from `.env`)
- OpenAPI docs: `http://127.0.0.1:8000/docs`

### Optional: tests

```bash
uv sync --extra test
uv run pytest
```

### Optional: build the package

```bash
uv build
```

## 📚 Documentation

- **MVP API contracts (stable)**: see `docs/api-contracts.md`
- **Deployment appendix (thesis/demo runbook)**: see `docs/deployment-appendix.md`
