# Wind Price Lab API — optimized for Railway (PORT, DATABASE_URL)
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies (mirrors pyproject.toml; avoids packaging edge cases in slim CI)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir \
        "fastapi>=0.110" \
        "uvicorn[standard]>=0.27" \
        "sqlalchemy>=2.0" \
        "psycopg[binary]>=3.1" \
        "pydantic-settings>=2.2" \
        "pandas>=2.1" \
        "numpy>=1.26" \
        "scikit-learn>=1.4" \
        "joblib>=1.3" \
        "httpx>=0.27"

COPY README.md pyproject.toml ./
COPY apps ./apps
COPY services ./services
COPY db ./db

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

# Railway injects PORT; default 8000 for local docker run
CMD ["sh", "-c", "exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
