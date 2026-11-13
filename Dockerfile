# syntax=docker/dockerfile:1

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    DJANGO_DB_PATH=/data/db.sqlite3

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN mkdir -p /data

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uv", "run", "--no-dev", "gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000"]
