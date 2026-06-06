# Front-end improvement plan — soccer26

A design/UX critique of the **shipped** Astro front-end (`site/src`), focused on
net-new visual, layout/IA, component, responsive, motion, a11y, density, and
"delight" wins. Everything already marked ✅ in `docs/site-improvements.md` and
`docs/backlog.md` (real labels, shared `pct1()`, self-hosted fonts, exposure strip,
calibration glosses, chart SR tables, bracket, outrights, OG cards, methodology
ledger, RG footer, etc.) is treated as done and **not** re-listed.

Each item: **what / why / where / effort (S<0.5d · M 0.5–2d · L>2d)**. Grouped
Quick wins → Medium → Larger. Opinionated and directly actionable.

The current design system is genuinely strong: cohesive dark blue-violet theme,
disciplined token use, tabular-nums everywhere, zero-JS-by-default, solid a11y
basics. The gaps below are mostly about *consistency at the edges, mobile table
behaviour, motion polish, and a few high-leverage hierarchy decisions* — not a
rebuild.

---

## Quick wins (high impact ÷ low effort)

### QW-1 — Add a skip-to-content link — S
- **What:** A visually-hidden `<a href="#main">Skip to content</a>` as the first
  focusable element, revealed on focus; give `<main>` an `id="main"`.
- **Why:** The sticky header has 9 nav pills (now in a horizontal scroller). A
  keyboard or screen-reader user must tab through all of them on every page before
  reaching content. This is the single most common a11y miss on an otherwise solid
  site, and it's ~10 lines.
- **Where:** `site/src/layouts/Base.astro` (top of `<body>`, `<main>` id, one CSS
  rule reusing the existing `.sr-only` pattern with a `:focus` reveal).
- **Effort:** S

### QW-2 — Horizontal-scroll nav has no affordance or active-into-view — S/M
- **What:** The primary nav is `overflow-x:auto` with the scrollbar hidden
  (`scrollbar-width:none`). On a phone there is **no visual cue** that pills 7–9
  (Outrights/Bets/Calibration/Methodology) exist off-screen, and the active pill
  isn't scrolled into view. Add (a) a right-edge fade mask (`mask-image` gradient)
  that disappears at scroll-end, and (b) a tiny inline script to
  `scrollIntoView({inline:'center'})` the `[aria-current="page"]` link on load.
- **Why:** Hidden-scrollbar nav is a known discoverability trap; users on
  `/methodology` currently land with the active pill clipped off the right edge and
  half the IA invisible. This is the most-used component on the site.
- **Where:** `site/src/layouts/Base.astro` (`.site-header nav` mask + a 6-line
  inline script). Respect `prefers-reduced-motion` for the scroll.
- **Effort:** S/M

### QW-3 — Match-detail edges table still prints raw market codes — S
- **What:** `selectionLabel()` is used for the *selection* on `matches/[id].astro`,
  but the dashboard "Biggest value edges" tiles and the matchday hero badge render
  raw `edge.selection` (e.g. `OVER_2_5`, `HOME`) with no humanisation, and the
  match-page "Bets on this match" + "Edges vs market" tables print the raw
  `b.market` / market code. Route all of these through `selectionLabel()` /
  a `marketLabel()` helper so no `OVER_2_5`/`BTTS_YES` ever reaches the UI.
- **Why:** `site-improvements.md` item #1 flagged raw codes as the top
  "looks unfinished" issue and fixed the *tables*, but the **dashboard edge tiles**
  (`index.astro` `.edge-sel`: `{edge.selection}`) and the **matchday badge**
  (`+{pct1}% {e.selection}`) still leak `HOME`/`OVER_2_5`. Same data, same bug, just
  in the highest-traffic surface.
- **Where:** `site/src/pages/index.astro` (`.edge-sel`, `.md-tail` badge),
  `site/src/lib/data.ts` (add `marketLabel()` next to `selectionLabel()`).
- **Effort:** S

### QW-4 — Newsletter renders a disabled dead form by default — S
- **What:** `Newsletter.astro` ships with `NEWSLETTER_ACTION = ""`, so the dashboard
  shows a greyed-out email box + disabled "Subscribe" button that does nothing. A
  disabled input the user can't interact with reads as broken, not "coming soon."
  When unconfigured, **hide the form entirely** and show a single confident RSS CTA
  button instead (or a "notify me" mailto). Only render the form when configured.
- **Why:** A non-functional form on the primary landing page actively erodes the
  "shipped and trustworthy" impression the whole positioning depends on. An honest
  RSS CTA is strictly better than a dead control.
