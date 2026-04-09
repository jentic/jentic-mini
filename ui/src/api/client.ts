import {
	OpenAPI,
	CatalogService,
	ToolkitsService,
	UserService,
	SearchService,
	ObserveService,
	InspectService,
} from './generated';

OpenAPI.WITH_CREDENTIALS = true;

export const api = {
	getMe: () => UserService.meUserMeGet(),
	login: (username: string, password: string) =>
		UserService.loginUserLoginPost({ requestBody: { username, password } }),
	logout: () => UserService.logoutUserLogoutPost(),
	createUser: (username: string, password: string) =>
		UserService.createUserUserCreatePost({ requestBody: { username, password } }),
	generateDefaultKey: () => UserService.generateDefaultKeyDefaultApiKeyGeneratePost(),
	listApis: (page = 1, limit = 20, source?: string, q?: string) => {
		const params = new URLSearchParams({ page: String(page), limit: String(limit) });
		if (source) params.set('source', source);
		if (q) params.set('q', q);
		return fetchJson<any>(`/apis?${params}`);
	},
	getApi: (apiId: string) => fetchJson<any>(`/apis/${apiId}`),
	getCatalogEntry: (apiId: string) => fetchJson<any>(`/catalog/${apiId}`),
	listOperations: (apiId: string, page = 1, limit = 50) =>
		CatalogService.listApiOperationsApisApiIdOperationsGet({ apiId, page, limit }),
	listOverlays: (apiId: string) => CatalogService.listOverlaysApisApiIdOverlaysGet({ apiId }),
	submitOverlay: (apiId: string, overlay: any, contributedBy?: string) =>
		CatalogService.submitOverlayApisApiIdOverlaysPost({
			apiId,
			requestBody: { overlay, contributed_by: contributedBy },
		}),
	importSpec: (sources: any[]) =>
		CatalogService.importSourcesImportPost({ requestBody: { sources } }),
	listCatalog: (q?: string, limit = 50, registeredOnly = false, unregisteredOnly = false) =>
		CatalogService.listCatalogCatalogGet({
			q: q ?? null,
			limit,
			registeredOnly,
			unregisteredOnly,
		}),
	refreshCatalog: () => CatalogService.refreshCatalogCatalogRefreshPost(),
	importFromCatalog: (apiId: string) => CatalogService.getCatalogEntryCatalogApiIdGet({ apiId }),
	listWorkflows: () => CatalogService.listWorkflowsWorkflowsGet({}),
	getWorkflow: (slug: string) => CatalogService.getWorkflowWorkflowsSlugGet({ slug }),
	addNote: (resource: string, note: string, type?: string) =>
		CatalogService.createNoteNotesPost({ requestBody: { resource, note, type: type ?? null } }),
	listNotes: (resource?: string, type?: string, limit = 50) =>
		CatalogService.listNotesNotesGet({ resource: resource ?? null, type: type ?? null, limit }),
	listToolkits: () => ToolkitsService.listToolkitsToolkitsGet(),
	getToolkit: (toolkitId: string) =>
		ToolkitsService.getToolkitToolkitsToolkitIdGet({ toolkitId }),
	createToolkit: (body: any) => ToolkitsService.createToolkitToolkitsPost({ requestBody: body }),
	updateToolkit: (toolkitId: string, body: any) =>
		ToolkitsService.patchToolkitToolkitsToolkitIdPatch({ toolkitId, requestBody: body }),
	deleteToolkit: (toolkitId: string) =>
		ToolkitsService.deleteToolkitToolkitsToolkitIdDelete({ toolkitId }),
	listKeys: (toolkitId: string) =>
		ToolkitsService.listToolkitKeysToolkitsToolkitIdKeysGet({ toolkitId }),
	createKey: (toolkitId: string, body: any) =>
		ToolkitsService.createToolkitKeyToolkitsToolkitIdKeysPost({ toolkitId, requestBody: body }),
	revokeKey: (toolkitId: string, keyId: string) =>
		ToolkitsService.revokeToolkitKeyToolkitsToolkitIdKeysKeyIdDelete({ toolkitId, keyId }),
	patchKey: (toolkitId: string, keyId: string, body: any) =>
		ToolkitsService.patchToolkitKeyToolkitsToolkitIdKeysKeyIdPatch({
			toolkitId,
			keyId,
			requestBody: body,
		}),
	listToolkitCredentials: (toolkitId: string) =>
		ToolkitsService.listToolkitCredentialsToolkitsToolkitIdCredentialsGet({ toolkitId }),
	bindCredential: (toolkitId: string, credentialId: string) =>
		ToolkitsService.addCredentialToToolkitToolkitsToolkitIdCredentialsPost({
			toolkitId,
			requestBody: { credential_id: credentialId },
		}),
	unbindCredential: (toolkitId: string, credentialId: string) =>
		ToolkitsService.removeCredentialFromToolkitToolkitsToolkitIdCredentialsCredentialIdDelete({
			toolkitId,
			credentialId,
		}),
	getPermissions: (toolkitId: string, credId: string) =>
		ToolkitsService.getCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsGet({
			toolkitId,
			credId,
		}),
	setPermissions: (toolkitId: string, credId: string, rules: any[]) =>
		ToolkitsService.setCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsPut({
			toolkitId,
			credId,
			requestBody: rules,
		}),
	patchPermissions: (toolkitId: string, credId: string, add: any[], remove: any[]) =>
		ToolkitsService.patchCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsPatch(
			{ toolkitId, credId, requestBody: { add, remove } },
		),
	listAccessRequests: (toolkitId: string, status?: string) =>
		ToolkitsService.listAccessRequestsToolkitsToolkitIdAccessRequestsGet({
			toolkitId,
			status: status ?? null,
		}),
	getAccessRequest: (toolkitId: string, reqId: string) =>
		ToolkitsService.getAccessRequestToolkitsToolkitIdAccessRequestsReqIdGet({
			toolkitId,
			reqId,
		}),
	createAccessRequest: (toolkitId: string, body: any) =>
		ToolkitsService.createAccessRequestToolkitsToolkitIdAccessRequestsPost({
			toolkitId,
			requestBody: body,
		}),
	approveAccessRequest: (toolkitId: string, reqId: string) =>
		ToolkitsService.approveAccessRequestToolkitsToolkitIdAccessRequestsReqIdApprovePost({
			toolkitId,
			reqId,
		}),
	denyAccessRequest: (toolkitId: string, reqId: string) =>
		ToolkitsService.denyAccessRequestToolkitsToolkitIdAccessRequestsReqIdDenyPost({
			toolkitId,
			reqId,
		}),
	listCredentials: (apiId?: string) =>
		fetchJson<any>(`/credentials${apiId ? `?api_id=${encodeURIComponent(apiId)}` : ''}`),
	createCredential: (body: any) =>
		fetchJson<any>('/credentials', {
			method: 'POST',
			body: JSON.stringify(body),
			headers: { 'Content-Type': 'application/json' },
		}),
	getCredential: (cid: string) => fetchJson<any>(`/credentials/${cid}`),
	updateCredential: (cid: string, body: any) =>
		fetchJson<any>(`/credentials/${cid}`, {
			method: 'PATCH',
			body: JSON.stringify(body),
			headers: { 'Content-Type': 'application/json' },
		}),
	deleteCredential: (cid: string) => fetchJson<any>(`/credentials/${cid}`, { method: 'DELETE' }),
	search: (q: string, n = 10) => SearchService.searchSearchGet({ q, n }),
	inspectCapability: (capabilityId: string, toolkitId?: string) =>
		InspectService.getCapabilityInspectCapabilityIdGet({ capabilityId, toolkitId }),
	listTraces: ({
		limit = 20,
		offset = 0,
		page,
		toolkit: _toolkit,
		workflow: _workflow,
	}: {
		limit?: number;
		offset?: number;
		page?: number;
		toolkit?: string;
		workflow?: string;
	} = {}) => {
		const effectiveOffset = page != null ? (page - 1) * (limit ?? 20) : (offset ?? 0);
		return ObserveService.listTracesTracesGet({ limit, offset: effectiveOffset });
	},
	getTrace: (traceId: string) => ObserveService.getTraceTracesTraceIdGet({ traceId }),
	listJobs: ({
		status,
		page = 1,
		limit = 20,
	}: { status?: string; page?: number; limit?: number } = {}) =>
		ObserveService.listJobsJobsGet({ status: status ?? null, page, limit }),
	getJob: (jobId: string) => ObserveService.getJobRouteJobsJobIdGet({ jobId }),
	cancelJob: (jobId: string) => ObserveService.cancelJobJobsJobIdDelete({ jobId }),
};

