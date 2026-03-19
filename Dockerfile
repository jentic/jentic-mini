FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone arazzo-engine and install runner from source
RUN git clone --depth 1 https://github.com/jentic/arazzo-engine.git /opt/arazzo-engine \
    && pip install --no-cache-dir -e /opt/arazzo-engine/runner

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8900

# Entrypoint runs DB init + broker app seed before starting the server.
# Both steps are idempotent — safe on every container start.
CMD ["/app/docker-entrypoint.sh"]
