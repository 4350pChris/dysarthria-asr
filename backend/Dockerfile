FROM python:3.14-slim AS builder

WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

FROM python:3.14-slim

WORKDIR /app/backend
ENV PATH="/app/backend/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/backend/.venv ./.venv

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
COPY static ./static

EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
