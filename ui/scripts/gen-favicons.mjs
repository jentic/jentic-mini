// @ts-check
/**
 * Deterministic favicon / app-icon / social-image generator for Jentic One.
 *
 * Single source of truth: the Jentic glyph paths (`LOGO_ICON_PATHS`) copied
 * verbatim from `ui/src/shared/ui/Logo.tsx` — the in-app brand mark — so every
 * generated icon stays pixel-identical to the logo rendered in the app shell
 * (decision D1). No Figma round-trip, no hand-traced raster.
 *
 * Run:  npm run gen:favicons   (from ui/)
 *
 * Emits into ui/public/ (which Vite copies verbatim into dist/ → the Python
 * wheel under jentic_one/static/, see pyproject.toml force-include):
 *   - favicon.svg                    (prefers-color-scheme aware, authored by hand)
 *   - favicon.ico                    (16/32/48 multi-res fallback)
 *   - favicon-96x96.png              (transparent mint glyph)
 *   - apple-touch-icon.png           (180x180, OPAQUE #0E1A1D plate — iOS masks
 *                                     transparency badly)
 *   - web-app-manifest-192x192.png   (opaque plate, PWA install)
 *   - web-app-manifest-512x512.png   (opaque plate, PWA install)
 *   - icon-512-maskable.png          (glyph in ~80% safe zone for Android masks)
 *   - og-image.png                   (1200x630 social card)
 *
 * The colours, glyph paths and source viewBox below MUST stay in lockstep with
 * Logo.tsx / index.css; re-run this script whenever the brand mark changes.
 */

import { Buffer } from 'node:buffer';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { writeFile } from 'node:fs/promises';
import sharp from 'sharp';
import pngToIco from 'png-to-ico';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = resolve(__dirname, '..', 'public');

// Brand palette — kept in lockstep with ui/src/index.css.
const BRAND_DARK = '#0E1A1D'; // --primary-950 (background / plate)
const BRAND_MINT = '#A3CACC'; // --primary-300 (brand glyph)
const OG_TEXT_COLOR = '#FFFFFF'; // wordmark on the OG card (not a brand token)

// Glyph paths copied verbatim from LOGO_ICON_PATHS in Logo.tsx (showWord=false).
const LOGO_ICON_PATHS = [
	'M94.04,26.63c-2.28-.32-4.91,2.9-7.17,8.67-2.61,6.68-5.26,13.38-8.06,19.87l-.03.06-1.57,3.69h0s-.05.13-.05.13c-1.16,2.74-5,11.78-6.24,14.68-.82,1.94-1.7,3.8-2.65,5.59,0,0,0,0,0,.01h0s-.01.02-.02.03c-.65,1.24-1.37,2.39-2.15,3.4-5.36,6.93-12.54,8.78-17.79,9.07-7.89.13-18.36-3.07-22.73-14.86-2.07-5.36-2.58-11.83-2.41-18.05h36.34s-1.47,3.37-1.47,3.37l-.3.69-3.06.08c-2.66.07-5.24.04-7.93.16-2.38.11-4.62-.08-6.49,2.04-.74.84-1.23,1.86-1.49,2.95-.35,1.51-.15,2.63.59,4.45,1.52,3.38,4.63,5.4,8.33,5.4.11,0,.23,0,.34,0,2.09-.07,4.28-.8,6.08-2.14,1.59-1.19,2.78-3.02,3.71-5.05l2.33-5.85,14.87-35.07h0s0-.01,0-.01c.38-.96.76-1.92,1.14-2.88,0-.01,0-.02.01-.03.68-1.66,1.45-1.67,1.46-1.67,0,0,2.45-.61,7.67-.61,4.68,0,7.92.42,8.06.51.13.09.66.16.65,1.39Z',
	'M104.8,58.91h-.03l-1.96-6.2-.02-.06-2.06-6.51h0s-3.83-12.16-3.83-12.16c-.72-2.15-1.34-4.39-3.11-4.01-3.1.68-4.9,5.86-6.39,9.94-.36.97-.73,2.03-.93,3.16l.47.58,12.4,15.26.14.17h-16.88l-2.38-.02-.02.05-1.41,3.24-.3.7h27.65l-1.33-4.14ZM100.71,61.78h0s.01,0,.01,0h-.01Z',
];

// Source glyph viewBox from Logo.tsx ICON_VIEWBOX: "21.5 25.4 83.3 66.8".
const GLYPH = { x: 21.5, y: 25.4, w: 83.3, h: 66.8 };
const GLYPH_CX = GLYPH.x + GLYPH.w / 2; // 63.15
const GLYPH_CY = GLYPH.y + GLYPH.h / 2; // 58.8

