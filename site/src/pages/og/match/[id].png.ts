import type { APIRoute } from "astro";
import { renderOgPng } from "../../../lib/og";
import { loadFixtures, loadPredictions, publishedProbs } from "../../../lib/data";

const PNG_HEADERS = {
  "Content-Type": "image/png",
  "Cache-Control": "public, max-age=31536000, immutable",
};

const fmtKick = (k?: string) =>
  k ? new Date(k).toLocaleString("en-GB", {
    weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  }) + " UTC" : "Kick-off TBD";

export function getStaticPaths() {
  const { matches } = loadFixtures();
  const { predictions } = loadPredictions();
  const predById = new Map(predictions.map((p) => [p.match_id, p]));
  return matches.map((m) => ({
    params: { id: m.id },
    props: { match: m, pred: predById.get(m.id) ?? null },
  }));
}

export const GET: APIRoute = async ({ props }) => {
  const { match, pred } = props as any;
  const p = pred ? publishedProbs(pred) : undefined;  // blended "our call" (C1 consistency)
  const png = await renderOgPng({
    eyebrow: `World Cup 2026 · ${match.group ? `Group ${match.group}` : match.stage}`,
    title: `${match.home} vs ${match.away}`,
    bar: p
      ? { home: p.home, draw: p.draw, away: p.away, homeLabel: match.home, awayLabel: match.away }
      : undefined,
    subtitle: p ? undefined : "Model probabilities pending — fixtures & analysis on the page.",
    footer: `${fmtKick(match.kickoff)}${match.venue ? ` · ${match.venue}` : ""}`,
  });
  return new Response(new Uint8Array(png), { headers: PNG_HEADERS });
};
