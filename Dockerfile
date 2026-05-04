# Production image for ArtMentorAI FastAPI
# Python 3.12, non-root, bind 0.0.0.0:8000. Do not use --dev (no .env load)

FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=/usr/local/bin/python \
    SERVER__HOST=0.0.0.0 \
    SERVER__PORT=8000

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

RUN uv sync --frozen --no-dev

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --no-log-init --home-dir /app --shell /usr/sbin/nologin app \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["/app/.venv/bin/artmentorai-project"]