- **Where:** `site/src/components/Newsletter.astro` (gate the `<form>` on
  `configured`; promote the RSS link to a real button in the stub case).
- **Effort:** S

### QW-5 — Standardise the "hero chips" + "hero" pattern into one component — S/M
- **What:** The hero scaffold (radial-gradient panel + `.eyebrow` + `h1` +
  `.hero-chips` with `.hero-chip` / `.hero-chip.accent`) is **copy-pasted with
  near-identical CSS** across `index`, `groups`, `bracket`, `outrights`, `team`,
  and `gp-hero`/`ou-hero`/`bk-hero` each redeclare the same `.hero-chip` rules.
  Extract a `<PageHero>` component (eyebrow, title, subtitle slot, chips array) and
  promote `.hero-chip` to global `Base.astro`.
- **Why:** Five divergent copies already drift (different paddings: 1.5/1.7/1.8rem,
  different gradient stops). Consolidation kills the drift, shrinks CSS, and makes
  future restyling one edit. Pure consistency/maintainability win with visible
  payoff (uniform hero rhythm).
- **Where:** new `site/src/components/PageHero.astro`; `Base.astro` (global
  `.hero-chip`); the 5 pages above.
- **Effort:** S/M

### QW-6 — Card grids jump from multi-column straight to 1-column — S
- **What:** `.cards-grid`, `.news-grid`, `.groups-grid` use
  `repeat(auto-fill, minmax(300–330px, 1fr))` but then `@media (max-width:720px)`
  forces `1fr`. Between ~640–720px you get an awkward single wide card while there's
  room for the auto-fill to keep 2. Drop the hard 720px override (auto-fill already
  collapses gracefully) or lower the minmax floor to ~280px so the transition is
  smooth, not stepped.
- **Why:** Tablet/large-phone landscape shows one stretched card with lots of dead
  horizontal space — looks unfinished. Letting `auto-fill` do its job is fewer lines
  *and* better.
- **Where:** `site/src/layouts/Base.astro` (`.cards-grid`), `index.astro`,
  `team/[slug].astro`, `groups.astro` (remove redundant 720px `1fr` overrides).
- **Effort:** S

### QW-7 — Stage-colour legend on /matches lacks R32→3RD parity — S
- **What:** The `/matches` legend lists Groups/R32/R16/QF/SF/Final but omits the
  **Third place** swatch even though that stage section renders below; and the
  legend dots aren't keyed to the same `--stage-*` tokens used by `StageChip`
  consistently (3RD uses `--stage-3rd`). Add the missing swatch and confirm token
  parity so the key actually explains every chip on the page.
- **Why:** A colour key that doesn't cover all the colours on the page is worse than
  none — it implies completeness it doesn't have.
- **Where:** `site/src/pages/matches/index.astro` (`.legend`).
- **Effort:** S

### QW-8 — Give SVG charts a non-`viewBox`-distorting aspect on mobile — S
- **What:** The equity curve (`bets.astro`) uses `viewBox="0 0 720 180"
  preserveAspectRatio="none"` with `width:100%; height:180px`. On a 360px phone the
  720-wide art is squashed to 2:1 horizontally, distorting stroke angles and making
  the dashed baseline look coarse. Either keep `preserveAspectRatio` default and let
  height scale, or reduce the viewBox width on narrow screens. (The reliability
  curve already does the right thing with `height:auto`.)
- **Why:** A distorted equity curve undercuts the "we measure honestly" message on
  the exact page that *is* the proof. Cheap fix, real polish.
- **Where:** `site/src/pages/bets.astro` (`.equity` svg + CSS).
- **Effort:** S

