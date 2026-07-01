import { http, HttpResponse } from 'msw';

/**
 * Toolkits module MSW handlers (Mode A — mocked dev/e2e). Registered in
 * `src/mocks/handlers.ts` with one additive spread line. These mirror the REAL
 * `control` toolkit contract (verified against the live `/openapi.json`), so
 * the mocked surface matches what the repository tier expects from the backend.
 */
type MockToolkit = {
	toolkit_id: string;
	name: string;
	description: string | null;
	active: boolean;
	key_count: number;
	credential_count: number;
	permissions: Array<Record<string, unknown>>;
	created_at: string;
	updated_at: string | null;
};

const now = () => new Date().toISOString();

const toolkits: MockToolkit[] = [
	{
		toolkit_id: 'tk_demo_github',
		name: 'GitHub Tools',
		description: 'Issues, PRs, and repo automation for the support agent.',
		active: true,
		key_count: 2,
		credential_count: 1,
		permissions: [],
		created_at: '2026-05-01T10:00:00Z',
		updated_at: null,
	},
	{
		toolkit_id: 'tk_demo_billing',
		name: 'Billing (suspended)',
		description: 'Stripe + internal billing. Suspended pending review.',
		active: false,
		key_count: 1,
		credential_count: 2,
		permissions: [],
		created_at: '2026-04-12T08:30:00Z',
		updated_at: '2026-06-01T12:00:00Z',
	},
];

const keysByToolkit: Record<string, Array<Record<string, unknown>>> = {
	tk_demo_github: [
		{
			key_id: 'key_1',
			toolkit_id: 'tk_demo_github',
			label: 'CI runner',
			key_preview: 'jntc_live_ab12…',
			revoked: false,
			allowed_ips: null,
			last_used_at: '2026-06-18T09:00:00Z',
			created_at: '2026-05-01T10:05:00Z',
		},
	],
};

const bindingsByToolkit: Record<string, Array<Record<string, unknown>>> = {
	tk_demo_github: [
		{
			toolkit_id: 'tk_demo_github',
			credential_id: 'cred_gh_1',
			label: 'GitHub PAT',
			api_name: 'GitHub',
			api_vendor: 'github',
			credential_type: 'api_key',
			bound_at: '2026-05-01T10:10:00Z',
			permissions: [
				{ effect: 'allow', methods: ['GET'], path: '/repos/.*', _system: false },
				{
					effect: 'deny',
					methods: null,
					path: '/admin/.*',
					_system: true,
					_comment: 'system safety',
				},
			],
		},
	],
};

/**
 * Agents bound to each toolkit (reverse lookup, served by
 * `GET /toolkits/:id/agents`). Link/unlink in tests mutate this so the
 * Bound Agents section reflects changes after a mutation.
 */
const agentsByToolkit: Record<string, Array<Record<string, unknown>>> = {
	tk_demo_github: [
		{
			agent_id: 'agt_support_bot',
			agent_name: 'Support Bot',
			status: 'active',
			bound_at: '2026-05-02T09:00:00Z',
		},
	],
};

/** Workspace agents — the candidate list for the "Link agent" picker. */
const agents: Array<Record<string, unknown>> = [
	{
		id: 'agt_support_bot',
		name: 'Support Bot',
		status: 'active',
		registered_by: 'admin@local',
		created_at: '2026-04-01T09:00:00Z',
	},
	{
		id: 'agt_billing_bot',
		name: 'Billing Bot',
		status: 'active',
		registered_by: 'admin@local',
		created_at: '2026-04-05T09:00:00Z',
	},
	{
		id: 'agt_pending_bot',
		name: 'Pending Bot',
		status: 'pending',
		registered_by: 'admin@local',
		created_at: '2026-04-08T09:00:00Z',
	},
];

const find = (id: string) => toolkits.find((t) => t.toolkit_id === id);

