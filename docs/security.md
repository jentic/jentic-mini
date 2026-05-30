# Pluggable Security Registry & Barrikade Integration

Jentic Mini features a modular, vendor-neutral **Security Plugin Registry** designed to protect the gateway at both the **Ingress** (inbound client requests) and **Egress** (downstream API responses) boundaries. 

The primary security driver integrated into Jentic Mini is **Barrikade**, an AI-powered security scanner that classifies payloads for prompt injection, sensitive data leakage, and toxic content.

---

## Architecture Overview

To maintain complete separation of concerns and avoid coupling the gateway to proprietary third-party SDKs, the security system is designed as a pluggable registry:

```
                  ┌───────────────────────────┐
                  │   Inbound Client Request  │
                  └─────────────┬─────────────┘
                                │
                                ▼
              ┌───────────────────────────────────┐
              │     SecurityIngressMiddleware     │
              └─────────────────┬─────────────────┘
                                │ (scan_ingress)
                                ▼
              ┌───────────────────────────────────┐
              │      security_registry (SL)       │
              └─────────────────┬─────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
         ┌─────────────────────┐ ┌─────────────────────┐
         │   BarrikadePlugin   │ │   CustomPlugin      │
         └──────────┬──────────┘ └──────────┬──────────┘
                    │                       │
                    ▼ (scan_text)           ▼
         ┌─────────────────────-┐ ┌─────────────────────-┐
         │ Barrikade API /detect│ │   Custom Classifier  │       
         └─────────────────────-┘ └─────────────────────-┘
```

The gateway secures two distinct boundaries:
1. **Ingress (Inbound Interception)**: A global FastAPI/Starlette middleware intercepting client query strings and request payloads (POST/PUT/etc.) before routing or database execution. This blocks prompt injections and malicious search queries early.
2. **Egress (Response Interception)**: Caught at the catch-all `broker.py` proxy router right after the raw upstream response bytes are read from third-party APIs. This blocks PII leaks, secret credentials, or indirect prompt injections returned by external systems before they reach the agent or Arazzo workflow runner.

---

## Code Structure

The security registry is organized under `src/security/`:

* **`src/security/plugin.py`**: Declares `SecurityVerdict` (a slotted dataclass modeling classifications) and `SecurityPlugin` (the abstract base class).
* **`src/security/registry.py`**: Coordinates registered plugins, executing dynamic ingress/response filters with **first-block-wins short-circuiting** to optimize latency.
* **`src/security/utils.py`**: High-performance, isolated data-extraction parsers (such as recursive JSON value collection).
* **`src/security/barrikade.py`**: Concrete implementation of `SecurityPlugin` encapsulating HTTP communication with the FastAPI Barrikade container.

---

## Configuration Reference

The security layer is fully configurable via standard environment variables:

| Environment Variable | Type | Default | Description |
|----------------------|------|---------|-------------|
| `BARRIKADE_URL` | String | `None` | Endpoint of the running Barrikade container (e.g. `http://localhost:8000`). If unset, the plugin is not registered, disabling scanning with zero latency. |
| `BARRIKADE_TIMEOUT_MS` | Integer | `1000` | Gateway execution timeout for security checks. Safe defaults guarantee low proxy overhead. |
| `BARRIKADE_FAIL_OPEN` | Boolean | `True` | Policy under network or timeout exceptions. Set to `True` to allow traffic in case the security service goes down, or `False` to fail closed (blocking all proxy requests). |

---

## Core Hooks & Lifecycle

### 1. Inbound Ingress Interception
* **Middleware**: `SecurityIngressMiddleware` (in `src/main.py`)
* **Logic**:
  1. Inspects incoming `request.query_params` using `extract_text_from_query_params`.
  2. If the request carries a body (POST/PUT/PATCH/DELETE), reads `request.body()`, extracts raw string values recursively from JSON (ignoring syntax tags), and recycles the Starlette stream.
  3. Delegates text to `security_registry.scan_ingress(text, path, method)`.
  4. If a plugin flags a threat, the middleware instantly short-circuits and renders a `403 Forbidden` JSON response:
     ```json
     {
       "error": "security_violation",
       "message": "The request body was blocked by the barrikade security layer.",
       "verdict": "block",
       "decision_layer": "llm",
       "confidence_score": 0.98
     }
     ```

### 2. Downstream Response Interception
* **Location**: Catch-all broker router `broker(request, target)` (in `src/routers/broker.py`)
* **Logic**:
  1. Once the outbound HTTP call finishes, Jentic Mini reads response bytes: `_upstream_body = await upstream_response.read()`.
  2. If `security_registry.has_plugins()` is active, decodes the body using `extract_text_from_payload`.
  3. Calls `security_registry.scan_response(text, upstream_host, status_code)`.
  4. If flagged as unsafe, logs a `policy_denied` trace and short-circuits with a `403 Forbidden` response-block verdict, completely preventing the third-party data from leaking to the agent or runner.

---

## Developer Guide: Adding a Custom Plugin

Creating and registering a new security plugin in Jentic Mini is incredibly straightforward:

### Step 1: Subclass `SecurityPlugin`
Create a new file (e.g., `src/security/my_security.py`) and implement the abstract methods.

### Step 2: Register the Plugin
Import and register your plugin in Jentic Mini's `lifespan` in `src/main.py`:

```python
# In src/main.py
from src.security.my_security import MySecurityPlugin

async def lifespan(app: FastAPI):
    # ...
    if MY_SECURITY_ENABLED:
        security_registry.register(MySecurityPlugin())
    # ...
```

---