/// <reference types="vite/client" />

interface ImportMetaEnv {
	/** Set to '1' to start the MSW worker in `npm run dev` (RUNBOOK Mode A). */
	readonly VITE_ENABLE_MSW?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