### QW-9 — Focus-visible radius bug on pill/round elements — S
- **What:** The global `:focus-visible` sets `border-radius:6px` on the **outline
  target itself**, which fights the 999px pill radius on nav links, chips, and
  stage chips (the focus ring corners don't match the element). Outlines don't need
  a radius override; drop it (or scope it) so the ring hugs round controls.
- **Why:** Small but visible: focus rings on the rounded nav pills currently show
  square-ish corners. A11y polish that the rest of the system clearly cares about.
- **Where:** `site/src/layouts/Base.astro` (`:focus-visible`).
- **Effort:** S

---

## Medium

### M-1 — Mobile dense-table strategy (TASK-023 is still open) — M
- **What:** The edges table (8 cols), bookmaker-odds table (up to 6 cols), and the
  full group table all rely on `.table-wrap { overflow-x:auto }`. Horizontal scroll
  inside a vertically-scrolling page is the weakest mobile pattern — users miss the
  Stake/EV columns entirely. Implement a card-collapse at `≤560px`: each row becomes
  a labelled mini-card (Match heading; Selection · Model · Edge · Best price · EV ·
  Stake as `label:value` rows). Drive it with `data-label` attributes + a
  `@media` `display:block` table reflow so no JS is needed.
- **Why:** Mobile is the betting segment; the edges table is the actionable
  centerpiece and currently its most important columns (EV, Kelly stake) are
  off-screen by default on a phone. This is the biggest remaining responsive gap.
- **Where:** `site/src/pages/edges.astro`, `site/src/components/BookmakerOdds.astro`,
  shared helper CSS (consider a global `.table--cards` modifier in `Base.astro`).
- **Effort:** M

### M-2 — `ProbBar` segments rely on colour + thin contrast for draw — M
- **What:** The win/draw/away segments are distinguished by blue/grey/amber only.
  The `role="img"` aria-label is good (TASK-027 partial), but: (a) the inline `%`
  text uses `color:#04130a` (near-black) on the **draw** segment whose grey
  `#565f86` background gives **failing contrast**; (b) there's no non-colour cue
  (the legend swatches are colour-only). Fix draw-segment text colour to the light
  `#eef1fb` it already special-cases in one place but not the inline label, and add
  a subtle pattern or a leading letter (H/D/A) inside each segment when wide enough.
- **Why:** The prob bar is the single most-repeated data-viz on the site (every
  match card + every match page). Contrast + colourblind redundancy here is high
  reach. TASK-027 is still open in the backlog.
- **Where:** `site/src/components/ProbBar.astro`, `MatchCard.astro` `.mc-bar`,
  `Base.astro` `.probbar` segment rules.
- **Effort:** M

### M-3 — Hierarchy: dashboard buries the actionable CTA below five sections — M
- **What:** The dashboard order is hero → matchday → biggest edges → next up → news
  → newsletter → bankroll → groups. That's a long scroll with **no primary
  action**. The hero's only CTA is "How it's calibrated →". Add a clear primary
  button row in/under the hero — "See all value edges →" (to `/edges`) and "Today's
  matches →" — so the landing page routes users to the centerpiece without scrolling.
  Consider demoting "Latest team news" below groups (it's the least decision-driving
  block but currently sits 4th).
- **Why:** The edges page is the product's reason to exist; the homepage should
  point at it in the first viewport. Right now the strongest action is a tiny text
  link among stat chips.
- **Where:** `site/src/pages/index.astro` (hero CTA row; section reorder).
- **Effort:** M

### M-4 — Empty-state inconsistency: dev-facing copy leaks to users — S/M
- **What:** Several empty states tell the *operator* to run Python:
  "populate `fixtures/fixtures.json`", "run `python model/predict.py`",
  "run `python model/fetch_odds.py …`", "run `python model/simulate.py`". These are
  build-time CLI instructions rendered into the **public** page. Replace the
  user-facing copy with a neutral "No data yet — check back once the tournament
  starts (11 Jun)" and move the operator hint into an HTML comment or a
  `import.meta.env.DEV`-gated block.
- **Why:** A public betting-analysis site that tells visitors to run
  `python model/predict.py` reads as a broken deploy, not a polished product. The
  `/edges`, `/outrights`, `/matches`, dashboard, and `/calibration` empty states all
  do this. (The `/bets` empty state has the same issue but is at least styled.)
- **Where:** `index.astro`, `edges.astro`, `matches/index.astro`, `outrights.astro`,
  `calibration.astro`, `bets.astro`.
- **Effort:** S/M

### M-5 — Tooltip bubble clips inside scroll/overflow containers — M
- **What:** `Tooltip.astro` positions its bubble with `position:absolute` relative
  to the inline term. On `/edges` and `/bets` the tooltips live inside prose, which
  is fine, but the same component used inside any `.table-wrap` (`overflow-x:auto`)
  or near the viewport top would be clipped. Also: it opens on `:focus-visible` only,
  so a **touch tap** (which doesn't trigger hover or focus-visible reliably) never
  reveals the definition on mobile. Add `tabindex` focus (already present) plus a
  click/tap toggle, and guard against top-edge clipping (flip below when near the top).
- **Why:** Jargon tooltips are a trust feature for newcomers; on mobile they
  currently can't be opened at all, which is exactly the audience that needs them.
- **Where:** `site/src/components/Tooltip.astro` (tap handling, edge-flip).
- **Effort:** M

### M-6 — Motion polish: standardise easing + add staged reveals — M
- **What:** Transitions are scattered and inconsistent (`0.12s`, `0.14s`, `0.15s`,
  `0.16s`, `0.3s`, mixed `ease`). Define `--ease`, `--dur-fast`, `--dur` tokens and
  use them. Then add one tasteful entrance: a subtle `@starting-style` /
  IntersectionObserver fade-up on card grids and stat rows (cheap, CSS-first,
  gated behind `prefers-reduced-motion`). The hover lifts (`translateY(-3px)`) are
  nice; the site has almost no *entrance* motion, which is the cheapest "feels
  alive" win.
- **Why:** Perceived quality. The hover micro-interactions are good but isolated;
  unifying timing and adding a restrained reveal lifts the whole site from "static
  and competent" to "crafted." Must stay subtle — this is a data/credibility product.
- **Where:** `Base.astro` (motion tokens + reduced-motion already handled), card
  components, stat rows. Replace ad-hoc durations across components.
- **Effort:** M

### M-7 — Number formatting + sign treatment isn't fully unified — S/M
- **What:** Percentages are mostly via `pct1()` now (good), but several surfaces
  still hand-roll: `bets.astro` edge column does `(b.model_edge_pct*100).toFixed(1)`,
  CLV uses a local `fmtClv`, ROI uses `.toFixed(1)`, `matches/[id]` has a local
  `probPct`. Centralise `pct1`, `signed(n)` (always `+`/`−`), and a `money()` into
  `data.ts` and use everywhere. Also adopt a real minus glyph (`−`, U+2212) for
  negative P/L so tabular alignment is clean.
- **Why:** Item #2 in `site-improvements.md` fixed the *edge-%* drift; the same
  drift now lives in CLV/ROI/edge-in-bet-log. One formatter module ends the whole
  class of bug and tightens numeric polish (the site is otherwise very tabular-nums
  disciplined).
- **Where:** `site/src/lib/data.ts` (formatters), `bets.astro`, `matches/[id].astro`,
  `edges.astro`.
- **Effort:** S/M

### M-8 — `/calibration` and `/methodology` lack the hero treatment — S
- **What:** Every other top-level page leads with a gradient hero panel; calibration
  and methodology (per the file structure) lead with a bare `.eyebrow` + `h1` on the
  page background. These are the **trust/credibility** pages — the ones the
  positioning leans on hardest — yet they look the most utilitarian.
- **Why:** Visual hierarchy should track importance. The "how good is the model,
  honestly?" page is a flagship of the whole honest-forecaster pitch and deserves
  the same first-impression polish as Groups or Outrights. Reuses QW-5's `PageHero`.
- **Where:** `site/src/pages/calibration.astro`, `site/src/pages/methodology.astro`.
- **Effort:** S (once PageHero exists)

### M-9 — Flags: layout shift + offline/OG inconsistency — S/M
- **What:** `TeamFlag` loads remote `flagcdn.com` PNGs with `loading="lazy"`. On the
  bracket/groups/outrights pages that's dozens of cross-origin requests with a
  visible pop-in, and an external dependency that breaks the otherwise-offline build
  ethos (OG cards already had to skip flags for this reason). Width/height are set
  (good — no CLS), but consider vendoring a flag sprite or `wsrv.nl`-cached/self-
  hosted subset so flags are first-party, instant, and consistent with the OG cards.
- **Why:** Removes a third-party runtime dependency on the most flag-dense pages,
  kills the lazy pop-in on the bracket, and unifies on-page flags with OG-card flags
  (a noted follow-up in TASK-015/025).
- **Where:** `site/src/components/TeamFlag.astro`, build step to vendor flags.
- **Effort:** S/M (S if just preloading/eager above-the-fold; M to vendor)

---

## Larger

### L-1 — Mobile bottom tab bar (TASK-017, still open) — M/L
- **What:** Implement the planned bottom tab bar for `≤720px`: Today (/),
  Edges, Matches, Bracket, Track record(/bets) — 5 icons + labels, fixed bottom,
  safe-area-inset aware, with the current route highlighted. Pair it with QW-2 so
  the top scroller carries the secondary routes (Groups, Outrights, Calibration,
  Methodology).
- **Why:** Mobile is the core segment and the 9-pill horizontal scroller is a stopgap
  the backlog itself calls "the minimum." A bottom bar is the native mobile
  navigation pattern and a real perceived-quality jump. Highest-value larger item.
- **Where:** new `site/src/components/MobileNav.astro`, `Base.astro` (render it,
  add bottom padding to `<main>` so content isn't hidden behind the bar).
- **Effort:** M/L

### L-2 — A "Today / live" command-centre treatment on the dashboard — L
- **What:** The matchday band is good but static. Make the dashboard genuinely feel
  like a live tournament cockpit: promote the matchday band into the hero on
  matchdays (countdown to the *next* kickoff as a headline number), add a compact
  "movers" lane (biggest edge changes / soonest-kicking edges) and a single-line
  "tournament pulse" (N matches today · M new edges · top champion). This is the
  retention surface; right now it's a competent list of sections rather than a
  living dashboard.
- **Why:** The product lead's stated top retention lever is "what do I look at right
  now." The pieces exist (countdowns, edges, sim) but aren't composed into one
  glanceable above-the-fold story. Ties together QW-3, M-3.
- **Where:** `site/src/pages/index.astro`, small new components, `data.ts` selectors
  (soonest-edge, "today" rollups). Depends on/overlaps M-3.
- **Effort:** L

### L-3 — Interactive micro-charts for the match page — M/L
- **What:** The match page is text/stat-card heavy. Add (still zero-or-tiny-JS):
  a small score-matrix heatmap (the Poisson grid the model already computes drives
  it), a sparkline of each team's Elo trajectory, and a compact "where the edge is"
  bar comparing model vs implied across the priced markets. These turn a numbers
  page into something shareable and skimmable.
- **Why:** Per-match pages are the SEO/share leaf nodes (OG cards already target
  them). A signature visual (the score-matrix heatmap especially) is a "moment of
  delight" + a differentiation vs generic tipster sites, and the data is already
  in the prediction payload.
- **Where:** `site/src/pages/matches/[id].astro`, new chart components,
  `data.ts`/prediction shape (expose the score matrix if not already emitted).
- **Effort:** M/L (M if matrix already in JSON; L if model must emit it)

### L-4 — Theme system: respect `prefers-color-scheme` + a print stylesheet — M
- **What:** The site hard-codes dark (`color-scheme: dark`). Two upgrades: (1) a
  light-theme token set behind `@media (prefers-color-scheme: light)` (the design is
  fully tokenised, so this is mostly a second `:root` block) for users/contexts that
  demand it and for better OG/preview rendering; (2) a print stylesheet so a
  bettor can print/PDF an edges sheet or the calibration report cleanly (strip
  gradients/sticky header, force ink-friendly colours).
- **Why:** All-dark excludes a real slice of users and reads poorly when embedded or
  screenshotted on light backgrounds; print/PDF is a natural "save my edges" flow
  for an analysis tool. The full token system makes both cheaper than they look.
- **Where:** `site/src/layouts/Base.astro` (`:root` light block + `@media print`).
- **Effort:** M

### L-5 — Watchlist / favourite teams (TASK-026) as a delight + retention layer — M
- **What:** localStorage-backed favourite-team stars (on team pages, group cards,
  match cards) that (a) pin followed teams' fixtures/edges to the top of the
  dashboard and `/edges`, and (b) add a tiny "following N" chip in the header.
  No accounts, progressive-enhancement only.
- **Why:** The only zero-backend retention mechanic in the backlog; turns a
  read-only dashboard into something personal. Pairs naturally with the bottom nav
  (L-1) and the live dashboard (L-2).
- **Where:** small client component + `localStorage`, `index.astro`, `edges.astro`,
  `team/[slug].astro`, `GroupCard.astro`, `MatchCard.astro`.
- **Effort:** M

---

## Cross-cutting consistency notes (fold into the above)

- **Duplicated `.sr-only`** is redeclared in `index`, `bets`, `bracket`,
  `calibration`, `BookmakerOdds`. Promote one copy to global `Base.astro` and delete
  the rest (DRY; also guarantees consistent behaviour). *(S, bundle with QW-1.)*
- **`.see-all`, `.hero-chip`, `.news-grid`, `.cards-grid`, `.callout`** are each
  re-declared across pages — globalise the stable ones in `Base.astro`. *(S.)*
- **Inline `style=` attributes** for section spacing (`margin-top:2.25rem` etc.) are
  everywhere; a `.section` / `.stack` utility would replace dozens of inline styles
  and enforce vertical rhythm. *(S/M.)*
- **`background-attachment: fixed`** is correctly gated to desktop — leave it, but if
  L-4 adds a light theme, re-check the radial-gradient body wash for contrast.
```
