import { defineConfig, globalIgnores } from 'eslint/config';
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import pluginReact from 'eslint-plugin-react';
import pluginReactHooks from 'eslint-plugin-react-hooks';
import pluginImportX from 'eslint-plugin-import-x';
import pluginUnusedImports from 'eslint-plugin-unused-imports';
import pluginJsxA11y from 'eslint-plugin-jsx-a11y';
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';
import globals from 'globals';

export default defineConfig(
	js.configs.recommended,
	tseslint.configs.recommended,

	// ─── Main source rules ───────────────────────────────────────────────
	{
		files: ['**/*.{ts,tsx}'],
		plugins: {
			react: pluginReact,
			'react-hooks': pluginReactHooks,
			'import-x': pluginImportX,
			'unused-imports': pluginUnusedImports,
			'jsx-a11y': pluginJsxA11y,
		},
		languageOptions: {
			ecmaVersion: 'latest',
			sourceType: 'module',
			globals: {
				...globals.browser,
			},
			parserOptions: {
				ecmaFeatures: { jsx: true },
			},
		},
		settings: {
			react: { version: 'detect' },
		},
		rules: {
			// ── Import hygiene ──────────────────────────────────────────
			'import-x/no-duplicates': 'error',
			'import-x/order': [
				'error',
				{
					groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'],
					'newlines-between': 'never',
				},
			],
			'import-x/no-cycle': ['error', { ignoreExternal: true }],
			'import-x/no-self-import': 'error',
			'import-x/no-restricted-paths': [
				'error',
				{
					zones: [{ target: './src/components/**', from: './src/pages/**' }],
				},
			],
			'unused-imports/no-unused-imports': 'error',
			'no-restricted-imports': [
				'error',
				{
					patterns: [
						{
							group: ['../*'],
							message: 'Use @/ absolute imports instead of relative parent paths.',
						},
					],
				},
			],

			// ── React ───────────────────────────────────────────────────
			'react/react-in-jsx-scope': 'off',
			'react/prop-types': 'off',
			'react/jsx-pascal-case': 'error',
			'react/jsx-key': 'error',
			'react/jsx-no-target-blank': 'warn',
			'react/jsx-no-useless-fragment': 'warn',
			'react/jsx-curly-brace-presence': ['warn', { props: 'never', children: 'never' }],
			'react/no-children-prop': 'error',
			'react/no-danger-with-children': 'error',
			'react/no-danger': 'error',
			'react/no-array-index-key': 'warn',
			'react/button-has-type': 'error',
			'react/self-closing-comp': 'warn',
			'react/function-component-definition': [
				'error',
				{
					namedComponents: 'function-declaration',
					unnamedComponents: 'function-expression',
				},
			],
			'react-hooks/rules-of-hooks': 'error',
			'react-hooks/exhaustive-deps': 'warn',

			'no-restricted-syntax': [
				'warn',
				{
					selector:
						"JSXOpeningElement[name.name='a'][attributes] JSXAttribute[name.name='href'][value.value=/^\\/[^/]/]",
					message:
						'Use <Link> from react-router-dom for internal navigation instead of <a>.',
				},
			],

			// ── Accessibility ───────────────────────────────────────────
			'jsx-a11y/alt-text': 'error',
			'jsx-a11y/anchor-has-content': 'error',
			'jsx-a11y/anchor-is-valid': 'error',
			'jsx-a11y/click-events-have-key-events': 'warn',
			'jsx-a11y/no-static-element-interactions': 'warn',
			'jsx-a11y/label-has-associated-control': ['error', { depth: 3 }],

			// ── TypeScript ──────────────────────────────────────────────
			'@typescript-eslint/no-unused-vars': [
				'warn',
				{ argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
			],
			'@typescript-eslint/no-explicit-any': 'warn',
			'@typescript-eslint/no-non-null-assertion': 'warn',
			'@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],

			// ── General ─────────────────────────────────────────────────
			'no-console': ['warn', { allow: ['warn', 'error'] }],
			'no-unused-vars': 'off',
			'max-depth': ['warn', 4],
		},
	},

	// ─── App shell & page files — enforce UI component library usage ────
	{
		files: ['src/pages/**/*.{ts,tsx}', 'src/components/layout/**/*.{ts,tsx}'],
		rules: {
			'no-restricted-syntax': [
				'error',
				{
					selector:
						"JSXOpeningElement[name.name='a'][attributes] JSXAttribute[name.name='href'][value.value=/^\\/[^/]/]",
					message:
						'Use <Link> from react-router-dom for internal navigation instead of <a>.',
				},
				{
					selector: "JSXOpeningElement[name.name='button']",
					message: 'Use <Button> from @/components/ui instead of raw <button>.',
				},
				{
					selector: "JSXOpeningElement[name.name='input']",
					message: 'Use <Input> from @/components/ui instead of raw <input>.',
				},
				{
					selector: "JSXOpeningElement[name.name='select']",
					message: 'Use <Select> from @/components/ui instead of raw <select>.',
				},
				{
					selector: "JSXOpeningElement[name.name='textarea']",
					message: 'Use <Textarea> from @/components/ui instead of raw <textarea>.',
				},
			],
		},
	},

	// ─── Test files — relaxed rules ──────────────────────────────────────
	{
		files: ['**/__tests__/**', '**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}'],
		rules: {
			'no-console': 'off',
			'no-restricted-imports': 'off',
			'@typescript-eslint/no-explicit-any': 'off',
			'@typescript-eslint/no-non-null-assertion': 'off',
			'@typescript-eslint/consistent-type-imports': 'off',
			'react/function-component-definition': 'off',
			'react/button-has-type': 'off',
			'jsx-a11y/click-events-have-key-events': 'off',
			'jsx-a11y/no-static-element-interactions': 'off',
		},
	},

	// ─── E2E tests — lint checked but relaxed ────────────────────────────
	{
		files: ['e2e/**/*.{ts,tsx}'],
		rules: {
			'no-console': 'off',
			'no-restricted-imports': 'off',
			'@typescript-eslint/no-explicit-any': 'off',
			'@typescript-eslint/no-non-null-assertion': 'off',
			'@typescript-eslint/consistent-type-imports': 'off',
		},
	},

	// Prettier must be last to override formatting rules
	eslintPluginPrettierRecommended,

	// ─── Global ignores ──────────────────────────────────────────────────
	globalIgnores([
		'dist/',
		'node_modules/',
		'coverage/',
		'playwright-report/',
		'.vitest-attachments/',
		'src/api/generated/',
		'eslint.config.js',
		'vite.config.ts',
		'vitest.config.ts',
		'prettier.config.js',
		'playwright.config.ts',
		'playwright.docker.config.ts',
	]),
);