// --- OAuth Brokers (not in generated client — direct fetch) ---

/** Structured API error — carries the parsed JSON body when available. */
export class ApiError extends Error {
	constructor(
		public readonly status: number,
		public readonly statusText: string,
		/** Raw response body text */
		public readonly body: string,
		/** Parsed JSON body, if the response was JSON */
		public readonly data: Record<string, any> | null = null,
	) {
		super(data?.message ?? `${status} ${statusText}`);
		this.name = 'ApiError';
	}
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
	const res = await fetch(url, { credentials: 'include', ...init });
	if (!res.ok) {
		const body = await res.text().catch(() => '');
		let data: Record<string, any> | null = null;
		try { data = JSON.parse(body); } catch { /* not JSON */ }
		throw new ApiError(res.status, res.statusText, body, data);
	}
	const text = await res.text();
	return text ? JSON.parse(text) : (undefined as unknown as T);
}

export interface OAuthBroker {
	id: string;
	type: string;
	config: Record<string, any>;
	created_at?: string;
}

export interface OAuthAccount {
	id: string;
	broker_id: string;
	external_user_id: string;
	api_host: string;
	app_slug: string;
	account_id: string;
	label: string;
	healthy: boolean;
	synced_at: string;
}

export interface ConnectLinkResponse {
	connect_link_url: string;
	expires_at: number;
	broker_id: string;
	app: string;
}

