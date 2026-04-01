import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { playwright } from '@vitest/browser-playwright';

export default defineConfig({
	plugins: [react(), tailwindcss()],
	optimizeDeps: {
		include: ['@jentic/arazzo-ui', 'react-dom/client'],
	},
	test: {
		browser: {
			enabled: true,
			provider: playwright(),
			instances: [{ browser: 'chromium' }],
		},
		globals: true,
		setupFiles: ['./src/__tests__/setup.ts'],
		include: ['src/**/*.test.{ts,tsx}'],
		coverage: {
			provider: 'istanbul',
			reporter: ['text', 'html', 'lcov'],
			include: ['src/components/ui/**', 'src/pages/**', 'src/hooks/**'],
			exclude: ['src/api/generated/**'],
		},
	},
});
