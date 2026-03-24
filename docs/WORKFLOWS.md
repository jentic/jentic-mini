# Workflows Guide

## What Is an Arazzo Workflow?

[Arazzo](https://spec.openapis.org/arazzo/latest.html) is an open standard (part of the OpenAPI Initiative) for defining multi-step API workflows. Key concepts:

- A workflow references one or more OpenAPI source specs
- Each **step** references a specific operation from those specs
- Steps can reference each other's outputs using runtime expressions: `$steps.{stepId}.outputs.{field}`
- Inputs can have default values
- The workflow defines its own input/output schema

Arazzo is to API workflows what OpenAPI is to individual operations.

---

## How JPE Executes Workflows

### Invocation

The canonical way to execute a workflow is via the broker, using the workflow's Capability ID:

```bash
curl -X POST http://localhost:8900/localhost/workflows/summarise-latest-topics \
  -H "X-Jentic-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"topic_count": 5}}'
```

The workflow Capability ID format: `POST/{jpe_hostname}/workflows/{slug}`

### Execution Flow

```
1. Client calls POST /{jpe_hostname}/workflows/{slug}
   (routed through the broker)

2. Broker detects the JPE hostname → internal dispatch
   (does NOT proxy to an external server)

3. dispatch_workflow(slug, inputs, collection_id) in workflows.py:

4. Read Arazzo spec from disk (workflows.arazzo_path)

5. Apply input schema defaults
   (fields with defaults are optional in the call body)

6. Preprocess Arazzo doc:
   For each sourceDescriptions entry:
     - Read the referenced OpenAPI spec
     - Rewrite servers[0].url → http://localhost:8900/{host}
     - Write to a temp file
   Update Arazzo sourceDescriptions to point to temp files

7. Spawn arazzo-runner subprocess with preprocessed spec

8. arazzo-runner executes each step:
   Step N:
     - Resolves operation from its source spec
     - Builds URL: http://localhost:8900/{host}/{path}
     - Calls local broker
     - Broker injects credentials, logs trace, forwards to upstream
     - Returns response to runner
     - Runner evaluates output expressions for next step

9. Runner returns: {status, outputs, step_outputs}

10. Write trace: executions row + execution_steps rows

11. Return to client:
    {
      "status": "success",
      "slug": "summarise-latest-topics",
      "outputs": { ... },
      "step_outputs": { "step1": {...}, "step2": {...} },
      "trace_id": "uuid",
      "_links": { "trace": "/traces/uuid" }
    }
```

### Error Response

On failure, JPE returns the upstream HTTP status and a structured error:

```json
{
  "status": "error",
  "slug": "my-workflow",
  "failed_step": {
    "step_id": "callOpenAI",
    "operation": "POST/api.openai.com/v1/chat/completions",
    "api_host": "api.openai.com",
    "http_status": 400,
    "detail": "max_tokens exceeds model limit"
  },
  "remediation": "Check the inputs for step callOpenAI. The upstream API returned a 400."
}
```

Auth failures (401/403) get a separate remediation hint pointing to the credentials flow.

---

## Working Example: Techpreneurs + OpenAI

**Location:** `/mnt/jentic-pe/src/specs/techpreneurs-openai.arazzo.json`

**Capability ID:** `POST/localhost/workflows/summarise-latest-topics`

**What it does:** Fetches the latest topics from the Techpreneurs Discourse forum, then asks OpenAI to summarise them.

**Steps:**

1. `GET techpreneurs.ie/latest.json` — Discourse list-topics endpoint (public, no auth required)
2. `POST api.openai.com/v1/chat/completions` — sends topics from step 1 to GPT-4 for summarisation

**Required credentials:**
- `api.openai.com` with scheme `BearerAuth` → bound to your collection

**Invocation:**
```bash
curl -X POST http://localhost:8900/localhost/workflows/summarise-latest-topics \
  -H "X-Jentic-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

(All inputs have defaults, so empty body works.)

**Known issue:** Discourse returns a large JSON payload. If the topics list is too large, the OpenAI step may fail with a 400 (token limit). See the transformation limitation below.

---

## Known Limitation: No Step-to-Step Data Transformation

Arazzo runtime expressions (`$steps.X.outputs.Y`) pass data **verbatim** between steps. There is no built-in filter, map, or transform primitive.

**Problem:** Step 1 might return a 500KB JSON response. Step 2 (e.g. OpenAI) only needs 3 fields from it. Passing the full payload causes:
- 400 errors from context-length limits
- Wasted tokens / latency

**Current workarounds:**
1. Design workflows where each step's output is naturally compact (e.g. APIs that return minimal data by default)
2. Use query parameters to limit response size (e.g. `?per_page=5` on list endpoints)
3. Pre-process data in workflow inputs before invocation

**Proper solution (not yet built):** A custom Arazzo extension for transformation steps, or a JPE-provided `transform` pseudo-operation at `/localhost/transform` that accepts data + a jq/JSONPath filter and returns the result.

---

## Registering a Workflow

### From a URL

```http
POST /import
X-Jentic-API-Key: {admin_key}
Content-Type: application/json

{
  "type": "workflow",
  "source": "url",
  "url": "https://raw.githubusercontent.com/org/repo/main/my-workflow.arazzo.json"
}
```

### Inline

```http
POST /import
{
  "type": "workflow",
  "source": "inline",
  "content": { ... arazzo document as JSON ... }
}
```

### From a local file

Place the file in `/mnt/jentic-pe/src/specs/` and use `"source": "file"` with a path.

After import, the workflow appears in:
- `GET /workflows` — list
- `GET /search?q=...` — BM25 search
- `GET /inspect/POST/localhost/workflows/{slug}` — inspect

---

## Inspecting a Workflow

```http
GET /inspect/POST/localhost/workflows/summarise-latest-topics
X-Jentic-API-Key: {key}
```

Returns:
```json
{
  "id": "POST/localhost/workflows/summarise-latest-topics",
  "type": "workflow",
  "name": "Summarise Latest Techpreneurs Topics",
  "description": "Fetches latest forum topics and returns an AI-generated summary.",
  "inputs": {
    "type": "object",
    "properties": {
      "topic_count": {"type": "integer", "default": 10}
    }
  },
  "steps": [
    {"step_id": "getTopics", "operation": "GET/techpreneurs.ie/latest.json"},
    {"step_id": "summarise", "operation": "POST/api.openai.com/v1/chat/completions"}
  ],
  "_links": {
    "execute": "/localhost/workflows/summarise-latest-topics"
  }
}
```

For LLM consumption, request `Accept: text/markdown` — returns the same info as formatted Markdown optimised for inclusion in a prompt.

---

## Listing Workflows

```http
GET /workflows
X-Jentic-API-Key: {key}
```

```http
GET /workflows/{slug}
```

---

## Arazzo File Format Overview

Minimal Arazzo document structure:

```json
{
  "arazzo": "1.0.0",
  "info": {
    "title": "My Workflow",
    "version": "1.0.0"
  },
  "sourceDescriptions": [
    {
      "name": "openai",
      "url": "https://raw.githubusercontent.com/.../openai-openapi.json",
      "type": "openapi"
    }
  ],
  "workflows": [
    {
      "workflowId": "my-workflow",
      "summary": "Does something useful",
      "inputs": {
        "type": "object",
        "properties": {
          "prompt": {"type": "string"}
        }
      },
      "steps": [
        {
          "stepId": "callOpenAI",
          "operationId": "createChatCompletion",
          "requestBody": {
            "contentType": "application/json",
            "payload": {
              "model": "gpt-4o",
              "messages": [{"role": "user", "content": "$inputs.prompt"}]
            }
          },
          "outputs": {
            "reply": "$response.body#/choices/0/message/content"
          }
        }
      ],
      "outputs": {
        "reply": "$steps.callOpenAI.outputs.reply"
      }
    }
  ]
}
```

Key points for JPE compatibility:
- `sourceDescriptions[].url` should point to a publicly accessible OpenAPI spec (JPE rewrites this to localhost at execution time)
- `operationId` must match an `operationId` in the referenced source spec
- Output expressions use JSONPath syntax after `#/`
- The workflow `workflowId` becomes the slug in JPE (kebab-cased if needed)
