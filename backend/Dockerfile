# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.12-slim AS runtime

RUN groupadd --system appuser && useradd --system --gid appuser --no-create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

# Build-time-only placeholders so `collectstatic` can import settings without a real DB or
# secret; these are never used at runtime, real values are injected by whatever runs the image.
ENV SECRET_KEY=build-time-placeholder \
    DATABASE_URL=postgres://placeholder:placeholder@localhost:5432/placeholder \
    DEBUG=False \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python manage.py collectstatic --noinput

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
