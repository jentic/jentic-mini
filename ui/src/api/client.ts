import { OpenAPI } from './generated'
import { CatalogService, ToolkitsService, UserService, SearchService, ObserveService, CredentialsService, InspectService } from './generated'

OpenAPI.WITH_CREDENTIALS = true;

export const api = {
  getMe: () => UserService.meUserMeGet(),
  login: (username: string, password: string) => UserService.loginUserLoginPost({ requestBody: { username, password } }),
  logout: () => UserService.logoutUserLogoutPost(),
  createUser: (username: string, password: string) => UserService.createUserUserCreatePost({ requestBody: { username, password } }),
  generateDefaultKey: () => UserService.generateDefaultKeyDefaultApiKeyGeneratePost(),
  listApis: (page = 1, limit = 20, source?: string, q?: string) => CatalogService.listApisApisGet({ page, limit, source: source ?? null, q: q ?? null }),
  getApi: (apiId: string) => CatalogService.getApiApisApiIdGet({ apiId }),
  listOperations: (apiId: string, page = 1, limit = 50) => CatalogService.listApiOperationsApisApiIdOperationsGet({ apiId, page, limit }),
  declareScheme: (apiId: string, body: any) => CatalogService.submitSchemeApisApiIdSchemePost({ apiId, requestBody: body }),
  listOverlays: (apiId: string) => CatalogService.listOverlaysApisApiIdOverlaysGet({ apiId }),
  submitOverlay: (apiId: string, overlay: any, contributedBy?: string) => CatalogService.submitOverlayApisApiIdOverlaysPost({ apiId, requestBody: { overlay, contributed_by: contributedBy } }),
  importSpec: (sources: any[]) => CatalogService.importSourcesImportPost({ requestBody: { sources } }),
  listCatalog: (q?: string, limit = 50, registeredOnly = false, unregisteredOnly = false) => CatalogService.listCatalogCatalogGet({ q: q ?? null, limit, registeredOnly, unregisteredOnly }),
  refreshCatalog: () => CatalogService.refreshCatalogCatalogRefreshPost(),
  getCatalogEntry: (apiId: string) => CatalogService.getCatalogEntryCatalogApiIdGet({ apiId }),
  importFromCatalog: (apiId: string) => CatalogService.getCatalogEntryCatalogApiIdGet({ apiId }),
  listWorkflows: () => CatalogService.listWorkflowsWorkflowsGet(),
  getWorkflow: (slug: string) => CatalogService.getWorkflowWorkflowsSlugGet({ slug }),
  addNote: (resource: string, note: string, type?: string) => CatalogService.createNoteNotesPost({ requestBody: { resource, note, type: type ?? null } }),
  listNotes: (resource?: string, type?: string, limit = 50) => CatalogService.listNotesNotesGet({ resource: resource ?? null, type: type ?? null, limit }),
  listToolkits: () => ToolkitsService.listToolkitsToolkitsGet(),
  getToolkit: (toolkitId: string) => ToolkitsService.getToolkitToolkitsToolkitIdGet({ toolkitId }),
  createToolkit: (body: any) => ToolkitsService.createToolkitToolkitsPost({ requestBody: body }),
  updateToolkit: (toolkitId: string, body: any) => ToolkitsService.patchToolkitToolkitsToolkitIdPatch({ toolkitId, requestBody: body }),
  deleteToolkit: (toolkitId: string) => ToolkitsService.deleteToolkitToolkitsToolkitIdDelete({ toolkitId }),
  listKeys: (toolkitId: string) => ToolkitsService.listToolkitKeysToolkitsToolkitIdKeysGet({ toolkitId }),
  createKey: (toolkitId: string, body: any) => ToolkitsService.createToolkitKeyToolkitsToolkitIdKeysPost({ toolkitId, requestBody: body }),
  revokeKey: (toolkitId: string, keyId: string) => ToolkitsService.revokeToolkitKeyToolkitsToolkitIdKeysKeyIdDelete({ toolkitId, keyId }),
  patchKey: (toolkitId: string, keyId: string, body: any) => ToolkitsService.patchToolkitKeyToolkitsToolkitIdKeysKeyIdPatch({ toolkitId, keyId, requestBody: body }),
  listToolkitCredentials: (toolkitId: string) => ToolkitsService.listToolkitCredentialsToolkitsToolkitIdCredentialsGet({ toolkitId }),
  bindCredential: (toolkitId: string, credentialId: string) => ToolkitsService.addCredentialToToolkitToolkitsToolkitIdCredentialsPost({ toolkitId, requestBody: { credential_id: credentialId } }),
  unbindCredential: (toolkitId: string, credentialId: string) => ToolkitsService.removeCredentialFromToolkitToolkitsToolkitIdCredentialsCredentialIdDelete({ toolkitId, credentialId }),
  getPermissions: (toolkitId: string, credId: string) => ToolkitsService.getCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsGet({ toolkitId, credId }),
  setPermissions: (toolkitId: string, credId: string, rules: any[]) => ToolkitsService.setCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsPut({ toolkitId, credId, requestBody: rules }),
  patchPermissions: (toolkitId: string, credId: string, add: any[], remove: any[]) => ToolkitsService.patchCredentialPermissionsToolkitsToolkitIdCredentialsCredIdPermissionsPatch({ toolkitId, credId, requestBody: { add, remove } }),
  listAccessRequests: (toolkitId: string, status?: string) => ToolkitsService.listAccessRequestsToolkitsToolkitIdAccessRequestsGet({ toolkitId, status: status ?? null }),
  getAccessRequest: (toolkitId: string, reqId: string) => ToolkitsService.getAccessRequestToolkitsToolkitIdAccessRequestsReqIdGet({ toolkitId, reqId }),
  createAccessRequest: (toolkitId: string, body: any) => ToolkitsService.createAccessRequestToolkitsToolkitIdAccessRequestsPost({ toolkitId, requestBody: body }),
  approveAccessRequest: (toolkitId: string, reqId: string) => ToolkitsService.approveAccessRequestToolkitsToolkitIdAccessRequestsReqIdApprovePost({ toolkitId, reqId }),
  denyAccessRequest: (toolkitId: string, reqId: string) => ToolkitsService.denyAccessRequestToolkitsToolkitIdAccessRequestsReqIdDenyPost({ toolkitId, reqId }),
  listCredentials: (apiId?: string) => CredentialsService.listCredentialsCredentialsGet({ apiId: apiId ?? null }),
  createCredential: (body: any) => CredentialsService.createCredentialsPost({ requestBody: body }),
  getCredential: (cid: string) => CredentialsService.getCredentialCredentialsCidGet({ cid }),
  updateCredential: (cid: string, body: any) => CredentialsService.patchCredentialsCidPatch({ cid, requestBody: body }),
  deleteCredential: (cid: string) => CredentialsService.deleteCredentialsCidDelete({ cid }),
  search: (q: string, n = 10) => SearchService.searchSearchGet({ q, n }),
  inspectCapability: (capabilityId: string, toolkitId?: string) => InspectService.getCapabilityInspectCapabilityIdGet({ capabilityId, toolkitId }),
  listTraces: ({ limit = 20, offset = 0, page, toolkit: _toolkit, workflow: _workflow }: { limit?: number; offset?: number; page?: number; toolkit?: string; workflow?: string } = {}) => {
    const effectiveOffset = page != null ? (page - 1) * (limit ?? 20) : (offset ?? 0)
    return ObserveService.listTracesTracesGet({ limit, offset: effectiveOffset })
  },
  getTrace: (traceId: string) => ObserveService.getTraceTracesTraceIdGet({ traceId }),
  listJobs: ({ status, page = 1, limit = 20 }: { status?: string; page?: number; limit?: number } = {}) => ObserveService.listJobsJobsGet({ status: status ?? null, page, limit }),
  getJob: (jobId: string) => ObserveService.getJobRouteJobsJobIdGet({ jobId }),
  cancelJob: (jobId: string) => ObserveService.cancelJobJobsJobIdDelete({ jobId }),
}

export * from './generated'
