import type { APIRoute } from "astro";
import {
  loadFixtures, loadPredictions, loadNews,
  allEdges, selectionLabel, pct1,
} from "../lib/data";

// Hand-rolled RSS 2.0 so the feed builds with no configured domain (Astro.site is
// unset until a deploy domain exists). Edge links are absolute once `site` is set,
// otherwise root-relative; news links are already absolute (BBC/Guardian/ESPN).
const xmlEscape = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
   .replace(/"/g, "&quot;").replace(/'/g, "&apos;");

const rfc822 = (iso?: string | null) => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toUTCString();
};

interface Item {
  title: string; link: string; guid: string;
  pubDate: string; description: string; category: string;
}

export const GET: APIRoute = async ({ site }) => {
  const base = site ? site.href.replace(/\/$/, "") : "";
  const { matches } = loadFixtures();
  const { predictions, generated_at } = loadPredictions();
  const { items: news } = loadNews();

  const items: Item[] = [];

  // Top value edges — the actionable content.
  const edges = allEdges(predictions, matches).slice(0, 20);
  for (const e of edges) {
    const price = e.best_odds ? ` @ ${e.best_odds.toFixed(2)}${e.best_book ? ` (${e.best_book})` : ""}` : "";
    items.push({
      title: `${e.home} vs ${e.away}: ${selectionLabel(e.selection, e.home, e.away)} +${pct1(e.edge_pct)}%${price}`,
      link: `${base}/matches/${e.match_id}`,
      guid: `edge-${e.match_id}-${e.selection}`,
      pubDate: rfc822(generated_at ?? e.kickoff),
      description:
        `Model ${(e.model_prob * 100).toFixed(1)}% vs the de-vigged market on ${e.market.replace(/_/g, " ")}. ` +
        `Edge +${pct1(e.edge_pct)}%${e.ev_pct != null ? `, EV ${e.ev_pct >= 0 ? "+" : ""}${pct1(e.ev_pct)}% at best price` : ""}. ` +
        `Kickoff ${e.kickoff ? new Date(e.kickoff).toUTCString() : "TBD"}. Analysis, not advice.`,
      category: "Value edge",
    });
  }

  // Tagged team news.
  for (const n of news.slice(0, 20)) {
    // Defence-in-depth: only emit http(s) links (feed URLs are third-party).
    const safeUrl = /^https?:\/\//i.test(n.url) ? n.url : base || "/";
    items.push({
      title: `${n.title}${n.teams.length ? ` (${n.teams.join(", ")})` : ""}`,
      link: safeUrl,
      guid: `news-${n.id}`,
      pubDate: rfc822(n.published_at),
      description: n.summary || n.title,
      category: n.is_injury_related ? "Team news · injury" : "Team news",
    });
  }

  const lastBuild = rfc822(generated_at) || new Date(0).toUTCString();
  const itemsXml = items.map((it) => `
    <item>
      <title>${xmlEscape(it.title)}</title>
      <link>${xmlEscape(it.link)}</link>
      <guid isPermaLink="false">${xmlEscape(it.guid)}</guid>
      ${it.pubDate ? `<pubDate>${it.pubDate}</pubDate>` : ""}
      <category>${xmlEscape(it.category)}</category>
      <description>${xmlEscape(it.description)}</description>
    </item>`).join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Soccer 26 — World Cup 2026 value edges &amp; team news</title>
    <link>${xmlEscape(base || "/")}</link>
    <description>New model value edges (vs the de-vigged market) and tagged team news for the 2026 World Cup. Transparent analysis, not betting advice.</description>
    <language>en</language>
    <lastBuildDate>${lastBuild}</lastBuildDate>
    <generator>soccer26</generator>${itemsXml}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
};
