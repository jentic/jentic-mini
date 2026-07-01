/**
 * Dashboard MSW handlers + fixtures.
 *
 * Dashboard has no endpoint of its own — it composes four EXISTING list
 * endpoints owned by other domains:
 *   GET /agents?status=pending      — agents awaiting approval
 *   GET /events?requires_action=true — actionable alerts
 *   GET /executions                 — recent activity / success rate
 *   GET /apis                       — registered API count
 *
 * These are NOT gap-filling mocks (the endpoints are real — verified against
 * the running backend); they exist so Dashboard's overview renders in Mode A
 * and in component tests. At full integration the real backend serves these
 * paths. In Mode A, several of these paths (notably `/agents`) are ALSO
 * registered by sibling modules in the root table, and MSW v2 resolves
 * FIRST-MATCH-WINS — and `...dashboardHandlers` is spread AFTER the siblings,
 * so a sibling can win `/agents` here. Tests therefore drive specific states
 * with `worker.use(...)` (which PREPENDS, so it always wins). See the
 * `seedDashboard()` helper in DashboardPage.test.tsx.
 *
 * Registered additively in src/mocks/handlers.ts. Shapes mirror the generated
 * response models so the typed client deserializes them unchanged.
 */
import { http, HttpResponse } from 'msw';

const now = Date.now();
const minutesAgo = (m: number) => new Date(now - m * 60_000).toISOString();

export const dashboardPendingAgents = [
	{
		id: 'agent_1',
		name: 'invoice-bot',
		description: 'Reconciles invoices nightly',
		status: 'pending',
		registered_by: 'user_1',
		created_at: minutesAgo(12),
	},
	{
		id: 'agent_2',
		name: 'support-triage',
		description: null,
		status: 'pending',
		registered_by: 'user_1',
		created_at: minutesAgo(90),
	},
];

export const dashboardActionableEvents = [
	{
		_links: { self: '/events/evt_1' },
		acknowledged: false,
		created_at: minutesAgo(5),
		detail: 'Stripe credential rejected 3 calls',
		event_id: 'evt_1',
		requires_action: true,
		severity: 'error',
		summary: 'Credential failing',
		type: 'credential.error',
	},
	{
		_links: { self: '/events/evt_2' },
		acknowledged: false,
		created_at: minutesAgo(40),
		detail: null,
		event_id: 'evt_2',
		requires_action: true,
		severity: 'warning',
		summary: 'Rate limit approaching',
		type: 'execution.rate_limit',
	},
];

export const dashboardExecutions = [
	{
		_links: { self: '/executions/exec_1' },
		created_at: minutesAgo(2),
		duration_ms: 142,
		execution_id: 'exec_1',
		http_status: 200,
		operation_id: 'charges/create',
		started_at: minutesAgo(2),
		status: 'completed',
		toolkit_id: 'payments',
		trace_id: 'trace_1',
	},
	{
		_links: { self: '/executions/exec_2' },
		created_at: minutesAgo(8),
		duration_ms: 87,
		execution_id: 'exec_2',
		http_status: 500,
		operation_id: 'repos/get',
		started_at: minutesAgo(8),
		status: 'failed',
		toolkit_id: 'github',
		trace_id: 'trace_2',
	},
	{
		_links: { self: '/executions/exec_3' },
		created_at: minutesAgo(15),
		duration_ms: 203,
		execution_id: 'exec_3',
		http_status: 200,
		operation_id: 'messages/send',
		started_at: minutesAgo(15),
		status: 'completed',
		toolkit_id: 'slack',
		trace_id: 'trace_3',
	},
];

export const dashboardApis = [
	{
		api: { vendor: 'stripe', name: 'stripe-api', version: '2024-01-01', host: 'stripe.com' },
		display_name: 'Stripe',
		description: 'Payments APIs.',
		icon_url: null,
		current_revision_id: 'rev_1',
		revision_count: 1,
		operation_count: 412,
		security_schemes: ['bearer'],
		created_at: minutesAgo(5000),
		updated_at: minutesAgo(100),
		_links: { self: '/apis/stripe/stripe-api/2024-01-01' },
	},
	{
		api: { vendor: 'github', name: 'github-api', version: '1.1.4', host: 'github.com' },
		display_name: 'GitHub',
		description: 'GitHub REST API.',
		icon_url: null,
		current_revision_id: 'rev_2',
		revision_count: 1,
		operation_count: 900,
		security_schemes: ['bearer'],
		created_at: minutesAgo(5000),
		updated_at: minutesAgo(200),
		_links: { self: '/apis/github/github-api/1.1.4' },
	},
];

interface DashboardAccessRequestItem {
	id: string;
	resource_type: string;
	action: string;
	status: string;
	resource_id?: string | null;
	to_type?: string | null;
	to_id?: string | null;
	rules?: Record<string, unknown>[] | null;
	decision_reason: string | null;
	decided_at?: string | null;
	decided_by?: string | null;
}
interface DashboardAccessRequest {
	id: string;
	actor_id: string;
	status: string;
	reason: string | null;
	requested_by: string;
	approve_url: string;
	filed_at: string;
	expires_at: string;
	created_by: string;
	filer_owner_id: string | null;
	items: DashboardAccessRequestItem[];
}

