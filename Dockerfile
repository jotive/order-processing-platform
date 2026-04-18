FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN python -m ensurepip --upgrade \
    && python -m pip install --prefix=/install "fastapi>=0.115" "uvicorn[standard]>=0.32" \
        "pydantic>=2.9" "pydantic-settings>=2.6" \
        "sqlalchemy[asyncio]>=2.0" "asyncpg>=0.30" "alembic>=1.14" \
        "redis>=5.2" "python-json-logger>=2.0"


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/usr/local/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -u 1000 app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=app:app . /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
