# ---- Stage 1: install dependencies ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY requirements.txt .
COPY requirements/ ./requirements/
RUN python -m pip install --prefix=/install -r requirements.txt


# ---- Stage 2: runtime image ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /install /usr/local

# Fixed UID so Kubernetes can enforce runAsNonRoot
RUN adduser --disabled-password --gecos "" --no-create-home --uid 1000 appuser \
    && mkdir -p /var/lib/nexus/private_media /app/private_media \
    && chown -R appuser:appuser /var/lib/nexus /app

COPY --chown=appuser:appuser . .

USER 1000

EXPOSE 8000

# Production default. docker-compose overrides this with runserver for dev.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
