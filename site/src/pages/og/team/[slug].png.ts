import type { APIRoute } from "astro";
import { renderOgPng } from "../../../lib/og";
import { loadFixtures, teamGroups, teamSlug } from "../../../lib/data";

const PNG_HEADERS = {
  "Content-Type": "image/png",
  "Cache-Control": "public, max-age=31536000, immutable",
};

export function getStaticPaths() {
  const { groups } = loadFixtures();
  return teamGroups(groups).map(({ team, group }) => ({
    params: { slug: teamSlug(team) },
    props: { team, group },
  }));
}

export const GET: APIRoute = async ({ props }) => {
  const { team, group } = props as { team: string; group: string };
  const png = await renderOgPng({
    eyebrow: `World Cup 2026 · Group ${group}`,
    title: team,
    subtitle: "Fixtures · model win probabilities · value edges vs the market · team news.",
  });
  return new Response(new Uint8Array(png), { headers: PNG_HEADERS });
};
