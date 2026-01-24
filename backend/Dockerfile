FROM python:3.12-slim

LABEL maintainer="Mahesh"
LABEL security_text="I'll be back!"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.0

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY . .

RUN poetry install --no-interaction --no-ansi

RUN cat > /app/entrypoint.sh << 'EOF'
#!/bin/bash
set -e

echo "Initializing database..."
python -m app.db.init_db

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
EOF

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Health check for ECS
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1


ENTRYPOINT ["/app/entrypoint.sh"]
