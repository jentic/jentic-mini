/**
 * Vendor icon configuration shared across all monitor chart components.
 * Centralises colours, CDN icon URLs, and helper functions.
 */

export interface VendorConfig {
	bg: string;
	ring: string;
	text: string;
	iconUrl: string;
}

export const VENDOR_ICONS: Record<string, VendorConfig> = {
	slack: {
		bg: '#4A154B',
		ring: '#E01E5A',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/slack.svg',
	},
	github: {
		bg: '#24292f',
		ring: '#6e7681',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/github.svg',
	},
	sendgrid: {
		bg: '#1A82E2',
		ring: '#00B2E3',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v13/icons/sendgrid.svg',
	},
	hubspot: {
		bg: '#FF7A59',
		ring: '#FF5C35',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/hubspot.svg',
	},
	google: {
		bg: '#0F9D58',
		ring: '#34A853',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/googlesheets.svg',
	},
	jira: {
		bg: '#0052CC',
		ring: '#2684FF',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/jira.svg',
	},
	zendesk: {
		bg: '#03363D',
		ring: '#17494D',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/zendesk.svg',
	},
	airtable: {
		bg: '#18BFFF',
		ring: '#FCB400',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/airtable.svg',
	},
	mailchimp: {
		bg: '#FFE01B',
		ring: '#241C15',
		text: '#241C15',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/mailchimp.svg',
	},
	notion: {
		bg: '#000000',
		ring: '#505050',
		text: '#fff',
		iconUrl: 'https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/notion.svg',
	},
};

const DEFAULT_CONFIG: VendorConfig = {
	bg: '#6366f1',
	ring: '#818cf8',
	text: '#fff',
	iconUrl: '',
};

export function getVendorConfig(vendor: string): VendorConfig {
	return VENDOR_ICONS[vendor.toLowerCase()] ?? DEFAULT_CONFIG;
}

export function getInitials(name: string): string {
	return name
		.replace(/\s*API\s*/i, '')
		.split(/[\s\-_]+/)
		.slice(0, 2)
		.map((w) => w[0]?.toUpperCase() || '')
		.join('');
}

/** Inverts black Simple Icons SVGs to white. Reference as filter="url(#icon-to-white)". */
export const ICON_INVERT_FILTER_ID = 'icon-to-white';

/** No-op filter — icons stay black (for light-text vendors like Mailchimp). */
export const ICON_DARK_FILTER_ID = 'icon-keep-dark';

export function getIconFilterId(vendor: string): string {
	const config = getVendorConfig(vendor);
	return config.text === '#fff' ? ICON_INVERT_FILTER_ID : ICON_DARK_FILTER_ID;
}
