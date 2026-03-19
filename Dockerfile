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

EXPOSE 8900

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8900", "--reload", "--reload-dir", "/app/src", "--reload-include", "*.py"]