export const toolkitsHandlers = [
	http.get('/toolkits', () =>
		HttpResponse.json({ data: toolkits, has_more: false, next_cursor: null }),
	),

	http.post('/toolkits', async ({ request }) => {
		const body = (await request.json()) as { name: string; description?: string | null };
		const toolkit: MockToolkit = {
			toolkit_id: `tk_${Math.random().toString(36).slice(2, 8)}`,
			name: body.name,
			description: body.description ?? null,
			active: true,
			key_count: 1,
			credential_count: 0,
			permissions: [],
			created_at: now(),
			updated_at: null,
		};
		toolkits.unshift(toolkit);
		return HttpResponse.json({ toolkit, api_key: 'jntc_live_mockplaintextkey_show_once' });
	}),

	http.get('/toolkits/:toolkitId', ({ params }) => {
		const toolkit = find(params.toolkitId as string);
		if (!toolkit) return new HttpResponse(null, { status: 404 });
		return HttpResponse.json(toolkit);
	}),

	http.patch('/toolkits/:toolkitId', async ({ params, request }) => {
		const toolkit = find(params.toolkitId as string);
		if (!toolkit) return new HttpResponse(null, { status: 404 });
		const body = (await request.json()) as Partial<MockToolkit>;
		if (body.name != null) toolkit.name = body.name;
		if (body.description !== undefined) toolkit.description = body.description ?? null;
		if (body.active != null) toolkit.active = body.active;
		toolkit.updated_at = now();
		return HttpResponse.json(toolkit);
	}),

	http.delete('/toolkits/:toolkitId', ({ params }) => {
		const toolkitId = params.toolkitId as string;
		const idx = toolkits.findIndex((t) => t.toolkit_id === toolkitId);
		if (idx < 0) return new HttpResponse(null, { status: 404 });
		toolkits.splice(idx, 1);
		// Mirror the backend cascade so reverse-lookup endpoints return 404 /
		// empty after the delete (keys, bindings, and reverse agent grants).
		delete keysByToolkit[toolkitId];
		delete bindingsByToolkit[toolkitId];
		delete agentsByToolkit[toolkitId];
		return new HttpResponse(null, { status: 204 });
	}),

	http.get('/toolkits/:toolkitId/keys', ({ params }) =>
		HttpResponse.json({
			data: keysByToolkit[params.toolkitId as string] ?? [],
			has_more: false,
		}),
	),

	http.post('/toolkits/:toolkitId/keys', async ({ params, request }) => {
		const toolkitId = params.toolkitId as string;
		const body = (await request.json()) as { label?: string | null };
		const key = {
			key_id: `key_${Math.random().toString(36).slice(2, 8)}`,
			toolkit_id: toolkitId,
			label: body.label ?? null,
			key_preview: 'jntc_live_new…',
			revoked: false,
			allowed_ips: null,
			last_used_at: null,
			created_at: now(),
		};
		keysByToolkit[toolkitId] = [...(keysByToolkit[toolkitId] ?? []), key];
		return HttpResponse.json({ key, api_key: 'jntc_live_freshmockplaintext_show_once' });
	}),

	http.patch('/toolkits/:toolkitId/keys/:keyId', async ({ params, request }) => {
		const list = keysByToolkit[params.toolkitId as string] ?? [];
		const key = list.find((k) => k.key_id === params.keyId);
		if (!key) return new HttpResponse(null, { status: 404 });
		const body = (await request.json()) as { revoked?: boolean | null; label?: string | null };
		if (body.revoked != null) key.revoked = body.revoked;
		if (body.label !== undefined) key.label = body.label ?? null;
		return HttpResponse.json(key);
	}),

	http.delete('/toolkits/:toolkitId/keys/:keyId', ({ params }) => {
		const toolkitId = params.toolkitId as string;
		keysByToolkit[toolkitId] = (keysByToolkit[toolkitId] ?? []).filter(
			(k) => k.key_id !== params.keyId,
		);
		return new HttpResponse(null, { status: 204 });
	}),

	http.get('/toolkits/:toolkitId/credentials', ({ params }) =>
		HttpResponse.json({
			data: bindingsByToolkit[params.toolkitId as string] ?? [],
			has_more: false,
		}),
	),

	http.post('/toolkits/:toolkitId/credentials', async ({ params, request }) => {
		const toolkitId = params.toolkitId as string;
		const body = (await request.json()) as { credential_id: string };
		const binding = {
			toolkit_id: toolkitId,
			credential_id: body.credential_id,
			label: body.credential_id,
			api_name: null,
			api_vendor: null,
			credential_type: null,
			bound_at: now(),
			permissions: [],
		};
		bindingsByToolkit[toolkitId] = [...(bindingsByToolkit[toolkitId] ?? []), binding];
		return HttpResponse.json(binding);
	}),

	http.delete('/toolkits/:toolkitId/credentials/:credentialId', ({ params }) => {
		const toolkitId = params.toolkitId as string;
		bindingsByToolkit[toolkitId] = (bindingsByToolkit[toolkitId] ?? []).filter(
			(b) => b.credential_id !== params.credentialId,
		);
		return new HttpResponse(null, { status: 204 });
	}),

	http.get('/toolkits/:toolkitId/credentials/:credentialId/permissions', ({ params }) => {
		const list = bindingsByToolkit[params.toolkitId as string] ?? [];
		const binding = list.find((b) => b.credential_id === params.credentialId);
		return HttpResponse.json({ data: (binding?.permissions as unknown[]) ?? [] });
	}),

	http.put(
		'/toolkits/:toolkitId/credentials/:credentialId/permissions',
		async ({ params, request }) => {
			const list = bindingsByToolkit[params.toolkitId as string] ?? [];
			const binding = list.find((b) => b.credential_id === params.credentialId);
			const rules = (await request.json()) as Array<Record<string, unknown>>;
			const withSystem = [
				...rules,
				{
					effect: 'deny',
					methods: null,
					path: '/admin/.*',
					_system: true,
					_comment: 'system safety',
				},
			];
			if (binding) binding.permissions = withSystem;
			return HttpResponse.json({ data: withSystem });
		},
	),

	// --- Agent bindings (reverse lookup + agent-side link/unlink) ---

	http.get('/toolkits/:toolkitId/agents', ({ params }) =>
		HttpResponse.json({
			data: agentsByToolkit[params.toolkitId as string] ?? [],
			has_more: false,
			next_cursor: null,
		}),
	),

	// Link: agent-side bind (POST /agents/:agentId/toolkits { toolkit_id }).
	http.post('/agents/:agentId/toolkits', async ({ params, request }) => {
		const agentId = params.agentId as string;
		const body = (await request.json()) as { toolkit_id: string };
		const toolkitId = body.toolkit_id;
		const agent = agents.find((a) => a.id === agentId);
		const list = agentsByToolkit[toolkitId] ?? [];
		if (agent && !list.some((a) => a.agent_id === agentId)) {
			agentsByToolkit[toolkitId] = [
				...list,
				{
					agent_id: agentId,
					agent_name: agent.name,
					status: agent.status,
					bound_at: now(),
				},
			];
		}
		return HttpResponse.json({
			agent_id: agentId,
			toolkit_id: toolkitId,
			bound_at: now(),
		});
	}),

	// Unlink: agent-side unbind (DELETE /agents/:agentId/toolkits/:toolkitId).
	http.delete('/agents/:agentId/toolkits/:toolkitId', ({ params }) => {
		const { agentId, toolkitId } = params as { agentId: string; toolkitId: string };
		agentsByToolkit[toolkitId] = (agentsByToolkit[toolkitId] ?? []).filter(
			(a) => a.agent_id !== agentId,
		);
		return new HttpResponse(null, { status: 204 });
	}),

	http.get('/audit', ({ request }) => {
		const url = new URL(request.url);
		const targetType = url.searchParams.get('target_type');
		const targetId = url.searchParams.get('target_id');
		if (targetType !== 'toolkit') {
			return HttpResponse.json({ data: [], has_more: false, next_cursor: null });
		}
		const data = [
			{
				id: 'aud_2',
				occurred_at: '2026-06-01T12:00:00Z',
				action: 'update',
				target_type: 'toolkit',
				target_id: targetId ?? 'tk_demo_github',
				actor_type: 'user',
				actor_id: 'admin@local',
				reason: 'suspended pending review',
			},
			{
				id: 'aud_1',
				occurred_at: '2026-05-01T10:00:00Z',
				action: 'create',
				target_type: 'toolkit',
				target_id: targetId ?? 'tk_demo_github',
				actor_type: 'user',
				actor_id: 'admin@local',
				reason: null,
			},
		];
		return HttpResponse.json({ data, has_more: false, next_cursor: null });
	}),
];
