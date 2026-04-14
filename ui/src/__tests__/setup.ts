import '@testing-library/jest-dom/vitest';
import { worker } from './mocks/browser';
// Import client to ensure OpenAPI.BASE is set to '' before any tests run
import '@/api/client';

beforeAll(async () => {
	await worker.start({ onUnhandledRequest: 'warn' });
});

afterEach(() => {
	worker.resetHandlers();
	window.localStorage.clear();
	window.sessionStorage.clear();
});

afterAll(() => {
	worker.stop();
});
