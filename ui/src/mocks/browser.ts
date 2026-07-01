import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

/**
 * Browser-side MSW worker. Used by:
 *  - the Vitest browser-mode test setup (src/__tests__/setup.ts), and
 *  - the dev server when VITE_ENABLE_MSW=1 (see src/main.tsx),
 * so the same handler table backs both component tests and a backendless
 * `npm run dev` (RUNBOOK Mode A).
 */
export const worker = setupWorker(...handlers);
