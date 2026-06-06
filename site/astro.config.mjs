// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// The public site URL. Drives ABSOLUTE URLs for the sitemap, RSS feed, OG/Twitter
// cards, and canonical tags — all of which are broken/relative without it, costing
// social previews and search indexing.
//
// No domain yet: set the real URL via the SITE_URL env var at build time
// (`SITE_URL=https://yourdomain.com npm run build`) or replace PLACEHOLDER_SITE
// below. The build prints a warning while the placeholder is still in use so it
// can't ship to production unnoticed.
const PLACEHOLDER_SITE = 'https://soccer26.example.com';
const SITE_URL = process.env.SITE_URL || PLACEHOLDER_SITE;
if (SITE_URL === PLACEHOLDER_SITE) {
  // eslint-disable-next-line no-console
  console.warn(
    `\n[astro.config] SITE_URL not set — using placeholder ${PLACEHOLDER_SITE}.\n` +
    `  Set SITE_URL (or edit astro.config.mjs) once a domain exists, or sitemap/OG/RSS/canonical URLs will point at the placeholder.\n`,
  );
}

// https://astro.build/config
export default defineConfig({
  site: SITE_URL,
  integrations: [
    // Emits /sitemap-index.xml + /sitemap-0.xml across all 175 prerendered pages.
    sitemap(),
  ],
});
