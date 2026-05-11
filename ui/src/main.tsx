import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';
import '@/index.css';
// Side-effect: configures OpenAPI.BASE from <base href> and WITH_CREDENTIALS.
// Imported explicitly here (rather than relying on the App → pages graph) so
// the global stays initialised even if App's imports are code-split later.
import '@/api/client';
import { ApiError } from '@/api/generated/core/ApiError';

function isNonTransientError(error: unknown): boolean {
	if (error instanceof ApiError) return error.status === 401 || error.status === 403;
	if (error instanceof Error) return /^(401|403)\b/.test(error.message);
	return false;
}

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			retry: (failureCount, error) => {
				if (isNonTransientError(error)) return false;
				return failureCount < 2;
			},
		},
	},
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
	<React.StrictMode>
		<QueryClientProvider client={queryClient}>
			<App />
		</QueryClientProvider>
	</React.StrictMode>,
);
