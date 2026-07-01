import { Client } from 'pg';

/**
 * Direct Postgres access for the one real-backend seam with NO public API:
 * assigning an agent's `owner_id`.
 *
 * Why this exists: approving an access request is gated by the backend
 * (`control/services/access_requests/service.py::_compute_evaluation`) on two
 * rules — the reviewer must NOT be the filer (`not_filer`) AND must own the
 * filing agent (`owns_filer`: reviewer.sub == request.filer_owner_id, where
 * filer_owner_id resolves to the agent's `owner_id`). A DCR-registered agent is
 * created with `owner_id = NULL` (admin/repos/agent_repo.py::create_dcr) and
 * there is no endpoint that sets it, so an admin can never satisfy `owns_filer`
 * for an agent-filed request through the public API alone. To exercise the REAL
 * happy-path approve (admin :decide → approved), we set the agent's owner to the
 * admin directly. Everything else in the flow — register, :approve, jwt-bearer
 * mint, file, :decide — is real and public.
 *
 * Portability: the DSN is env-driven. Defaults to the superuser the CI fixtures
 * (`make start-fixtures`) expose on :5432; locally point it at the isolated
 * :5433 instance via E2E_DB_* env. Superuser is used so the connection can write
 * the admin-schema `agents` table regardless of per-surface role grants.
 */
function dsnFromEnv(): string {
	if (process.env.E2E_DB_URL) return process.env.E2E_DB_URL;
	const host = process.env.E2E_DB_HOST ?? 'localhost';
	const port = process.env.E2E_DB_PORT ?? '5432';
	const user = process.env.E2E_DB_USER ?? 'postgres';
	const password = process.env.E2E_DB_PASSWORD ?? 'postgres';
	const name = process.env.E2E_DB_NAME ?? 'jentic';
	return `postgresql://${user}:${password}@${host}:${port}/${name}`;
}

async function withClient<T>(fn: (client: Client) => Promise<T>): Promise<T> {
	const client = new Client({ connectionString: dsnFromEnv() });
	await client.connect();
	try {
		return await fn(client);
	} finally {
		await client.end();
	}
}

/**
 * Set `admin.agents.owner_id` for a DCR-registered agent so an admin reviewer
 * satisfies the `owns_filer` rule. Parameterised — no string interpolation into
 * SQL. Throws if the agent row is not found (rowCount 0) so a silent no-op can't
 * mask a broken seed.
 */
export async function setAgentOwner(agentId: string, ownerId: string): Promise<void> {
	await withClient(async (client) => {
		const res = await client.query('UPDATE admin.agents SET owner_id = $1 WHERE id = $2', [
			ownerId,
			agentId,
		]);
		if (res.rowCount !== 1) {
			throw new Error(
				`setAgentOwner: expected to update exactly 1 row for agent ${agentId}, updated ${res.rowCount}`,
			);
		}
	});
}
