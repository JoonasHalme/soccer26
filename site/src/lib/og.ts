/**
 * Build-time Open Graph card renderer: satori (HTML/CSS subset -> SVG with glyph
 * paths) -> resvg (SVG -> PNG). Fonts are vendored TTFs read from disk, so the
 * build stays fully offline. Cards are 1200x630 (the standard large-summary size).
 *
 * Team flags are remote (flagcdn) and fetching them at build would break offline
 * builds, so cards use the same monogram-chip fallback the site uses — on-brand
 * and dependency-free. Swapping in real flags is a future enhancement.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import satori from "satori";
import { html } from "satori-html";
import { Resvg } from "@resvg/resvg-js";

// process.cwd() is the `site/` directory at `astro build` (same assumption as
// data.ts). Resolving from cwd survives Vite bundling, where import.meta.url
// would point at a hashed chunk in dist/ and the relative font path would break.
const FONTS_DIR = path.join(process.cwd(), "src", "assets", "og-fonts");
const read = (f: string) => readFileSync(path.join(FONTS_DIR, f));

const FONTS = [
  { name: "Inter", data: read("Inter-Regular.ttf"), weight: 400 as const, style: "normal" as const },
  { name: "Inter", data: read("Inter-Bold.ttf"), weight: 700 as const, style: "normal" as const },
  { name: "Sora", data: read("Sora-Bold.ttf"), weight: 700 as const, style: "normal" as const },
];

const esc = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export interface OgBar {
  home: number; draw: number; away: number;
  homeLabel: string; awayLabel: string;
}
export interface OgOptions {
  eyebrow: string;
  title: string;
  subtitle?: string;
  bar?: OgBar;
  footer?: string;
}

const HOME = "#2bb6ff", DRAW = "#4a5278", AWAY = "#f0a52a", ACCENT = "#2fb672";

function barBlock(bar: OgBar): string {
  const pct = (n: number) => Math.round(n * 100);
  return `
    <div style="display:flex; flex-direction:column; gap:18px; margin-top:44px;">
      <div style="display:flex; height:30px; border-radius:999px; overflow:hidden; border:1px solid #262c4a;">
        <div style="display:flex; flex:${bar.home}; background:${HOME};"></div>
        <div style="display:flex; flex:${bar.draw}; background:${DRAW};"></div>
        <div style="display:flex; flex:${bar.away}; background:${AWAY};"></div>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:30px; font-weight:700;">
        <div style="display:flex; color:${HOME};">${esc(bar.homeLabel)} ${pct(bar.home)}%</div>
        <div style="display:flex; color:#9aa3c4;">Draw ${pct(bar.draw)}%</div>
        <div style="display:flex; color:${AWAY};">${esc(bar.awayLabel)} ${pct(bar.away)}%</div>
      </div>
    </div>`;
}

export async function renderOgPng(opts: OgOptions): Promise<Buffer> {
  const markup = html(`
    <div style="display:flex; flex-direction:column; width:1200px; height:630px; padding:64px 72px; background-color:#0b0e1a; background-image:radial-gradient(900px 500px at 0% 0%, rgba(31,224,122,0.16), transparent 60%), radial-gradient(800px 460px at 100% 0%, rgba(255,61,139,0.14), transparent 55%); color:#eef1fb; font-family:Inter;">
      <div style="display:flex; align-items:center;">
        <div style="display:flex; align-items:center; justify-content:center; width:56px; height:56px; border-radius:14px; background-color:${ACCENT}; color:#03210f; font-size:34px; font-weight:700; font-family:Sora;">26</div>
        <div style="display:flex; margin-left:18px; font-size:30px; font-weight:700; letter-spacing:-0.5px;">SOCCER 26</div>
        <div style="display:flex; flex:1;"></div>
        <div style="display:flex; font-size:24px; color:#6f78a0;">Analysis, not tips</div>
      </div>

      <div style="display:flex; flex:1; flex-direction:column; justify-content:center;">
        <div style="display:flex; font-size:28px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:${ACCENT};">${esc(opts.eyebrow)}</div>
        <div style="display:flex; margin-top:14px; font-size:74px; font-weight:700; font-family:Sora; letter-spacing:-2px; line-height:1.05;">${esc(opts.title)}</div>
        ${opts.subtitle ? `<div style="display:flex; margin-top:20px; font-size:34px; color:#9aa3c4; line-height:1.35;">${esc(opts.subtitle)}</div>` : ""}
        ${opts.bar ? barBlock(opts.bar) : ""}
      </div>

      <div style="display:flex; align-items:center; font-size:26px; color:#6f78a0; border-top:1px solid #262c4a; padding-top:24px;">
        <div style="display:flex;">${opts.footer ? esc(opts.footer) : "World Cup 2026 · transparent, calibration-first forecasting"}</div>
        <div style="display:flex; flex:1;"></div>
        <div style="display:flex; color:#9aa3c4;">soccer 26</div>
      </div>
    </div>
  `);

  const svg = await satori(markup, { width: 1200, height: 630, fonts: FONTS });
  const png = new Resvg(svg, { fitTo: { mode: "width", value: 1200 } }).render().asPng();
  return png;
}
