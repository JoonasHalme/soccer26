import type { APIRoute } from "astro";
import { renderOgPng } from "../../../lib/og";
import { loadFixtures } from "../../../lib/data";

const PNG_HEADERS = {
  "Content-Type": "image/png",
  "Cache-Control": "public, max-age=31536000, immutable",
};

export function getStaticPaths() {
  const { groups } = loadFixtures();
  return Object.keys(groups).map((letter) => ({
    params: { id: letter.toLowerCase() },
    props: { letter, teams: groups[letter] ?? [] },
  }));
}

export const GET: APIRoute = async ({ props }) => {
  const { letter, teams } = props as { letter: string; teams: string[] };
  const png = await renderOgPng({
    eyebrow: "World Cup 2026 · Group stage",
    title: `Group ${letter}`,
    subtitle: teams.join(" · "),
    footer: "Standings · fixtures · value edges · team news",
  });
  return new Response(new Uint8Array(png), { headers: PNG_HEADERS });
};
