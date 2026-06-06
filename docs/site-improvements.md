# Site improvements — specialist panel (UX · frontend/a11y · product/IA)

Three specialists reviewed the built site (post P0 pass). Consolidated, de-duplicated,
ranked. Cross-referenced to backlog TASK-ids where they exist.

## Confirmed healthy
Strong, consistent design system; zero JS bundles (only ~21KB CSS); good no-JS
fallbacks (countdowns, filters); solid a11y basics (aria-labels, focus-visible,
reduced-motion); nice empty states on /bets and /groups.

## Quick wins (high impact ÷ low effort) — do first
1. **Render real labels in tables** (UX). `/bets` shows raw `match_id` and the
   match-detail edges/bets tables show raw `OVER_2_5`/`HOME`. `selectionLabel()` +
   "Home vs Away" already exist — pure plumbing. *Most "looks unfinished" issue.*
2. **Single edge-% formatter** (frontend H1). `index.astro`/`MatchCard`/`[id].astro`
   print raw `edge_pct` (`+11.21%`) while `/edges` uses `.toFixed(1)` (`+11.2%`) —
   visible drift on the same data. One shared `pct1()` formatter.
3. **Mobile nav** (UX/​TASK-017). 6 pills + brand have no mobile handling — they
   wrap and break the sticky header band. `flex-wrap:nowrap; overflow-x:auto` +
   44px tap targets is the minimum; a menu/bottom-bar is the fuller fix.
4. ✅ **Self-host fonts** (frontend M1) — **shipped 2026-06-06.** Inter + Sora now
   served via `@fontsource-variable/*` imports in `Base.astro`; dropped the Google
   Fonts `<link>` + 2 preconnects. Build emits 9 local woff2; `--font-sans`/
   `--font-display` point at the "Inter/Sora Variable" families.
5. **Remove `background-attachment: fixed`** (frontend M2) — *already mitigated:* it's
   gated to `@media (min-width:860px) and (hover:hover)`, so mobile/touch never pays
   the repaint cost. Left as-is (desktop parallax is intentional).
6. ✅ **`aria-pressed` on edges filter chips + `aria-live` status** (frontend M5) —
   **2026-06-06.** Confirmed already wired (chips toggle `aria-pressed`, `#edge-status`
   is `aria-live="polite"`); bumped chip tap targets to 44px min.
7. ✅ **Surface best-book price + non-colour marker** (product / M6) — **2026-06-06.**
   `BookmakerOdds.astro` best-price cells now carry a ★ glyph + `.sr-only` "(best
   price)" alongside the green highlight (no longer colour-only). (Dashboard/edges
   line-shopping surfacing beyond the match page still open.)

## Medium
8. ✅ **Dashboard reorder** (UX) — **2026-06-06.** `index.astro` now leads with the
   Matchday band → value edges → next up → news, with the empty bankroll/P&L cards
   moved below and given an empty-state line ("…fills in once the tournament starts").
9. ✅ **EV-longshot signalling on /edges** (UX) — **2026-06-06.** Amber `LONGSHOT`
   tag in the EV cell when `model_prob < 0.25` or best price ≥ 4.0; Stake column
   emphasised (accent-tinted) as the honest sizing signal.
10. ✅ **Calibration metric glosses** (UX) — **2026-06-06.** Plain-language subtitle
    under each headline metric (log-loss/RPS/accuracy/ECE) + `<abbr>` tooltips on the
    validation-table rows (incl. Brier).
11. ✅ **Chart text alternatives** (frontend M3/M4) — **2026-06-06.** Equity curve
    (`/bets`) and reliability diagram (`/calibration`) now have visually-hidden SR
    summaries + data tables; SVGs marked `aria-hidden`/`aria-describedby`. Both pages
    gained a scoped `.sr-only` utility.
12. ✅ **`bestBookPrices` unchecked cast** (frontend H2) — **2026-06-06.** Replaced the
    `key as keyof …` cast in `data.ts` with a typed `BOOK_OUTCOMES` accessor table
    (`get: (b: BookOdds) => …`); exported signature unchanged.
13. ✅ **`[id].astro` guard before `render()`** (frontend M7) — **2026-06-06.** Explicit
    `if (analysis) { …render… }` guard; the 32 analysis-less matches can't reach
    `render()`.
14. ✅ **De-duplicate the two stat-card rows on /bets** (UX#14) — **2026-06-06.** P/L &
    ROI kept once (richer summary row); CLV row trimmed to 3 cards (Avg CLV, beat-rate,
    CLV-rated) — no stat lost.

## New features the data already supports (product)
15. ✅ **Knockout BRACKET view** (split from TASK-028) — **shipped 2026-06-06.**
    `bracket.astro` now derives the full feeder tree from `fixtures.json`
    (`W<game_no>`/`L<game_no>` → match), lays every tie at its true bracket
    position, and links each feeder pair to the tie it feeds with deterministic
    SVG elbows (fixed-px geometry so connectors align exactly). Per-round colour
    accents, round headers, a 🏆 Champion apex node (fills from the Final result),
    SR-only linearised list, and the third-place play-off below. Builds clean
    (111 pages); verified visually in-browser.
16. **IA re-order / task-based nav** — e.g. Today · Value · Matches · Bracket ·
    Track record · Model. "Track record" reads as public proof; fixes
    dashboard/edges/matches overlap.
17. **Per-team / per-group landing pages** (TASK-025) — the only organic-discovery/SEO
    surface; every input (fixtures, flags, news, edges) exists. Raise priority.
18. **/methodology page + on-site prediction hash-ledger** (TASK-016 + TASK-021).
    Explainer copy already exists in fragments; `predictions.hash.json` already
    written — surfacing it is the cheapest trust artifact.
19. ✅ **Open-exposure / Kelly portfolio summary** on /edges — **shipped 2026-06-06.**
    `edges.astro` now leads with an exposure strip: open-edge count, total
    fractional-Kelly stake summed across all surfaced edges, and % of bankroll at
    risk (warn-coloured when >100%), with an honest caveat that it's the correlated
    *ceiling* — the universe to select from, not a portfolio to back wholesale.
20. ✅ **Injury flag on the matchday hero** — **shipped 2026-06-06.** `index.astro`
    badges a matchday row with an amber "✚ injury news" pill (incl. sr-only team
    names) when a tagged `is_injury_related` story touches either side.

## Blocked (ops prerequisite, not site code)
- **"Line moves / steam" view** needs closing snapshots — `fetch_odds.py --closing`
  has **not run on any fixture** (0 captured). Scheduling that capture also fills the
  currently-empty CLV record the business case depends on. Do the ops step first.

## Frontend correctness/quality debt (from the a11y/eng lens)
- **Python↔TS logic drift** (H3): `data.ts` re-implements Kelly + meanCI + the t-table.
  The t-table is **already truncated at df=20 vs df=30 in Python** — a real present
  divergence for 22–31 settled bets. Fix the table and add golden-fixture cross-checks
  (or emit stakes/CI from Python and have the site only display).
- `data.ts` is a 600-line grab-bag — natural home for the shared formatter; split later.
