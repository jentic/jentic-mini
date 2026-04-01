/** @type {import('prettier').Options} */
export default {
	useTabs: true,
	tabWidth: 4,
	singleQuote: true,
	semi: true,
	trailingComma: 'all',
	printWidth: 100,
	plugins: ['prettier-plugin-tailwindcss'],
	tailwindFunctions: ['clsx'],
};
