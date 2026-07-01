/**
 * Minimum password length enforced client-side on the setup and change-password
 * forms. Mirrors the backend policy (the Pydantic `min_length` on the auth
 * request schemas and `MIN_PASSWORD_LENGTH` in the Python service / Go CLI).
 * The server is the source of truth; this is the UX-level pre-check so users
 * get instant feedback instead of a round-trip rejection.
 */
export const MIN_PASSWORD_LENGTH = 12;
