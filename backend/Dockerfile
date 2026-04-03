FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/backend/

RUN mkdir -p /app/backend/data

ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/backend/data/vrednost.db

EXPOSE 8000

CMD ["sh", "-c", "python -m backend.scripts.import_gurs 2>/dev/null || true; uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
