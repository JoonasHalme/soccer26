import type { APIRoute } from "astro";

// Emitted at /robots.txt. Allows everything and advertises the sitemap with an
// ABSOLUTE URL (required by the Sitemap directive), derived from `site` so it
// tracks SITE_URL automatically.
export const GET: APIRoute = ({ site }) => {
  const base = site ? site.href.replace(/\/$/, "") : "";
  const lines = ["User-agent: *", "Allow: /"];
  if (base) lines.push(`Sitemap: ${base}/sitemap-index.xml`);
  return new Response(lines.join("\n") + "\n", {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
