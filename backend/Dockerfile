FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app/ ./app/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -e .

COPY alembic.ini ./
COPY alembic/ ./alembic/

# Les prompts vivent à la racine du dépôt (/prompts) et sont montés en lecture
# seule par docker compose : on les modifie sans rebuild (DEVIATIONS D4).
RUN mkdir -p /app/prompts
ENV PROMPTS_DIR=/app/prompts

RUN useradd -u 1000 -m -s /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
