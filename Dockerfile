# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
build-essential curl && rm -rf /var/lib/apt/lists/*


COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install -e .


COPY . .


EXPOSE 8000
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir src"]