export interface SyncResponse {
	accounts_synced: number;
}

export const oauthBrokers = {
	list: () => fetchJson<OAuthBroker[]>('/oauth-brokers'),
	get: (id: string) => fetchJson<OAuthBroker>(`/oauth-brokers/${encodeURIComponent(id)}`),
	create: (body: { id: string; type: string; config: Record<string, any> }) =>
		fetchJson<OAuthBroker>('/oauth-brokers', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
		}),
	delete: (id: string) =>
		fetch(`/oauth-brokers/${encodeURIComponent(id)}`, {
			method: 'DELETE',
			credentials: 'include',
		}).then((r) => {
			if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
		}),
	accounts: (id: string, externalUserId = 'default') =>
		fetchJson<OAuthAccount[]>(
			`/oauth-brokers/${encodeURIComponent(id)}/accounts?external_user_id=${encodeURIComponent(externalUserId)}`,
		),
	deleteAccount: (id: string, accountId: string) =>
		fetch(
			`/oauth-brokers/${encodeURIComponent(id)}/accounts/${encodeURIComponent(accountId)}`,
			{
				method: 'DELETE',
				credentials: 'include',
			},
		).then(async (r) => {
			if (!r.ok) {
				const e = await r.json().catch(() => ({}));
				throw new Error(e.detail || 'Failed to delete account');
			}
			return r.json();
		}),
	sync: (id: string, externalUserId = 'default') =>
		fetchJson<SyncResponse>(`/oauth-brokers/${encodeURIComponent(id)}/sync`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ external_user_id: externalUserId }),
		}),
	connectLink: (
		id: string,
		body: { app: string; external_user_id?: string; label: string; api_id?: string },
	) =>
		fetchJson<ConnectLinkResponse>(`/oauth-brokers/${encodeURIComponent(id)}/connect-link`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
		}),
	renameAccount: (brokerId: string, accountId: string, label: string) =>
		fetchJson<{ account_id: string; label: string }>(
			`/oauth-brokers/${encodeURIComponent(brokerId)}/accounts/${encodeURIComponent(accountId)}`,
			{
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ label }),
			},
		),
	reconnectLink: (brokerId: string, accountId: string) =>
		fetchJson<ConnectLinkResponse>(
			`/oauth-brokers/${encodeURIComponent(brokerId)}/accounts/${encodeURIComponent(accountId)}/reconnect-link`,
			{ method: 'POST', credentials: 'include' },
		),
	update: (id: string, config: Record<string, any>) =>
		fetchJson<OAuthBroker>(`/oauth-brokers/${encodeURIComponent(id)}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ config }),
		}),
};

export * from './generated';
