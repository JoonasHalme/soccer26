import type { APIRoute } from "astro";
import { renderOgPng } from "../../lib/og";

const PNG_HEADERS = {
  "Content-Type": "image/png",
  "Cache-Control": "public, max-age=31536000, immutable",
};

export const GET: APIRoute = async () => {
  const png = await renderOgPng({
    eyebrow: "FIFA World Cup 2026 · Transparent model",
    title: "Every probability, shown and graded in public.",
    subtitle: "Elo + Poisson model · value edges vs the de-vigged market · a public CLV track record.",
  });
  return new Response(new Uint8Array(png), { headers: PNG_HEADERS });
};
