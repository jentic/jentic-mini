// TypeScript types derived from OpenAPI spec

export interface UserOut {
  logged_in: boolean
  username?: string | null
  status?: string
}

export interface HealthOut {
  status: string
  default_key_claimed?: boolean
  setup_url?: string | null
  [key: string]: unknown
}

export interface DefaultKeyOut {
  key: string
}

export interface ToolkitKeyOut {
  id: string
  name?: string | null
  prefix?: string | null
  allowed_ips?: string[] | null
  revoked?: boolean
  created_at?: number | null
}

export interface ToolkitKeyCreated extends ToolkitKeyOut {
  key: string
}

export interface KeyCreate {
  name?: string | null
  allowed_ips?: string[] | null
}

export interface CredentialBindingOut {
  credential_id: string
  label?: string | null
  api_id?: string | null
  scheme_name?: string | null
}

export interface ToolkitOut {
  id: string
  name: string
  description?: string | null
  created_at?: number | null
  simulate?: boolean
  disabled?: boolean
  keys: ToolkitKeyOut[]
  credentials: CredentialBindingOut[]
  permissions: Record<string, unknown>[]
  pending_requests?: number
}

export interface ToolkitCreate {
  name: string
  description?: string | null
  simulate?: boolean
  initial_key_label?: string | null
}

export interface ToolkitPatch {
  name?: string | null
  description?: string | null
  simulate?: boolean | null
  disabled?: boolean | null
}

export interface PermissionRule {
  effect: 'allow' | 'deny'
  methods?: string[] | null
  path?: string | null
  operations?: string[] | null
  _system?: boolean
}

export interface AccessRequestOut {
  id: string
  toolkit_id: string
  type: 'grant' | 'modify_permissions'
  payload: Record<string, unknown>
  status: 'pending' | 'approved' | 'denied'
  reason?: string | null
  description?: string | null
  approve_url?: string | null
  created_at?: number | null
  resolved_at?: number | null
  applied_effects?: string[] | null
}

export interface CredentialOut {
  id: string
  label: string
  api_id?: string | null
  scheme_name?: string | null
  created_at?: number | null
  updated_at?: number | null
}

export interface CredentialCreate {
  label: string
  api_id?: string | null
  auth_type?: 'bearer' | 'basic' | 'apiKey' | null
  identity?: string | null
  value: string
}

export interface CredentialPatch {
  label?: string | null
  api_id?: string | null
  auth_type?: 'bearer' | 'basic' | 'apiKey' | null
  identity?: string | null
  value?: string | null
}

export interface ApiOut {
  id: string
  name?: string | null
  description?: string | null
  base_url?: string | null
  version?: string | null
  operation_count?: number | null
  created_at?: number | null
  [key: string]: unknown
}

export interface ApiListPage {
  items?: ApiOut[]
  data?: ApiOut[]
  total?: number | null
  page?: number | null
  size?: number | null
}

export interface OperationOut {
  id?: string | null
  capability_id?: string | null
  method?: string | null
  path?: string | null
  summary?: string | null
  description?: string | null
  [key: string]: unknown
}

export interface OperationListPage {
  items: OperationOut[]
  total?: number | null
  page?: number | null
  size?: number | null
}

export interface SearchResult {
  capability_id?: string | null
  api_id?: string | null
  api_name?: string | null
  method?: string | null
  path?: string | null
  summary?: string | null
  description?: string | null
  score?: number | null
  registered?: boolean
  type?: 'operation' | 'workflow'
  [key: string]: unknown
}

export interface WorkflowOut {
  slug: string
  name?: string | null
  description?: string | null
  steps?: WorkflowStep[]
  inputs?: Record<string, unknown>
  involved_apis?: string[]
  [key: string]: unknown
}

export interface WorkflowStep {
  id: string
  operation?: string | null
  description?: string | null
  [key: string]: unknown
}

export interface TraceOut {
  id: string
  toolkit_id?: string | null
  toolkit_name?: string | null
  capability_id?: string | null
  workflow_slug?: string | null
  status?: string | null
  http_status?: number | null
  duration_ms?: number | null
  created_at?: number | null
  steps?: TraceStepOut[]
  request?: Record<string, unknown>
  response?: Record<string, unknown>
  error?: string | null
  [key: string]: unknown
}

export interface TraceStepOut {
  step_id?: string | null
  capability_id?: string | null
  http_status?: number | null
  duration_ms?: number | null
  output?: unknown
  error?: string | null
  [key: string]: unknown
}

export interface TraceListPage {
  items: TraceOut[]
  total?: number | null
  page?: number | null
  size?: number | null
}

export interface JobOut {
  id: string
  kind?: string | null
  toolkit_id?: string | null
  status?: 'pending' | 'running' | 'complete' | 'failed' | string
  result?: unknown
  error?: string | null
  upstream_job_url?: string | null
  created_at?: number | null
  updated_at?: number | null
  [key: string]: unknown
}

export interface JobListPage {
  items: JobOut[]
  total?: number | null
  page?: number | null
  size?: number | null
}

export interface ImportRequest {
  source: string
  type?: string | null
  [key: string]: unknown
}

export interface ImportOut {
  id?: string | null
  status?: string | null
  message?: string | null
  [key: string]: unknown
}

export interface NoteCreate {
  resource: string
  content: string
}

export interface NoteOut {
  id: string
  resource: string
  content: string
  created_at?: number | null
}

export interface OverlaySubmit {
  content: string
  contributor?: string | null
}

export interface OverlayOut {
  id: string
  status?: string | null
  contributor?: string | null
  created_at?: number | null
  [key: string]: unknown
}

export interface SchemeInput {
  scheme_name: string
  scheme_type?: string | null
  [key: string]: unknown
}

export interface CatalogEntry {
  id: string
  name?: string | null
  domain?: string | null
  description?: string | null
  registered?: boolean
  [key: string]: unknown
}

export interface PermissionsPatch {
  add?: PermissionRule[]
  remove?: PermissionRule[]
}

export interface UserCreate {
  username: string
  password: string
}
