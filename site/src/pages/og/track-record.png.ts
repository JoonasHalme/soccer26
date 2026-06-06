import type { APIRoute } from "astro";
import { renderOgPng } from "../../lib/og";

const PNG_HEADERS = {
  "Content-Type": "image/png",
  "Cache-Control": "public, max-age=31536000, immutable",
};

export const GET: APIRoute = async () => {
  const png = await renderOgPng({
    eyebrow: "Public track record · World Cup 2026",
    title: "Did we beat the market?",
    subtitle: "Every bet logged, settled against the result, and scored for closing-line value (CLV).",
  });
  return new Response(new Uint8Array(png), { headers: PNG_HEADERS });
};
