FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY ctxd ./ctxd
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "ctxd.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
