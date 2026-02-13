FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

FROM base AS ci

COPY . /app

RUN python -m pip install --upgrade pip && \
    pip install ".[dev]" bandit pip-audit ruff

FROM base AS runtime

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
COPY main.py /app/main.py

RUN python -m pip install --upgrade pip && \
    pip install .

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
