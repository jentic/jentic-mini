# Development Setup

## Prerequisites

- **Python 3.11+**
- **PDM** (Python dependency manager):
  ```bash
  curl -sSL https://pdm-project.org/install-pdm.py | python3 -
  ```
- **Node.js 24+** and **npm** (for the UI)
- **Docker** and **Docker Compose** (for running the server)

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/jentic/jentic-mini.git
cd jentic-mini
```

### 2. Create virtual environment and install dependencies

```bash
pdm venv create
pdm install --dev
```

### 3. Install UI dependencies

```bash
cd ui
npm install
```

### 4. Run the server (Docker)

There are two compose files:

- **`compose.yml`** — base configuration (production-like)
- **`compose.dev.yml`** — adds Vite dev server with HMR on port 5173

```bash
docker compose up -d                                  # base only
docker compose -f compose.yml -f compose.dev.yml up   # with UI dev server
```

The API is available at `http://localhost:8900` and the Swagger UI at `http://localhost:8900/docs`.

### 5. UI development (optional)

For frontend development with hot module replacement outside Docker:

```bash
cd ui
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies API calls to the backend on port 8900.

## Day-to-day Development

- **Python changes**: `src/` is volume-mounted into the container. Uvicorn auto-reloads on any `.py` file change — no container restart needed.
- **UI changes**: Use `npm run dev` in `ui/` for Vite HMR.
- **Rebuild UI in Docker**: `cd ui && npm run build`, then `docker compose up -d --build`.

## Running Tests

### Backend

```bash
pdm run python -m pytest tests/ -v
```

### UI

```bash
cd ui
npm test              # Vitest watch mode
npm run test:run      # Single CI run
npm run test:e2e      # Playwright E2E tests (mocked)
npm run test:e2e:docker  # Docker E2E (real backend)
```

## Linting

### UI

```bash
cd ui
npm run lint          # ESLint check (includes Prettier)
npm run lint:fix      # Auto-fix
```
