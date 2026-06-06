# News / Team-News Feed — Research & Implementation Plan

Research for adding a pre-match **news / team-news feed** (injuries, suspensions,
lineup news, general pre-match info) to the World Cup 2026 betting-analysis site.

**Scope reminder (how this project works):** Python fetchers read API keys from
`.env` via a tiny hand-rolled loader, pull external data, and write JSON into the
repo. The Astro site is a **static build** that reads those JSON files at build
time (`site/src/lib/data.ts`, `readJson`). Teams are **international sides
(countries)**, and team names are normalised with a hand-maintained dictionary
(`ODDS_TO_FIXTURE` in `model/fetch_odds.py`). Fixtures live in
`fixtures/fixtures.json` (104 matches; `home`/`away` are country names like
`"Mexico"`, `"South Africa"`, `"USA"`, `"DR Congo"`). The only existing external
API is The Odds API (free tier, ~500 req/month). Any news feed should follow the
same shape: a `model/fetch_news.py` that writes `site/public/data/news.json`.

> **Honest headline finding:** For **national teams**, structured machine-readable
> injury/suspension data is **thin and often stale** compared with club football,
> and the most decision-relevant events (a star withdrawing from camp, a late
> illness, a manager's pre-match presser) break first as **news headlines**, not
> as structured API rows. So the right v1 is **RSS/news headlines matched to
> teams ($0)**, with a **paid structured-injuries API as a v2 enrichment**, not
> the other way round.

---

## 1. Data sources

### 1.1 Structured football data APIs

#### API-Football (api-sports.io) — recommended paid option
- **Provides:** fixtures, **lineups** (incl. pre-match predicted formations once
  published), **injuries** (which includes suspensions — "players who potentially
  will not participate"), predictions, odds, players, standings. Structured JSON.
- **National-team / World Cup coverage:** Explicitly supports **World Cup 2026**.
  The competition is **`league=1`**, season **`2026`**. Per their official guide,
  the 48 teams are `teams?league=1&season=2026`; injuries/suspensions are
  `injuries?league=1&season=2026` (and you can scope by `fixture` id); lineups,
  predictions, fixture stats, player stats and odds are all listed as covered for
  the tournament.
  ([api-football.com WC2026 guide](https://www.api-football.com/news/post/fifa-world-cup-2026-guide-to-using-data-with-api-sports))
- **Injuries endpoint:** `GET /injuries` accepts `fixture`, `league`+`season`,
  `team`, `player`, `date`. Returns player, team, fixture, plus `type`
  (e.g. "Missing Fixture"/"Questionable") and `reason`. Before trusting it, check
  the `coverage.injuries` boolean on the `/leagues` response for that
  league-season.
  ([New Injuries endpoint](https://www.api-football.com/news/post/new-endpoint-injuries),
  [Docs v3](https://api-sports.io/documentation/football/v3))
- **Access:** REST, key in `x-apisports-key` header (or RapidAPI host header).
- **Pricing / free tier:** **Free plan = 100 requests/day**, all endpoints
  included; paid plans **from $19/mo** (higher daily/min limits, more history).
  Features don't change between tiers — only volume/history.
  ([Pricing](https://www.api-football.com/pricing))
- **Caveats (their own words):** "values set to True do not guarantee 100% data
  availability" and there can be a delay between calendar publication and data
  availability. Treat injury coverage as **best-effort, not authoritative**, for
  national teams.
  ([WC2026 guide](https://www.api-football.com/news/post/fifa-world-cup-2026-guide-to-using-data-with-api-sports))
- **Fit:** Excellent — same "Python + requests + key in .env + write JSON"
  pattern as `fetch_odds.py`; free tier (100/day) is plenty for 104 fixtures
  polled occasionally.

#### Sportmonks — strong alternative, no true free tier
- **Provides:** injuries & suspensions (the **`sidelined`** include on teams /
  players / fixtures), **confirmed lineups** and **Premium Expected (predicted)
  lineups** (separate add-on), squads, formations.
  ([Injuries & suspensions](https://www.sportmonks.com/glossary/injuries-and-suspensions/),
  [Expected lineups](https://www.sportmonks.com/blogs/premium-expected-lineups/),
  [Lineups guide](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/lineups-and-formations))
- **National-team / World Cup:** Covers the World Cup; has a dedicated WC2026
  guide and widget bundles.
  ([WC2026 API guide](https://www.sportmonks.com/blogs/world-cup-2026-api-guide-coverage-endpoints-data-types/),
  [World Cup API](https://www.sportmonks.com/football-api/world-cup-api/))
- **Access:** REST, `api_token` query param, rich `include=` system.
- **Pricing:** **No forever-free plan that includes the World Cup.** The free
  plan only covers Danish Superliga + Scottish Premiership. Paid: **Starter
  €29/mo (5 leagues), Growth €99/mo (30 leagues), Pro €249/mo (120 leagues)**;
  14-day trial after subscribing. Expected (predicted) lineups are a paid add-on.
  ([Plans & pricing](https://www.sportmonks.com/football-api/plans-pricing/),
  [Free plan](https://www.sportmonks.com/football-api/free-plan/))
- **Fit:** Good data quality, but cost/structure is worse than API-Football for
  this single-tournament, hobby use case. Recommend it only if API-Football's
  national-team injury coverage proves too sparse.

#### Opta / Stats Perform — enterprise only (not realistic here)
- The gold standard for lineups/injuries/data depth, but **B2B, contract-based,
  no public self-serve pricing or free tier**. Overkill and unaffordable for a
  personal site. Mentioned for completeness; **not recommended**.

### 1.2 News APIs (headlines, not structured injuries)

| Source | Free tier | National-team news | Commercial/static-site use | Notes |
|---|---|---|---|---|
| **NewsAPI.org** | **100 req/day**, dev/testing only | Good (150k+ sources) | **Free plan is dev-only — not for production/public sites**; paid required for production + "powered by" attribution | ([Pricing](https://newsapi.org/pricing), [Terms](https://newsapi.org/terms)) |
| **GNews** | **100 req/day**, 1 req/sec; archive to 2020 | Good; full article body paywalled | Free plan "development and testing only," no commercial; paid **from $9.99/mo (10k req)** | ([Pricing](https://gnews.io/pricing)) |
| **NewsData.io / Currents / TheNewsAPI** | Varying small free tiers | OK | Check each ToS | Alternatives if the above don't fit ([Currents](https://currentsapi.services/en/product/price)) |

The catch: every mainstream news API's **free tier forbids production / public-site
use**. Since this is a *personal* site whose pages are *built* (the headlines get
baked into static JSON, not proxied live to visitors), you are in a grey area —
**RSS avoids the problem entirely** and is the cleaner $0 choice (see below). If
you ever want keyword *search* (e.g. "Brazil injury Neymar") rather than just a
firehose to filter locally, a paid GNews tier ($9.99/mo) is the cheapest path.

### 1.3 RSS feeds from major outlets — the $0 backbone (recommended for v1)
- **BBC Sport football:** `https://feeds.bbci.co.uk/sport/football/rss.xml`
  — verified valid RSS 2.0, ~60 items, each with `title`/`link`/`pubDate`/
  `description` (+ media thumbnails). Confirmed to carry **national-team / WC2026
  content** (England, Scotland, Wales squad/manager items in the live feed).
  ([BBC Sport RSS list](https://rss.feedspot.com/bbcsport_rss_feeds/))
- **The Guardian football:** `https://www.theguardian.com/football/rss`
  — football news/results/blogs incl. World/international football.
  ([Guardian RSS list](https://rss.feedspot.com/theguardian_rss_feeds/))
- **ESPN soccer:** ESPN exposes per-section RSS via
  `https://www.espn.com/espn/rss/` (and historically `espnfc` feeds). ESPN also
  publishes a human-curated **"2026 World Cup injuries tracker"** article — useful
  as a manual cross-check even if not a feed.
  ([ESPN RSS index](https://www.espn.com/espn/news/story?id=3437834),
  [ESPN WC injuries tracker](https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker-which-stars-miss-latest-info))
- **Why RSS for v1:** No API key, no daily quota, explicitly published for
  syndication (headline + link + summary; you link back to the source, which is
  the intended use — keep the link and outlet attribution, don't republish full
  article bodies). Gives you exactly what a bettor wants pre-match: *"is there a
  fresh story about this country's squad?"*

### 1.4 Official / social sources
- **FIFA, national FAs, club/# accounts on X:** earliest signal (camp
  withdrawals, presser quotes) but **no stable free API** (X's API is paid/locked
  down) and high scraping/ToS risk. **Not recommended** for an automated fetcher;
  use manually if at all.

### 1.5 Wikipedia / Wikidata — squad reference data (not news)
- **`2026 FIFA World Cup squads`** (Wikipedia) lists each team's 23–26 official
  players, positions, ages — good for a **squad reference / player→team map**, not
  for injuries.
  ([Wikipedia squads](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads),
  [Wikidata Q133699268](https://www.wikidata.org/wiki/Q133699268))
- **Access:** MediaWiki Action API `action=parse&prop=wikitext|text&section=N`, or
  REST/TextExtracts, CC-licensed.
  ([API:Parsing wikitext](https://www.mediawiki.org/wiki/API:Parsing_wikitext))
- **Use:** optional v2 nicety — lets you detect when a headline names a player and
  attribute it to the right country. Not needed for v1.

---

## 2. Architecture — fitting a news feed into this project

Mirror the existing data pipeline exactly:

```
model/fetch_news.py   →  site/public/data/news.json   →  site reads via data.ts
   (Python + requests)        (committed JSON)           (build time)
```

### 2.1 Mapping news → teams → matches
- Build a **per-team keyword index** from `fixtures.json`. For each of the ~48
  countries, generate match aliases: the canonical name plus common variants
  (reverse the `ODDS_TO_FIXTURE` idea — e.g. `"USA"` → `["USA","United States",
  "US men", "USMNT"]`; `"South Korea"` → `["South Korea","Korea Republic"]`;
  `"DR Congo"` → `["DR Congo","Congo DR","DRC"]`; `"Ivory Coast"` →
  `["Ivory Coast","Côte d'Ivoire","Cote d'Ivoire"]`). Reuse/extend the existing
  normalisation dictionary so there's **one source of truth** for name variants.
- For each RSS/news item, lowercase the title+description and test for any team's
  aliases (word-boundary match to avoid e.g. "Iran" matching "Iranian" noise is
  fine, but guard short tokens like "US"/"DRC" with word boundaries). Tag the
  item with every matched country.
- **Match-level association:** a `news.json` item tagged with country X is shown
  on (a) the dashboard global feed and (b) every upcoming match page where
  `home == X or away == X`. No separate per-match files needed — the site filters
  by team at build time (cheap; 104 matches × small feed).

### 2.2 Filtering, dedup, freshness
- **Recency:** drop items older than, say, 10 days (configurable); for a given
  match, the match page can prefer items from the last 3–5 days before kickoff.
- **Relevance:** keep an item only if it (a) matched at least one tournament team
  **and** (b) optionally contains a football/squad keyword (`injur`, `suspend`,
  `ban`, `squad`, `lineup`, `line-up`, `doubt`, `ruled out`, `withdraw`, `fit`,
  `return`) to bias toward team-news vs. transfer gossip. Store an
  `is_injury_related` boolean for UI filtering.
- **Dedup:** key on normalised URL (strip query/utm) and a normalised title hash;
  keep the earliest `pubDate`. Merge tags if the same story is matched twice.
- **Caching / rate limits:** RSS has no quota, but be polite — send a
  `User-Agent`, honour `ETag`/`Last-Modified` if you persist them, and run the
  fetcher on your weekend workflow cadence (the README's "one call per matchday"
  philosophy). If you add API-Football, the **100 req/day** free cap is ample:
  one `/injuries?league=1&season=2026` call returns the whole tournament; cache
  the response and only re-poll changed/near-kickoff fixtures.

### 2.3 How the static site surfaces it
- **Primary: build-time (recommended).** `fetch_news.py` writes
  `site/public/data/news.json`; add `loadNews()` to `site/src/lib/data.ts`
  (same `readJson` helper). Render a "Team News" panel on `index.astro`
  (dashboard) and a per-match news block on `site/src/pages/matches/[id].astro`,
  filtering items by the match's two teams. Fully static, no client JS, matches
  the project's ethos.
- **Optional: light client-side refresh.** Because static builds go stale between
  deploys, you *could* add a tiny client `fetch('/data/news.json')` so a rebuilt
  JSON shows without a full redeploy — but simplest is to just re-run the fetcher
  + rebuild as part of the pre-match workflow. Recommend build-time only for v1.

### 2.4 Recommended approach + fallback
- **Primary (v1):** RSS (BBC + Guardian + ESPN) → team-name matching → filtered,
  deduped `news.json` → build-time render. **$0, no keys, no ToS risk.**
- **Enrichment (v2):** add API-Football `/injuries` (free 100/day) to attach
  **structured injury/suspension rows** per team, shown as a distinct,
  higher-confidence block separate from the headline feed.
- **Cheap fallback if an RSS host blocks you:** swap that host for another feed
  (Sky Sports, football365, BBC top-level `sport/rss.xml`) — the matcher is
  source-agnostic.

---

## 3. Injuries & lineups specifically (national teams) — honest assessment

- **Structured injury/suspension data that actually covers national teams:**
  practically only **API-Football** (`/injuries`, free tier) and **Sportmonks**
  (`sidelined`, paid). API-Football explicitly lists injuries as covered for
  **WC2026 (`league=1`, `season=2026`)**.
  ([api-football WC2026 guide](https://www.api-football.com/news/post/fifa-world-cup-2026-guide-to-using-data-with-api-sports))
- **Predicted/confirmed lineups:** API-Football lineups (predicted formations
  before kickoff, confirmed ~1h before); Sportmonks confirmed lineups + Premium
  **Expected** lineups add-on.
  ([Expected lineups](https://www.sportmonks.com/blogs/premium-expected-lineups/))
- **Reliability & timeliness — the gaps (be realistic):**
  - National-team injury feeds are **sparser and laggier** than club feeds.
    API-Football itself warns coverage flags "do not guarantee 100% data
    availability" and there can be ingestion delays.
    ([guide](https://www.api-football.com/news/post/fifa-world-cup-2026-guide-to-using-data-with-api-sports))
  - The highest-impact pre-match events are **squad/camp dynamics** an API rarely
    captures in time: WC2026 squads are 23–26 players locked by **2 June 2026**,
    and an injured player can be replaced from the provisional list **up to 24h
    before the team's first match** — these withdrawals surface in **news first**
    (e.g. the late "withdrew through injury / replaced by …" reports).
    ([Sky Sports squad lists](https://www.skysports.com/football/news/11095/13543070/world-cup-2026-squad-lists-england-scotland-brazil-usa-spain-france-germany-netherlands-argentina-portugal-and-more))
  - Confirmed XIs only land **~1 hour pre-kickoff**; "predicted" lineups are
    estimates and disagree across providers.
- **Net:** Treat structured injuries as a **supporting signal**, and rely on the
  **RSS/headline feed + human-curated trackers** (e.g. ESPN's WC injuries tracker)
  as the primary, timeliest pre-match read. Do not present API injury rows as
  authoritative.
  ([ESPN WC injuries tracker](https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker-which-stars-miss-latest-info))

---

## 4. Implementation plan (phased)

### Phase v1 — RSS + team-name matching ($0, ~½–1 day)
**Goal:** a build-time team-news feed with zero keys and zero quota risk.

**Files to add:**
- `model/fetch_news.py` — new fetcher (mirror `fetch_odds.py`: `_load_env()`
  reused pattern, `requests`, write JSON).
- `model/team_aliases.py` *(optional)* — the country→aliases map (or inline it).
- `site/public/data/news.json` — output (committed, like `predictions.json`).
- Edits (separate task, not in this research scope): `loadNews()` in
  `site/src/lib/data.ts`; a panel in `site/src/pages/index.astro`; a block in
  `site/src/pages/matches/[id].astro`.

**Dependencies:** add a feed parser. Either `feedparser` (add to
`model/requirements.txt`) or hand-parse with stdlib `xml.etree` to avoid a new
dep — RSS is simple enough that stdlib is fine and keeps the dependency list lean
(the repo already has `requests`).

**Endpoints (no key):**
- `https://feeds.bbci.co.uk/sport/football/rss.xml`
- `https://www.theguardian.com/football/rss`
- `https://www.espn.com/espn/rss/` (soccer section)

**Algorithm:**
1. `_load_env()` (not needed for RSS, but keep for v2 parity).
2. Load `fixtures.json`; build `{country: [aliases]}` and the set of
   tournament teams.
3. For each feed: GET (with `User-Agent`), parse items
   (`title`,`link`,`pubDate`,`description`,`source`).
4. Normalise, dedup (URL/title), drop items older than N days, tag with matched
   countries, set `is_injury_related`.
5. Sort by `pubDate` desc; write `news.json`.

**JSON shape:**
```json
{
  "generated_at": "2026-06-05T12:00:00Z",
  "sources": ["BBC Sport", "The Guardian", "ESPN"],
  "items": [
    {
      "id": "sha1-of-url",
      "title": "Brazil sweat on Vinicius fitness before opener",
      "url": "https://www.bbc.co.uk/sport/football/...",
      "source": "BBC Sport",
      "published_at": "2026-06-05T09:14:00Z",
      "summary": "Short description from the feed...",
      "teams": ["Brazil"],
      "is_injury_related": true
    }
  ]
}
```
Site usage: dashboard shows latest N items; a match page shows
`items.filter(i => i.teams.includes(home) || i.teams.includes(away))`.

### Phase v2 — structured injuries/suspensions (API-Football, free→$19/mo, ~½ day)
**Goal:** a separate, higher-confidence injuries block per team/match.

**Setup:** sign up at api-sports.io, add `APIFOOTBALL_KEY=...` to `.env`
(same place as `ODDS_API_KEY`).

**Endpoints (header `x-apisports-key: <key>`, base `https://v3.football.api-sports.io`):**
- Coverage check: `GET /leagues?id=1&season=2026` → confirm
  `coverage.fixtures.injuries == true`.
- Tournament injuries: `GET /injuries?league=1&season=2026`.
- Per-fixture (optional): `GET /injuries?fixture=<id>`.
- Predicted lineups (optional): `GET /fixtures/lineups?fixture=<id>`.

**Extend `fetch_news.py` (or `fetch_injuries.py`):** map API `team.name` →
fixture country via the alias map, write an `injuries` array into `news.json` (or
a sibling `injuries.json`):
```json
"injuries": [
  { "team": "Brazil", "player": "Vinícius Júnior",
    "type": "Questionable", "reason": "Knee", "fixture_id": null,
    "source": "API-Football", "as_of": "2026-06-05T11:00:00Z" }
]
```
**Rate limits:** one tournament-wide `/injuries` call per run easily fits the
**100/day** free cap; cache and only re-poll near kickoffs.
([Pricing](https://www.api-football.com/pricing))

### Phase v3 — optional polish
- Keyword **search** via paid GNews ($9.99/mo) for targeted per-team queries
  ([GNews pricing](https://gnews.io/pricing)).
- Wikipedia squad parse for player→team attribution / richer match context
  ([API:Parsing wikitext](https://www.mediawiki.org/wiki/API:Parsing_wikitext)).
- Sportmonks Expected Lineups if predicted XIs become important
  ([Expected lineups](https://www.sportmonks.com/blogs/premium-expected-lineups/)).

### API keys summary (all go in repo-root `.env`)
| Phase | Var | Needed? |
|---|---|---|
| v1 RSS | — | none |
| v2 injuries | `APIFOOTBALL_KEY` | free tier (100/day) |
| v3 search | `GNEWS_KEY` | optional, paid |

---

## Sources
- API-Football WC2026 guide: https://www.api-football.com/news/post/fifa-world-cup-2026-guide-to-using-data-with-api-sports
- API-Football injuries endpoint: https://www.api-football.com/news/post/new-endpoint-injuries
- API-Football docs (v3): https://api-sports.io/documentation/football/v3
- API-Football pricing: https://www.api-football.com/pricing
- Sportmonks plans & pricing: https://www.sportmonks.com/football-api/plans-pricing/
- Sportmonks free plan: https://www.sportmonks.com/football-api/free-plan/
- Sportmonks injuries & suspensions: https://www.sportmonks.com/glossary/injuries-and-suspensions/
- Sportmonks expected lineups: https://www.sportmonks.com/blogs/premium-expected-lineups/
- Sportmonks lineups guide: https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/lineups-and-formations
- Sportmonks WC2026 guide: https://www.sportmonks.com/blogs/world-cup-2026-api-guide-coverage-endpoints-data-types/
- NewsAPI.org pricing: https://newsapi.org/pricing
- NewsAPI.org terms: https://newsapi.org/terms
- GNews pricing: https://gnews.io/pricing
- BBC Sport RSS list: https://rss.feedspot.com/bbcsport_rss_feeds/
- Guardian RSS list: https://rss.feedspot.com/theguardian_rss_feeds/
- ESPN RSS index: https://www.espn.com/espn/news/story?id=3437834
- ESPN WC2026 injuries tracker: https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker-which-stars-miss-latest-info
- Wikipedia 2026 WC squads: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads
- Wikidata Q133699268: https://www.wikidata.org/wiki/Q133699268
- MediaWiki API parsing wikitext: https://www.mediawiki.org/wiki/API:Parsing_wikitext
- Sky Sports WC2026 squad lists (squad rules / late withdrawals): https://www.skysports.com/football/news/11095/13543070/world-cup-2026-squad-lists-england-scotland-brazil-usa-spain-france-germany-netherlands-argentina-portugal-and-more
