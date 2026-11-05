FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Claude Code, qui note les réponses sur ton abonnement Claude (DEVIATIONS D14) : le
# binaire officiel du canal « stable », vérifié par sa somme SHA-256 du manifeste, sans
# mise à jour automatique. Rebuild avec --build-arg CLAUDE_CODE_CHANNEL=latest (ou une
# version, 2.1.311) pour en changer.
ARG CLAUDE_CODE_CHANNEL=stable
RUN set -eu; \
    base=https://downloads.claude.ai/claude-code-releases; \
    case "$(uname -m)" in x86_64) arch=x64 ;; aarch64|arm64) arch=arm64 ;; *) exit 1 ;; esac; \
    case "$CLAUDE_CODE_CHANNEL" in [0-9]*) version="$CLAUDE_CODE_CHANNEL" ;; \
        *) version="$(curl -fsSL "$base/$CLAUDE_CODE_CHANNEL")" ;; esac; \
    checksum="$(curl -fsSL "$base/$version/manifest.json" \
        | python -c "import json, sys; print(json.load(sys.stdin)['platforms']['linux-$arch']['checksum'])")"; \
    curl -fsSL -o /usr/local/bin/claude "$base/$version/linux-$arch/claude"; \
    echo "$checksum  /usr/local/bin/claude" | sha256sum -c -; \
    chmod 755 /usr/local/bin/claude; \
    claude --version
ENV DISABLE_AUTOUPDATER=1

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
