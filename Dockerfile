# One-process image for a small free host (Render). See DEPLOY.md and deploy/server.py.
# Local development does not use it: see the Quickstart in README.md.
FROM ghcr.io/astral-sh/uv:0.12.5-python3.13-trixie-slim

WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/.cache/fastembed \
    RUN_EXECUTION=inline

# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

# Bake the embedding model (~90 MB) into the image: no download at start.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

CMD ["sh", "deploy/start.sh"]
