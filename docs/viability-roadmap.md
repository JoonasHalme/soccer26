# Viability roadmap — expert panel synthesis

Three advisors reviewed the project for "what to add to make it more viable":
a professional bettor (betting-tool features), a product/growth lead (UX,
retention, mobile), and a business strategist (positioning, monetization,
compliance). This is the consolidated, de-duplicated roadmap.

## The one thing all three agreed on

**A public, tamper-evident, continuously-graded track record that reports
Closing Line Value (CLV), not just ROI.**

- The bettor: CLV vs. the de-vigged closing line is the only honest skill
  metric over a ~100-match sample; ROI is noise.
- The strategist: the bet log is empty and "beats the market" is unproven, so
  there is no edge to sell and nothing for a stranger to verify. This gap is the
  entire business problem.
- The product lead: a "model report card" (which calls hit/missed, running CLV)
  is also the content that drives return visits and shares.

Everything monetizable or trustworthy is downstream of this. Start capturing it
now (qualifiers/friendlies), hash predictions before kickoff so they can't be
cherry-picked.

## Tier 1 — highest impact-to-effort (do first)

| # | Item | Lens | Effort |
|---|------|------|--------|
| 1 | **CLV capture + scoreboard** — snapshot closing odds, de-vig them the same way `devig_market()` does, report CLV + beat-rate on the bets page | Bettor / Business | M |
| 2 | **Line-shopping / best-price across books** — price edges against the *best* available book price, not consensus (worth several % EV/bet) | Bettor | M (✅ per-book odds now fetched — see below) |
| 3 | **Fractional-Kelly + flat staking engine** — turn the 5% gate into actual bankroll-aware position sizing | Bettor | S/M |
| 4 | **"Today / this matchday" hero + kickoff countdowns** — reframe the dashboard around "what do I look at now" | Product | S |
| 5 | **Compliance layer** — RG disclaimer, 18+/jurisdiction note, "not advice", affiliate-disclosure stub (currently entirely absent) | Business | S |
| 6 | **Quick bet-logging** — `add_bet.py --edge <id> --odds <price>` or a copy-paste bet-slip pre-filled from the model edge | Bettor | S |

## Tier 2 — high value, builds on Tier 1

| # | Item | Lens | Effort |
|---|------|------|--------|
| 7 | **Aggregated "all current value edges" page** (sortable/filterable) — the actionable centerpiece + newsletter teaser | Product / Business | S/M |
| 8 | **Search / filter / sort across matches & edges** (client-side over existing JSON) | Product | M |
| 9 | **Asian Handicap / Asian totals markets** — lowest vig in football; the score matrix already prices them | Bettor | S price / M source |
| 10 | **Live / results mode** — poll `results.json` on matchdays so scores + LIVE pill update without a redeploy | Product | M |
| 11 | **Reposition as "the transparent, auditable WC2026 model"** — claim the niche 538's SPI shutdown vacated; publish the calibration report | Business | S |
| 12 | **Newsletter (Substack/Patreon) + RSS digest of new edges & news** — no gambling licence needed; the realistic monetization on-ramp | Business / Product | S–M |
| 13 | **Live calibration tracking** — bin tournament predictions vs. outcomes; show model vs. de-vigged-closing reliability side by side | Bettor | M |
| 14 | **Shareable OG / edge cards** — build-time generated; the only real growth/distribution mechanic | Product | M |
| 15 | **Onboarding "How to read this" + jargon tooltips** (edge, de-vig, xG, Elo) — trust + shareability | Product | S–M |

## Tier 3 — depth, polish, later

- Mobile nav + bottom tab bar + table-collapse (mobile is the betting segment) — Product, M
- Per-team / per-group SEO landing pages (`/team/brazil`, `/group/a`) — Product, M
- Bet-log analytics split by source/market/edge-bucket/CLV — Bettor, S/M
- Price-cross alerting (scheduled poller, rate-limit-bound) — Bettor, M
- Pre-commit SHA + timestamp of predictions (tamper-evident) — Bettor/Business, S
- Alt totals / DNB / double-chance / correct-score from the score matrix — Bettor, S
- Watchlist / favourite teams (localStorage v1, no backend) — Product, M
- Accessibility: prob-bar screen-reader labels, colorblind redundancy — Product, S–M
- Outright/group winner Monte-Carlo sim (engagement, high-vig, not edge) — Bettor/Product, M/L

## Monetization verdict (business strategist)

Realistic stack for a solo operator: **content/SEO + ads → newsletter
(Substack/Patreon) → a thin premium tier later.** Affiliate/referral is lucrative
but a compliance + credibility minefield (licensing varies by jurisdiction; you
can't be paid to send users to a book you also "review") — if used, ring-fence
and disclose it. Tipster/subscription-for-edge is a *future* prize gated entirely
on a proven CLV record. API/data licensing is a non-starter (the model is behind
free open-source alternatives).

**Honest verdict:** not viable as a "sharp tips that beat the market" product
(mid-tier single-Elo model, unproven edge, empty log). Genuinely viable as a
**transparent, honestly-graded, World-Cup-focused forecaster** that wins an
audience on credibility, monetizes via content + newsletter, and earns a premium
tier only after a public CLV record proves the model does more than calibrate
well. The technical foundation is strong; the missing pieces are trust
infrastructure and honest positioning, not more model sophistication.