/**
 * Build an SVG string that centres the glyph inside a `size`x`size` canvas.
 *
 * @param {object} opts
 * @param {number} opts.size            canvas edge in px
 * @param {string} opts.fill            glyph fill colour
 * @param {string} [opts.background]    plate colour; omit/transparent for none
 * @param {number} [opts.coverage]      fraction of the canvas the glyph spans
 *   (0..1). Tuned per variant: bare-glyph favicons run hot (~0.78-0.82) to stay
 *   legible at 16-96px; plated icons sit smaller (~0.62-0.64) to leave a margin
 *   around the glyph; the maskable icon is smallest (~0.46) so it stays inside
 *   the Android adaptive-icon safe zone after a circular/squircle mask.
 * @param {number} [opts.radius]        corner radius (px) when a background is drawn
 */
function glyphSvg({ size, fill, background, coverage = 0.74, radius = 0 }) {
	// Scale so the glyph's larger dimension fills `coverage` of the canvas.
	const scale = (size * coverage) / Math.max(GLYPH.w, GLYPH.h);
	const center = size / 2;
	const paths = LOGO_ICON_PATHS.map((d) => `<path d="${d}" fill="${fill}" />`).join('');
	const plate = background
		? `<rect width="${size}" height="${size}" rx="${radius}" ry="${radius}" fill="${background}" />`
		: '';
	return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${plate}<g transform="translate(${center} ${center}) scale(${scale}) translate(${-GLYPH_CX} ${-GLYPH_CY})">${paths}</g></svg>`;
}

/** Render an SVG string to a PNG buffer. */
async function svgToPng(svg) {
	return sharp(Buffer.from(svg)).png().toBuffer();
}

async function writePng(name, svg) {
	const buf = await svgToPng(svg);
	await writeFile(resolve(PUBLIC_DIR, name), buf);
	console.log(`  ✓ ${name}`);
}

async function main() {
	console.log('Generating Jentic One icon set into ui/public/ …');

	// Transparent mint glyph — small PNG fallback for the SVG favicon.
	await writePng('favicon-96x96.png', glyphSvg({ size: 96, fill: BRAND_MINT, coverage: 0.78 }));

	// Apple touch icon — OPAQUE dark plate, mint glyph (iOS masks transparency).
	await writePng(
		'apple-touch-icon.png',
		glyphSvg({ size: 180, fill: BRAND_MINT, background: BRAND_DARK, coverage: 0.62 }),
	);

	// PWA install icons — opaque dark plate.
	await writePng(
		'web-app-manifest-192x192.png',
		glyphSvg({ size: 192, fill: BRAND_MINT, background: BRAND_DARK, coverage: 0.64 }),
	);
	await writePng(
		'web-app-manifest-512x512.png',
		glyphSvg({ size: 512, fill: BRAND_MINT, background: BRAND_DARK, coverage: 0.64 }),
	);

	// Maskable icon — glyph kept inside the ~80% Android adaptive-icon safe zone
	// (so a circular/squircle mask never clips it), opaque plate edge-to-edge.
	await writePng(
		'icon-512-maskable.png',
		glyphSvg({ size: 512, fill: BRAND_MINT, background: BRAND_DARK, coverage: 0.46 }),
	);

	// favicon.ico — multi-resolution (16/32/48) from transparent mint glyph.
	const icoSizes = [16, 32, 48];
	const icoBuffers = await Promise.all(
		icoSizes.map((s) => svgToPng(glyphSvg({ size: s, fill: BRAND_MINT, coverage: 0.82 }))),
	);
	await writeFile(resolve(PUBLIC_DIR, 'favicon.ico'), await pngToIco(icoBuffers));
	console.log('  ✓ favicon.ico (16/32/48)');

	// Open Graph card — 1200x630 dark canvas, centred glyph + product wordmark.
	const ogW = 1200;
	const ogH = 630;
	const glyphScale = (ogH * 0.4) / Math.max(GLYPH.w, GLYPH.h);
	const og = `<svg xmlns="http://www.w3.org/2000/svg" width="${ogW}" height="${ogH}" viewBox="0 0 ${ogW} ${ogH}">
		<rect width="${ogW}" height="${ogH}" fill="${BRAND_DARK}" />
		<g transform="translate(${ogW / 2} ${ogH / 2 - 70}) scale(${glyphScale}) translate(${-GLYPH_CX} ${-GLYPH_CY})">
			${LOGO_ICON_PATHS.map((d) => `<path d="${d}" fill="${BRAND_MINT}" />`).join('')}
		</g>
		<text x="${ogW / 2}" y="${ogH / 2 + 120}" text-anchor="middle"
			font-family="Sora, 'Helvetica Neue', Arial, sans-serif" font-size="72" font-weight="600"
			fill="${OG_TEXT_COLOR}">Jentic One</text>
		<text x="${ogW / 2}" y="${ogH / 2 + 180}" text-anchor="middle"
			font-family="'Nunito Sans', 'Helvetica Neue', Arial, sans-serif" font-size="30" font-weight="400"
			fill="${BRAND_MINT}">The control plane for your agents' tools and credentials</text>
	</svg>`;
	await writePng('og-image.png', og);

	console.log('Done. favicon.svg is authored by hand (see ui/public/favicon.svg).');
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
