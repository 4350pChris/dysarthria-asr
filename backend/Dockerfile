FROM python:3.14-slim

WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY seed/phrases.csv /app/seed/phrases.csv
COPY src ./src
COPY static ./static

EXPOSE 8000
CMD ["uv", "run", "--frozen", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