export const dashboardPendingAccessRequests: DashboardAccessRequest[] = [
	{
		id: 'ar_dash_1',
		actor_id: 'invoice-bot',
		status: 'pending',
		reason: 'agent needs Stripe charges:write',
		requested_by: 'usr_admin_1',
		approve_url: 'https://app.example.test/access-requests/ar_dash_1',
		filed_at: minutesAgo(7),
		expires_at: minutesAgo(-1440),
		created_by: 'usr_admin_1',
		filer_owner_id: null,
		items: [
			{
				id: 'ari_dash_1',
				resource_type: 'toolkit',
				action: 'use',
				status: 'pending',
				decision_reason: null,
			},
			{
				id: 'ari_dash_2',
				resource_type: 'credential',
				action: 'bind',
				to_type: 'toolkit',
				to_id: 'tk_stripe',
				status: 'pending',
				decision_reason: null,
				rules: [
					{
						effect: 'allow',
						methods: ['POST'],
						operations: ['charges/create', 'charges/capture', 'refunds/create'],
					},
					{ effect: 'deny', methods: ['DELETE'] },
				],
			},
			{
				id: 'ari_dash_scope',
				resource_type: 'scope',
				action: 'grant',
				resource_id: 'capabilities:execute',
				status: 'pending',
				decision_reason: null,
			},
		],
	},
	{
		id: 'ar_dash_2',
		actor_id: 'support-triage',
		status: 'pending',
		reason: 'read-only GitHub access',
		requested_by: 'usr_admin_1',
		approve_url: 'https://app.example.test/access-requests/ar_dash_2',
		filed_at: minutesAgo(55),
		expires_at: minutesAgo(-1440),
		created_by: 'usr_admin_1',
		filer_owner_id: null,
		items: [
			{
				id: 'ari_dash_3',
				resource_type: 'toolkit',
				action: 'use',
				status: 'pending',
				decision_reason: null,
			},
		],
	},
];

export const dashboardHandlers = [
	http.get('/agents', ({ request }) => {
		const status = new URL(request.url).searchParams.get('status');
		const data = status === 'pending' ? dashboardPendingAgents : [];
		return HttpResponse.json({ data, has_more: false, next_cursor: null });
	}),

	http.get('/access-requests', ({ request }) => {
		const url = new URL(request.url);
		const status = url.searchParams.get('status');
		// The Dashboard card only ever asks for the org-wide pending queue. An
		// actor-scoped query (`actor_id=…`, the per-actor detail card #619) or any
		// non-pending filter is not ours — fall through to the shared rail handler
		// instead of shadowing it with the wrong (org-wide) data.
		if (status !== 'pending' || url.searchParams.has('actor_id')) return undefined;
		return HttpResponse.json({
			data: dashboardPendingAccessRequests,
			has_more: false,
			next_cursor: null,
		});
	}),

	// The Dashboard card opens the shared AccessRequestDialog for its OWN
	// fixtures (`ar_dash_*`), which the rail handler doesn't know about — without
	// these the dialog's GET-by-id / :decide would 404 ("Access request not
	// found"). Scope strictly to `ar_dash_*` and fall through for everything else
	// so the rail handler still serves its own `ar_1…ar_4`.
	http.get('/access-requests/:id', ({ params }) => {
		const id = String(params.id);
		if (!id.startsWith('ar_dash_')) return undefined;
		const ar = dashboardPendingAccessRequests.find((r) => r.id === id);
		if (!ar) return new HttpResponse(null, { status: 404 });
		return HttpResponse.json(ar);
	}),

	http.post(/\/access-requests\/(ar_dash_[^/]+):decide$/, async ({ request }) => {
		const match = new URL(request.url).pathname.match(
			/\/access-requests\/(ar_dash_[^/]+):decide$/,
		);
		const id = match ? decodeURIComponent(match[1]) : '';
		const ar = dashboardPendingAccessRequests.find((r) => r.id === id);
		if (!ar) return new HttpResponse(null, { status: 404 });
		const body = (await request.json().catch(() => ({}))) as {
			items?: { item_id: string; decision: string; decision_reason?: string | null }[];
		};
		for (const decision of body.items ?? []) {
			const item = ar.items.find((i) => i.id === decision.item_id);
			if (item) {
				item.status = decision.decision;
				item.decision_reason = decision.decision_reason ?? null;
			}
		}
		const allDenied = ar.items.every((i) => i.status === 'denied');
		const allApproved = ar.items.every((i) => i.status === 'approved');
		ar.status = allDenied ? 'denied' : allApproved ? 'approved' : 'partially_approved';
		return HttpResponse.json(ar);
	}),

	http.get('/events', ({ request }) => {
		const requiresAction = new URL(request.url).searchParams.get('requires_action');
		// The Dashboard AlertsCard only consumes the actionable slice. The rail's
		// full backlog query (no `requires_action`) is not ours — fall through so
		// the shared rail handler serves it instead of returning an empty page.
		if (requiresAction !== 'true') return undefined;
		return HttpResponse.json({
			data: dashboardActionableEvents,
			has_more: false,
			next_cursor: null,
		});
	}),

	http.get('/executions', () =>
		HttpResponse.json({ data: dashboardExecutions, has_more: false, next_cursor: null }),
	),

	http.get('/apis', () =>
		HttpResponse.json({ data: dashboardApis, has_more: false, next_cursor: null }),
	),
];
