import { http, HttpResponse } from 'msw'

/**
 * Default "happy path" MSW handlers.
 *
 * Relative paths work because OpenAPI.BASE is '' (empty string) and
 * the hand-written fetchJson() also uses relative URLs.
 * If BASE is ever set to an absolute URL, update these to match.
 */
export const handlers = [
  // ── Auth & health ───────────────────────────────────────────────
  http.get('/health', () =>
    HttpResponse.json({ status: 'ok' }),
  ),

  http.get('/user/me', () =>
    HttpResponse.json({ logged_in: true, username: 'admin', role: 'admin' }),
  ),

  http.post('/user/login', () =>
    HttpResponse.json({ logged_in: true, username: 'admin' }),
  ),

  http.get('/version', () =>
    HttpResponse.json({ current: '0.3.0', latest: '0.3.0' }),
  ),

  // ── Dashboard data ──────────────────────────────────────────────
  http.get('/apis', () =>
    HttpResponse.json({ data: [], total: 0, page: 1 }),
  ),

  http.get('/toolkits', () => HttpResponse.json([])),

  http.get('/workflows', () => HttpResponse.json([])),

  http.get('/traces', () =>
    HttpResponse.json({ traces: [], total: 0 }),
  ),

  // ── Toolkit detail ──────────────────────────────────────────────
  http.get('/toolkits/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      name: 'Test Toolkit',
      description: 'A test toolkit',
      suspended: false,
      simulate: false,
      disabled: false,
      credential_count: 0,
      key_count: 0,
      credentials: [],
    }),
  ),

  http.get('/toolkits/:id/keys', () =>
    HttpResponse.json({ keys: [] }),
  ),

  http.get('/toolkits/:id/access-requests', () =>
    HttpResponse.json([]),
  ),

  http.get('/toolkits/:id/credentials', () =>
    HttpResponse.json([]),
  ),

  // ── Credentials ─────────────────────────────────────────────────
  http.get('/credentials', () =>
    HttpResponse.json({ data: [], total: 0 }),
  ),

  http.get('/credentials/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      label: 'Test Credential',
      api_id: 'test-api',
      auth_type: 'bearer',
    }),
  ),

  // ── Search ──────────────────────────────────────────────────────
  http.get('/search', () => HttpResponse.json([])),

  // ── Catalog ─────────────────────────────────────────────────────
  http.get('/catalog', () => HttpResponse.json([])),
  http.get('/catalog/:id', () =>
    HttpResponse.json({ id: 'test-api', name: 'Test API' }),
  ),

  // ── Default API key ─────────────────────────────────────────────
  http.post('/default-api-key/generate', () =>
    HttpResponse.json({ key: 'jntc_test_key_abc123' }),
  ),

  // ── User creation ───────────────────────────────────────────────
  http.post('/user/create', () =>
    HttpResponse.json({ username: 'admin' }),
  ),
]
