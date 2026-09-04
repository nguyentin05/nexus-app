FROM python:3.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY app ./app

RUN uv sync --frozen --no-cache --no-dev

FROM python:3.13-slim-bookworm AS runtime
LABEL org.opencontainers.image.source="https://github.com/nguyentin05/nexus-app"
LABEL org.opencontainers.image.title="nexus-auth-service"

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app app ./app

RUN pip install --no-cache-dir certifi==2022.12.7

USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
