# Stage 1: Build UI
FROM node:24-slim AS ui-build
WORKDIR /build
COPY ui/ ./ui/
RUN mkdir -p static
RUN cd ui && npm ci --ignore-scripts && npm run build

# Stage 2: Install Python dependencies
FROM python:3.11-slim AS py-deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev curl git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install PDM (recommended method)
RUN curl -sSL https://pdm-project.org/install-pdm.py | python3 -

# Clone arazzo-engine and install runner from source
RUN git clone --depth 1 https://github.com/jentic/arazzo-engine.git /opt/arazzo-engine \
    && /root/.local/bin/pdm venv create --with-pip \
    && /app/.venv/bin/pip install --no-cache-dir -e /opt/arazzo-engine/runner

COPY pyproject.toml pdm.lock ./
RUN /root/.local/bin/pdm install --prod --no-editable --no-self

# Stage 3: Runtime
FROM python:3.11-slim

ARG APP_VERSION=0.9.0
ENV APP_VERSION=${APP_VERSION}

LABEL maintainer="vladimir@jentic.com" \
      org.opencontainers.image.authors="vladimir@jentic.com" \
      org.opencontainers.image.url="https://github.com/jentic/jentic-mini" \
      org.opencontainers.image.source="https://github.com/jentic/jentic-mini" \
      org.opencontainers.image.description="Jentic Mini Docker image" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${APP_VERSION}"

WORKDIR /app

COPY --from=py-deps /app/.venv /app/.venv
COPY --from=py-deps /opt/arazzo-engine /opt/arazzo-engine
ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir -p /app/data /app/src

# Copy source into /app/src so that `from src.xxx` imports work from WORKDIR /app
COPY src/ /app/src/

# Copy Alembic migration config and scripts
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/

# Copy built UI assets from stage 1 — placed outside /app/src/ so the
# dev bind mount (./src:/app/src) doesn't hide them at runtime.
COPY --from=ui-build /build/static/ /app/static/

COPY --chmod=0644 LICENSE NOTICE llms.txt /app/
COPY --chmod=0755 docker-entrypoint.sh /app/docker-entrypoint.sh

# Run as non-root
RUN useradd -r -s /bin/false jentic \
    && chown -R jentic:jentic /app/data
USER jentic

EXPOSE 8900

# Entrypoint runs DB init + broker app seed before starting the server.
# Both steps are idempotent — safe on every container start.
CMD ["/app/docker-entrypoint.sh"]
