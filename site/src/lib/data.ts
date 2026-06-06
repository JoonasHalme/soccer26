import fs from "node:fs";
import path from "node:path";

// process.cwd() is the `site/` directory at both `astro dev` and `astro build`.
const ROOT = path.resolve(process.cwd(), "..");

type Json = unknown;

/** A validator throws a descriptive Error if `data` isn't the shape it expects. */
type Validator<T> = (data: unknown, rel: string) => asserts data is T;

/**
 * Read + parse a build-time JSON artifact, with a clear failure policy:
 *  - MISSING file  → return `fallback` (pre-tournament artifacts may not exist yet).
 *  - CORRUPT JSON  → THROW (a malformed artifact must fail the build loudly, not
 *    silently render wrong numbers on a betting site).
 *  - optional `validate` → THROW with the filename if the shape is wrong.
 * This replaces the old `JSON.parse(...) as T` lie-to-the-compiler with a real
 * boundary check (code review H3 / TASK-055).
 */
function readJson<T = Json>(rel: string, fallback: T, validate?: Validator<T>): T {
  const full = path.join(ROOT, rel);
  let raw: string;
  try {
    raw = fs.readFileSync(full, "utf8");
  } catch {
    return fallback; // missing file is tolerated
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new Error(`[data] ${rel} is not valid JSON: ${(err as Error).message}`);
  }
  if (validate) validate(parsed, rel);
  return parsed as T;
}

/** Throw a uniform, file-named error from a loader validator. */
function fail(rel: string, msg: string): never {
  throw new Error(`[data] ${rel} is malformed: ${msg}`);
}
const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

// Exported, named loader validators (used by the loaders below; unit-tested directly
// so we know malformed artifacts are rejected, not silently rendered).
export const validateFixtures: Validator<{ matches: Match[]; groups: Record<string, string[]> }> = (d, rel) => {
  if (!isObj(d) || !Array.isArray(d.matches)) fail(rel, "expected { matches: [...] }");
  for (const m of d.matches as unknown[]) {
    if (!isObj(m) || typeof m.id !== "string") fail(rel, "a match is missing a string `id`");
  }
};
export const validateBets: Validator<BetsConfig> = (d, rel) => {
  if (!isObj(d)) fail(rel, "expected a config object");
  if (typeof d.starting_bankroll !== "number") fail(rel, "`starting_bankroll` must be a number");
  if (!Array.isArray(d.bets)) fail(rel, "`bets` must be an array");
  for (const b of d.bets as unknown[]) {
    if (!isObj(b) || typeof b.id !== "string") fail(rel, "a bet is missing a string `id`");
    if (typeof b.stake !== "number" || typeof b.odds_decimal !== "number")
      fail(rel, `bet ${String((b as { id: string }).id)} needs numeric stake & odds_decimal`);
  }
};
export const validatePredictions: Validator<{ generated_at: string | null; predictions: Prediction[] }> = (d, rel) => {
  if (!isObj(d) || !Array.isArray(d.predictions)) fail(rel, "expected { predictions: [...] }");
  for (const p of d.predictions as unknown[]) {
    if (!isObj(p) || typeof p.match_id !== "string") fail(rel, "a prediction is missing `match_id`");
    if (!isObj(p.probabilities)) fail(rel, `prediction ${String((p as { match_id: string }).match_id)} has no probabilities`);
  }
};

export interface Match {
  id: string;
  stage: "GROUP" | "R32" | "R16" | "QF" | "SF" | "3RD" | "FINAL";
  group?: string;
  round?: number;
  /** FIFA match number (knockout slots reference it as `W<game_no>` / `L<game_no>`). */
  game_no?: number;
  kickoff?: string;
  venue?: string;
  home: string;
  away: string;
  score?: { home: number | null; away: number | null };
  status: "SCHEDULED" | "LIVE" | "FINISHED" | "POSTPONED";
  odds?: Record<string, number>;
  books?: BookOdds[];
  /** Closing-line snapshot captured by `fetch_odds.py --closing` near kickoff. */
  closing_odds?: {
    captured_at?: string;
    consensus?: Record<string, number>;
    best_book?: Record<string, { price: number; book: string }>;
  };
}

/** One sportsbook's own prices for a match (line-shopping). */
export interface BookOdds {
  key: string;
  title: string;
  last_update?: string;
  h2h?: { home?: number; draw?: number; away?: number };
  totals?: { over_2_5?: number; under_2_5?: number };
}

export interface Bet {
  id: string;
  placed_at: string;
  match_id: string;
  market: string;
  selection: string;
  odds_decimal: number;
  stake: number;
  source: string;
  model_edge_pct?: number | null;
  model_prob?: number | null;
  rationale?: string;
  result?: "WIN" | "LOSS" | "PUSH" | "VOID" | null;
  pnl?: number | null;
  settled_at?: string | null;
  /** Closing-line value fields, populated by model/clv.py once the close exists. */
  closing_odds_decimal?: number | null;
  closing_fair_prob?: number | null;
  clv_pct?: number | null;
  best_book?: string | null;
}

/** One surfaced value edge from predict.py. Best-price fields are present only
 * when a sportsbook quotes the outcome (see model/predict.py find_edges). */
export interface Edge {
  market: string;
  selection: string;
  model_prob: number;         // our published (market-blended) call
  implied_prob: number;       // de-vigged consensus (fair) prob
  raw_implied_prob?: number;
  model_raw_prob?: number;    // pre-blend (anchored-model) prob
  raw_edge_pct?: number;      // raw gap: model_raw − fair (edge_pct = w · this)
  odds_decimal: number;       // consensus price
  edge_pct: number;           // STAKED edge: our call − de-vigged consensus = w · raw gap
  best_odds?: number;         // best price across books (line-shopping)
  best_book?: string;
  best_edge_pct?: number;     // realisable edge at the best price (raw)
  ev_pct?: number;            // expected return per unit at the best price
}

/** Asian handicap (home perspective; `line` = goals added to home) + Asian totals,
 * derived from the score matrix in model/elo.py. Display only — no AH odds sourced. */
export interface AsianHandicap { line: number; home: number; away: number; push?: number }
export interface AsianTotal { line: number; over: number; under: number }
export interface AsianMarkets { handicaps: AsianHandicap[]; totals: AsianTotal[] }

/** Double-chance / Draw-No-Bet / top correct scores, derived from the same score
 * matrix as 1X2 in model/elo.py. Display only — no odds sourced for these. */
export interface CorrectScore { home: number; away: number; prob: number }
export interface DerivedMarkets {
  double_chance: { home_or_draw: number; home_or_away: number; draw_or_away: number };
  dnb: { home: number; away: number };
  correct_scores: CorrectScore[];
}

export interface Prediction {
  match_id: string;
  home: string;
  away: string;
  kickoff?: string;
  ratings: { home: number; away: number };
  probabilities: {
    home: number; draw: number; away: number;
    over_2_5: number; under_2_5: number;
    btts_yes: number; btts_no: number;
    expected_goals: { home: number; away: number };
  };
  /** De-vigged fair probabilities implied by the market (priced groups only). */
  market?: Partial<Record<"home" | "draw" | "away" | "over_2_5" | "under_2_5", number>>;
  /** The PUBLISHED, market-blended forecast: pure `probabilities` shrunk toward
   * `market` (1X2 + O/U) by `weight` (the model's share). `blended` is false when
   * the match had no odds to blend against, in which case it equals the model. */
  forecast?: Prediction["probabilities"] & { blended: boolean; weight: number };
  asian?: AsianMarkets;
  derived?: DerivedMarkets;
  edges: Edge[];
  divergences?: Divergence[];
}

/** The probabilities to PUBLISH for a match: the market-blended forecast when we
 * have one, else the pure model. Use this for any "our call" surface (match
 * headline, cards, feed); use `.probabilities` only for the raw-model view. */
export function publishedProbs(p: Prediction): Prediction["probabilities"] {
  return p.forecast ?? p.probabilities;
}

/** A signed model-vs-fair gap for one priced outcome (both directions, no edge
 * threshold). `delta` = model − de-vigged fair. Powers the /divergence tracker. */
export interface Divergence {
  market: string;
  selection: string;
  model_prob: number;
  fair_prob: number;
  delta: number;
  best_odds?: number;
  best_book?: string;
}

/** A divergence collapsed to one row per (match, market) and joined with match
 * context, for the cross-match divergence page. */
export interface DivergenceRow extends Divergence {
  match_id: string;
  home: string;
  away: string;
  kickoff?: string;
  stage: Match["stage"];
  group?: string;
}

/** A value edge flattened with its match context, for the cross-match edges page. */
export interface EdgeRow extends Edge {
  match_id: string;
  home: string;
  away: string;
  kickoff?: string;
  stage: Match["stage"];
  group?: string;
}

const SELECTION_LABEL: Record<string, (home: string, away: string) => string> = {
  HOME: (h) => `${h} win`,
  AWAY: (_h, a) => `${a} win`,
  DRAW: () => "Draw",
  OVER_2_5: () => "Over 2.5 goals",
  UNDER_2_5: () => "Under 2.5 goals",
  BTTS_YES: () => "Both teams to score",
  BTTS_NO: () => "Both teams to score — No",
};

/** Human-readable label for an edge selection in the context of its match. */
export function selectionLabel(sel: string, home: string, away: string): string {
  return (SELECTION_LABEL[sel] ?? (() => sel))(home, away);
}

/** Compact, team-agnostic selection label for tiles/badges where space is tight
 * (so raw codes like OVER_2_5 / HOME never reach the UI). */
const SELECTION_SHORT: Record<string, string> = {
  HOME: "Home", AWAY: "Away", DRAW: "Draw",
  OVER_2_5: "Over 2.5", UNDER_2_5: "Under 2.5",
  BTTS_YES: "BTTS", BTTS_NO: "No BTTS",
};
export function selectionShort(sel: string): string {
  return SELECTION_SHORT[sel] ?? sel.replace(/_/g, " ");
}

/** Single source of truth for printing an edge percentage: one decimal place.
 * Use everywhere an edge % is rendered so badges, strips and tables agree
 * (kills the "+11.21%" vs "+11.2%" drift). */
export function pct1(n: number): string {
  return n.toFixed(1);
}

/** True minus glyph (− U+2212) — aligns in tabular columns where the ASCII hyphen
 * is too short and sits off the numeral baseline. */
export const MINUS = "−";

/** Number with an explicit sign and a real minus for negatives ("+4.2" / "−1.3"). */
export function signed(n: number, decimals = 1): string {
  const s = Math.abs(n).toFixed(decimals);
  return n < 0 ? `${MINUS}${s}` : `+${s}`;
}
/** Signed percentage ("+4.2%" / "−1.3%"). */
export function signedPct(n: number, decimals = 1): string {
  return `${signed(n, decimals)}%`;
}
/** Money with a real minus for negatives ("12.40 EUR" / "−12.40 EUR"). */
export function money(n: number, currency = "EUR", decimals = 2): string {
  return `${n < 0 ? MINUS : ""}${Math.abs(n).toFixed(decimals)} ${currency}`;
}

/**
 * Flatten every surfaced edge across all predictions into one list, joined with
 * its match's stage/group, sorted by consensus edge descending by default.
 * (Consensus edge — not raw EV — is the default sort so a single longshot price
 * can't dominate the table; the page lets the user re-sort by EV or kickoff.)
 */
export function allEdges(predictions: Prediction[], matches: Match[]): EdgeRow[] {
  const byId = new Map(matches.map((m) => [m.id, m]));
  const rows: EdgeRow[] = [];
  for (const p of predictions) {
    const m = byId.get(p.match_id);
    for (const e of p.edges) {
      rows.push({
        ...e,
        match_id: p.match_id,
        home: p.home,
        away: p.away,
        kickoff: p.kickoff,
        stage: m?.stage ?? "GROUP",
        group: m?.group,
      });
    }
  }
  rows.sort((a, b) => b.edge_pct - a.edge_pct);
  return rows;
}

/**
 * Where the model most disagrees with the market. For each match we collapse a
 * market to its single largest-|delta| outcome (the 1X2 legs are complementary —
 * a 35-pt HOME shortfall IS the same disagreement as the AWAY/DRAW surplus — so
 * three rows would triple-count one story). Rows are joined with match context
 * and sorted by absolute gap descending. `signedOnly` keeps only positive gaps
 * (model > market, the value direction) when a caller wants just those.
 */
export function topDivergences(
  predictions: Prediction[],
  matches: Match[],
  signedOnly = false,
): DivergenceRow[] {
  const byId = new Map(matches.map((m) => [m.id, m]));
  const rows: DivergenceRow[] = [];
  for (const p of predictions) {
    const best = new Map<string, Divergence>(); // market -> largest-|delta| outcome
    for (const d of p.divergences ?? []) {
      const cur = best.get(d.market);
      if (!cur || Math.abs(d.delta) > Math.abs(cur.delta)) best.set(d.market, d);
    }
    const m = byId.get(p.match_id);
    for (const d of best.values()) {
      if (signedOnly && d.delta <= 0) continue;
      rows.push({
        ...d,
        match_id: p.match_id,
        home: p.home,
        away: p.away,
        kickoff: p.kickoff,
        stage: m?.stage ?? "GROUP",
        group: m?.group,
      });
    }
  }
  rows.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  return rows;
}

export function loadFixtures() {
  return readJson<{ matches: Match[]; groups: Record<string, string[]> }>(
    "fixtures/fixtures.json",
    { matches: [], groups: {} },
    validateFixtures,
  );
}

/**
 * The fixtures the user should look at *right now*: today's matches if any are
 * still live/upcoming, otherwise the next calendar day that has fixtures. Drives
 * the dashboard's date-aware hero. `isToday` lets the UI say "Today" vs a date.
 */
/** Host-region timezone. The 2026 World Cup is played across North America and
 * many kickoffs fall after UTC-midnight (e.g. a 22:00 ET game = 02:00 UTC next
 * day), so a "matchday" is defined by the EASTERN calendar date, not the UTC one.
 * Eastern covers most venues and is the natural broadcast day. */
export const MATCHDAY_TZ = "America/New_York";

const _nyDateFmt = new Intl.DateTimeFormat("en-CA", {
  timeZone: MATCHDAY_TZ, year: "numeric", month: "2-digit", day: "2-digit",
});

/** The matchday key (YYYY-MM-DD in Eastern time) for a UTC kickoff ISO string. */
export function matchdayKey(iso: string): string {
  return _nyDateFmt.format(new Date(iso)); // en-CA => YYYY-MM-DD
}

/** Pretty label for a matchday key (e.g. "Thursday, 11 June"). */
export function matchdayLabel(key: string): string {
  return new Date(`${key}T12:00:00Z`).toLocaleDateString("en-GB", {
    timeZone: "UTC", weekday: "long", day: "numeric", month: "long",
  });
}

export function nextMatchday(
  matches: Match[],
  now: Date = new Date(),
): { date: string | null; label: string; isToday: boolean; matches: Match[] } {
  const nowIso = now.toISOString();
  const today = matchdayKey(nowIso); // Eastern date, not UTC

  const dated = matches.filter((m) => m.kickoff);
  const todays = dated.filter(
    (m) => matchdayKey(m.kickoff!) === today && m.status !== "FINISHED",
  );

  let date: string | null;
  let isToday = false;
  let dayMatches: Match[];

  if (todays.length) {
    date = today;
    isToday = true;
    dayMatches = todays;
  } else {
    const future = dated
      .filter((m) => m.status === "SCHEDULED" && m.kickoff! > nowIso)
      .sort((a, b) => a.kickoff!.localeCompare(b.kickoff!));
    date = future[0]?.kickoff ? matchdayKey(future[0].kickoff!) : null;
    dayMatches = date ? future.filter((m) => matchdayKey(m.kickoff!) === date) : [];
  }

  dayMatches = [...dayMatches].sort((a, b) => (a.kickoff ?? "").localeCompare(b.kickoff ?? ""));
  return { date, label: date ? matchdayLabel(date) : "", isToday, matches: dayMatches };
}

/** Most recent per-book `last_update` (ISO) across a match's books, or null. */
export function latestBookUpdate(match: Match): string | null {
  const ups = (match.books ?? [])
    .map((b) => b.last_update)
    .filter((u): u is string => typeof u === "string" && u.length > 0);
  return ups.length ? ups.reduce((a, b) => (a > b ? a : b)) : null;
}

/** The latest odds-capture time across ALL matches — a global "odds as of" stamp. */
export function oddsAsOf(matches: Match[]): string | null {
  let latest: string | null = null;
  for (const m of matches) {
    const u = latestBookUpdate(m);
    if (u && (!latest || u > latest)) latest = u;
  }
  return latest;
}

/** True when some match's odds were captured AFTER the predictions were generated —
 * the market has moved since the model last ran, so the published edges are stale and
 * `python model/predict.py` should be re-run. Build-time, kickoff-independent signal. */
export function oddsMovedSincePredictions(
  generatedAt: string | null | undefined,
  matches: Match[],
): boolean {
  if (!generatedAt) return false;
  const latest = oddsAsOf(matches);
  return latest != null && latest > generatedAt;
}

export interface BetsConfig {
  currency: string;
  starting_bankroll: number;
  unit_size: number;
  kelly_fraction: number;
  kelly_cap_pct: number;
  bets: Bet[];
}

export function loadBets() {
  return readJson<BetsConfig>("bets/bets.json", {
    currency: "EUR",
    starting_bankroll: 0,
    unit_size: 0,
    kelly_fraction: 0.25,
    kelly_cap_pct: 5,
    bets: [],
  }, validateBets);
}

/** Unscaled Kelly fraction f* = (b·p − q)/b; ≤0 means no +EV bet. */
export function fullKellyFraction(modelProb: number, odds: number): number {
  if (!odds || odds <= 1 || !(modelProb > 0 && modelProb < 1)) return 0;
  const b = odds - 1;
  const f = (b * modelProb - (1 - modelProb)) / b;
  return f > 0 ? f : 0;
}

/**
 * Fractional-Kelly stake for one bet, capped at `capPct` of bankroll. Mirrors
 * model/staking.py so the site and the bet-logger agree. Returns the suggested
 * stake and whether the cap bound it.
 */
export function kellyStake(
  modelProb: number,
  odds: number,
  bankroll: number,
  fraction = 0.25,
  capPct = 5,
): { stake: number; capped: boolean; fullKelly: number } {
  const fStar = fullKellyFraction(modelProb, odds);
  const capAmount = (bankroll * capPct) / 100;
  const raw = bankroll * fStar * fraction;
  const capped = raw > capAmount;
  return { stake: Math.round(Math.min(raw, capAmount) * 100) / 100, capped, fullKelly: fStar };
}

export function loadPredictions() {
  return readJson<{ generated_at: string | null; predictions: Prediction[] }>(
    "site/public/data/predictions.json",
    { generated_at: null, predictions: [] },
    validatePredictions,
  );
}

/** One immutable line in the append-only prediction provenance ledger
 * (model/predict.py). `sha256` is over the exact predictions.json bytes;
 * `content_sha256` is over the picks alone (timestamp-free, used for dedup). */
export interface LedgerEntry {
  generated_at: string;
  algorithm: string;
  sha256: string;
  content_sha256?: string;
  n_predictions: number;
  file: string;
}

export function loadLedger(): LedgerEntry[] {
  const l = readJson<LedgerEntry[]>("site/public/data/predictions_ledger.json", []);
  return Array.isArray(l) ? l : [];
}

/** Per-team tournament-outcome probabilities from the Monte-Carlo sim
 * (model/simulate.py). All fields are probabilities in [0,1]. */
export interface SimTeam {
  team: string;
  group: string;
  rating: number;
  win_group: number;
  qualify: number;
  r16: number;
  qf: number;
  sf: number;
  final: number;
  champion: number;
}
export interface Simulation {
  generated_at: string | null;
  n_sims: number;
  seed?: number;
  teams: SimTeam[];
}

export function loadSimulation(): Simulation {
  return readJson<Simulation>("site/public/data/simulation.json", {
    generated_at: null, n_sims: 0, teams: [],
  });
}

/** Frozen pre-kickoff 1X2 prediction per match (predictions.json only holds
 * scheduled matches, so this archive preserves a match's prediction after kickoff
 * for the post-match card + live calibration). Written by model/predict.py. */
export interface PredArchiveEntry { home: number; draw: number; away: number; locked_at?: string }
export function loadPredictionArchive(): Record<string, PredArchiveEntry> {
  const a = readJson<Record<string, PredArchiveEntry>>("site/public/data/predictions_archive.json", {});
  return a && typeof a === "object" ? a : {};
}

export type Outcome = "home" | "draw" | "away";
/** 1X2 result of a finished match, or null if not yet played. */
export function matchOutcome(m: Match): Outcome | null {
  const s = m.score;
  if (!s || s.home == null || s.away == null) return null;
  return s.home > s.away ? "home" : s.home < s.away ? "away" : "draw";
}

export interface LiveCalBin { lo: number; hi: number; predMean: number | null; obs: number | null; count: number }
export interface LiveCalibration {
  nMatches: number; nEvents: number; brier: number | null; hitRate: number | null; bins: LiveCalBin[];
}
/**
 * Tournament-to-date reliability of the model's *pre-kickoff* 1X2 predictions vs
 * realised outcomes — the honest "is the model staying calibrated on 2026 matches"
 * check. One-vs-rest: each finished match contributes 3 (predicted-prob, occurred)
 * pairs, binned into deciles. Empty until results land.
 */
export function liveCalibration(
  archive: Record<string, PredArchiveEntry>,
  matches: Match[],
): LiveCalibration {
  const bins: LiveCalBin[] = Array.from({ length: 10 }, (_, i) => ({
    lo: i / 10, hi: (i + 1) / 10, predMean: null, obs: null, count: 0,
  }));
  const acc = bins.map(() => ({ ps: 0, hits: 0, n: 0 }));
  let nMatches = 0, nEvents = 0, brierSum = 0, topCorrect = 0;

  for (const m of matches) {
    const actual = matchOutcome(m);
    const p = archive[m.id];
    if (!actual || !p) continue;
    nMatches++;
    const outcomes: Outcome[] = ["home", "draw", "away"];
    let top: Outcome = "home";
    for (const o of outcomes) {
      const prob = p[o];
      const hit = actual === o ? 1 : 0;
      const idx = Math.min(9, Math.max(0, Math.floor(prob * 10)));
      acc[idx].ps += prob; acc[idx].hits += hit; acc[idx].n++;
      brierSum += (prob - hit) ** 2;
      nEvents++;
      if (p[o] > p[top]) top = o;
    }
    if (top === actual) topCorrect++;
  }
  bins.forEach((b, i) => {
    if (acc[i].n) { b.count = acc[i].n; b.predMean = acc[i].ps / acc[i].n; b.obs = acc[i].hits / acc[i].n; }
  });
  return {
    nMatches, nEvents,
    brier: nEvents ? brierSum / nEvents : null,
    hitRate: nMatches ? topCorrect / nMatches : null,
    bins,
  };
}

// ---- Squads (model/fetch_squads.py from Wikipedia) ---------------------------
export interface SquadPlayer {
  no: number | null;
  pos: string;            // GK / DF / MF / FW
  name: string;
  club: string | null;
  caps: number | null;
  goals: number | null;
  age: number | null;
}
export interface Squad { coach: string | null; players: SquadPlayer[] }
export interface SquadsFile { source: string; updated: string; teams: Record<string, Squad> }

export function loadSquads(): SquadsFile {
  return readJson<SquadsFile>("site/public/data/squads.json", { source: "", updated: "", teams: {} });
}

export interface ReliabilityBin {
  lo: number; hi: number;
  mean_pred: number | null;
  mean_obs: number | null;
  count: number;
}
export interface CalibrationReport {
  generated_at: string | null;
  method?: string;
  split?: { since?: string; warmup?: number; val_cutoff?: string };
  constants?: Record<string, number>;
  handset_fallback?: Record<string, number>;
  metrics?: {
    handset?: { label: string; train: any; validation: any };
    fitted?: { label: string; train: any; validation: any };
  };
  overall?: Record<string, number | boolean | number[]>;
  reliability?: ReliabilityBin[];
}

export function loadCalibration() {
  return readJson<CalibrationReport | null>(
    "site/public/data/calibration.json",
    null,
  );
}

export interface NewsItem {
  id: string;
  title: string;
  url: string;
  source: string;
  published_at: string | null;
  summary: string;
  teams: string[];
  is_injury_related: boolean;
}

export function loadNews() {
  return readJson<{ generated_at: string | null; sources: string[]; items: NewsItem[] }>(
    "site/public/data/news.json",
    { generated_at: null, sources: [], items: [] },
  );
}

/** Short relative-ish label for a news timestamp ("3h ago", "Jun 4"). */
export function newsAge(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

// ---- Standings ----------------------------------------------------------

export interface TeamRow {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

/**
 * Build a points table per group from GROUP-stage results.
 * Only matches with status FINISHED or non-null scores count toward records;
 * every seeded team is always listed (so a not-yet-started tournament shows
 * all teams at P0 / 0 pts, in seeded order). Sorted by Pts, then GD, then GF.
 */
export function computeStandings(
  matches: Match[],
  groups: Record<string, string[]>,
): Record<string, TeamRow[]> {
  const out: Record<string, TeamRow[]> = {};

  for (const [letter, teams] of Object.entries(groups)) {
    const rows = new Map<string, TeamRow>();
    teams.forEach((team) => {
      rows.set(team, {
        team, played: 0, won: 0, drawn: 0, lost: 0,
        gf: 0, ga: 0, gd: 0, points: 0,
      });
    });

    const groupMatches = matches.filter(
      (m) =>
        m.stage === "GROUP" &&
        m.group === letter &&
        (m.status === "FINISHED" ||
          (m.score != null && m.score.home != null && m.score.away != null)),
    );

    for (const m of groupMatches) {
      const hs = m.score?.home;
      const as = m.score?.away;
      if (hs == null || as == null) continue;
      const home = rows.get(m.home);
      const away = rows.get(m.away);
      if (!home || !away) continue; // team not in this group's seed list

      home.played++; away.played++;
      home.gf += hs; home.ga += as;
      away.gf += as; away.ga += hs;

      if (hs > as) { home.won++; home.points += 3; away.lost++; }
      else if (hs < as) { away.won++; away.points += 3; home.lost++; }
      else { home.drawn++; away.drawn++; home.points++; away.points++; }
    }

    const sorted = [...rows.values()].map((r) => ({ ...r, gd: r.gf - r.ga }));
    sorted.sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      if (b.gd !== a.gd) return b.gd - a.gd;
      if (b.gf !== a.gf) return b.gf - a.gf;
      // keep seeded order as final tiebreak (stable-ish)
      return teams.indexOf(a.team) - teams.indexOf(b.team);
    });
    out[letter] = sorted;
  }

  return out;
}

/**
 * teamName -> flagcdn ISO 3166-1 alpha-2 code (lowercase).
 * Covers every team in fixtures.json's groups. UK home nations use the
 * special gb-eng / gb-sct / gb-wls codes that flagcdn supports.
 */
export const TEAM_FLAGS: Record<string, string> = {
  // Group A
  "Mexico": "mx",
  "South Africa": "za",
  "South Korea": "kr",
  "Czech Republic": "cz",
  // Group B
  "Canada": "ca",
  "Bosnia & Herzegovina": "ba",
  "Qatar": "qa",
  "Switzerland": "ch",
  // Group C
  "Brazil": "br",
  "Morocco": "ma",
  "Haiti": "ht",
  "Scotland": "gb-sct",
  // Group D
  "USA": "us",
  "Paraguay": "py",
  "Australia": "au",
  "Turkey": "tr",
  // Group E
  "Germany": "de",
  "Curaçao": "cw",
  "Ivory Coast": "ci",
  "Ecuador": "ec",
  // Group F
  "Netherlands": "nl",
  "Japan": "jp",
  "Sweden": "se",
  "Tunisia": "tn",
  // Group G
  "Belgium": "be",
  "Egypt": "eg",
  "Iran": "ir",
  "New Zealand": "nz",
  // Group H
  "Spain": "es",
  "Cape Verde": "cv",
  "Saudi Arabia": "sa",
  "Uruguay": "uy",
  // Group I
  "France": "fr",
  "Senegal": "sn",
  "Iraq": "iq",
  "Norway": "no",
  // Group J
  "Argentina": "ar",
  "Algeria": "dz",
  "Austria": "at",
  "Jordan": "jo",
  // Group K
  "Portugal": "pt",
  "DR Congo": "cd",
  "Uzbekistan": "uz",
  "Colombia": "co",
  // Group L
  "England": "gb-eng",
  "Croatia": "hr",
  "Ghana": "gh",
  "Panama": "pa",
};

export function flagCode(team: string): string | null {
  return TEAM_FLAGS[team] ?? null;
}

/** URL-safe slug for a team name ("Bosnia & Herzegovina" -> "bosnia-and-herzegovina",
 * "Curaçao" -> "curacao"). Used by the per-team SEO landing pages. */
export function teamSlug(name: string): string {
  return name
    .normalize("NFD").replace(/[̀-ͯ]/g, "") // strip accents
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

/** Flat list of every seeded team with its group letter, from fixtures.groups —
 * the canonical 48-team roster the team/group landing pages enumerate. */
export function teamGroups(
  groups: Record<string, string[]>,
): { team: string; group: string }[] {
  return Object.entries(groups).flatMap(([group, teams]) =>
    teams.map((team) => ({ team, group })),
  );
}

/**
 * For a match's per-book odds, find the best (highest) decimal price available
 * for each outcome column, so the UI can highlight the line-shopping winner.
 * Returns { outcomeKey: { price, book } } only for outcomes any book quotes.
 */
/**
 * Outcome columns with a fully-typed accessor that reads the price straight off
 * the matching sub-record. Pairing each key with its own `get` keeps the field
 * access checked by the compiler — no `any`/`keyof` cast that could silently
 * read a totals key off an h2h record (or vice-versa).
 */
export const BOOK_OUTCOMES = [
  { key: "home", get: (b: BookOdds) => b.h2h?.home },
  { key: "draw", get: (b: BookOdds) => b.h2h?.draw },
  { key: "away", get: (b: BookOdds) => b.h2h?.away },
  { key: "over_2_5", get: (b: BookOdds) => b.totals?.over_2_5 },
  { key: "under_2_5", get: (b: BookOdds) => b.totals?.under_2_5 },
] as const;

export function bestBookPrices(
  books: BookOdds[],
): Record<string, { price: number; book: string }> {
  const best: Record<string, { price: number; book: string }> = {};
  for (const b of books) {
    for (const { key, get } of BOOK_OUTCOMES) {
      const price = get(b);
      if (typeof price !== "number") continue;
      if (!best[key] || price > best[key].price) {
        best[key] = { price, book: b.title };
      }
    }
  }
  return best;
}

export function bankrollStats(bets: Bet[]) {
  const settled = bets.filter((b) => b.result && b.result !== "VOID");
  const wins = settled.filter((b) => b.result === "WIN").length;
  const losses = settled.filter((b) => b.result === "LOSS").length;
  const totalStake = settled.reduce((s, b) => s + b.stake, 0);
  const pnl = settled.reduce((s, b) => s + (b.pnl ?? 0), 0);
  const roi = totalStake > 0 ? (pnl / totalStake) * 100 : 0;
  return { wins, losses, count: settled.length, pnl, roi, totalStake };
}

export interface PnlPoint {
  n: number;            // bet number in sequence
  date: string;
  pnl: number;          // cumulative realised P/L
  bankroll: number;     // starting bankroll + cumulative P/L
  label: string;
  result: string;
}

/**
 * Cumulative realised P/L after each settled bet, in chronological order
 * (settled_at, falling back to placed_at). Drives the equity curve. Empty array
 * when nothing has settled yet, so the UI can show a placeholder.
 */
export function pnlSeries(bets: Bet[], startingBankroll: number): PnlPoint[] {
  const settled = bets
    .filter((b) => b.result && b.result !== "VOID" && typeof b.pnl === "number")
    .sort((a, b) =>
      (a.settled_at ?? a.placed_at).localeCompare(b.settled_at ?? b.placed_at),
    );
  let cum = 0;
  return settled.map((b, i) => {
    cum += b.pnl ?? 0;
    return {
      n: i + 1,
      date: (b.settled_at ?? b.placed_at).slice(0, 10),
      pnl: cum,
      bankroll: startingBankroll + cum,
      label: `${b.match_id} ${b.selection}`,
      result: b.result as string,
    };
  });
}

/** A bet is "model"-driven if it carried a >=5% model edge, else "manual". */
export function betSource(b: Bet): "model" | "manual" {
  return typeof b.model_edge_pct === "number" && b.model_edge_pct >= 0.05
    ? "model"
    : "manual";
}

interface PnlSplit {
  bets: number;
  pnl: number;
  stake: number;
  roi: number | null;
}

function splitPnl(bets: Bet[], keyFn: (b: Bet) => string): Record<string, PnlSplit> {
  const out: Record<string, PnlSplit> = {};
  for (const b of bets) {
    const k = keyFn(b);
    const row = (out[k] ??= { bets: 0, pnl: 0, stake: 0, roi: null });
    row.bets++;
    row.pnl += b.pnl ?? 0;
    row.stake += b.stake;
  }
  for (const row of Object.values(out)) {
    row.roi = row.stake > 0 ? (row.pnl / row.stake) * 100 : null;
  }
  return out;
}

/**
 * Closing-line-value + P/L-split stats over the bet log.
 *
 * `beatRate` is the share of CLV-rated bets that beat the de-vigged close
 * (clv_pct > 0); `avgClv` is the mean clv_pct. These only populate once
 * model/clv.py has run against a real closing snapshot, so before any bet is
 * settled they are null and the UI shows an explicit empty state.
 *
 * P/L is also split by SOURCE (model vs manual) and by MARKET so "did the model
 * beat my gut?" and "which markets actually pay?" are both answerable.
 */
// Two-tailed 95% Student-t critical values by df (mirrors model/clv.py). On a
// tiny sample the t-interval is the honest one; t≈1.96 beyond df=30.
const T95: Record<number, number> = {
  1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
  8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.16, 14: 2.145,
  15: 2.131, 16: 2.12, 17: 2.11, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.08,
  22: 2.074, 23: 2.069, 24: 2.064, 25: 2.06, 26: 2.056, 27: 2.052, 28: 2.048,
  29: 2.045, 30: 2.042,
};

/** 95% t-confidence interval for a mean; null for fewer than 2 points. */
export function meanCI(values: number[]): { mean: number; margin: number; low: number; high: number } | null {
  const n = values.length;
  if (n < 2) return null;
  const mean = values.reduce((s, v) => s + v, 0) / n;
  const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / (n - 1);
  const se = Math.sqrt(variance) / Math.sqrt(n);
  const margin = (T95[n - 1] ?? 1.96) * se;
  return { mean, margin, low: mean - margin, high: mean + margin };
}

/**
 * 95% Wilson score interval for a proportion k/n (as PERCENTAGES). This is the
 * honest CI for the CLV beat-rate: a binomial proportion, not a mean — far better
 * behaved on a tiny sample than a normal/t interval (which can run past 0/100%).
 * Returns null for n=0. (quant A3: lead with the beat-rate + its binomial CI rather
 * than the per-bet mean-CLV t-interval, whose variance is heteroskedastic — a couple
 * of longshots dominate it.)
 */
export function wilsonInterval(k: number, n: number, z = 1.96): { low: number; high: number } | null {
  if (n <= 0) return null;
  const p = k / n;
  const z2 = z * z;
  const denom = 1 + z2 / n;
  const center = (p + z2 / (2 * n)) / denom;
  const half = (z / denom) * Math.sqrt((p * (1 - p)) / n + z2 / (4 * n * n));
  return { low: Math.max(0, (center - half) * 100), high: Math.min(100, (center + half) * 100) };
}

export function clvStats(bets: Bet[]) {
  const settled = bets.filter((b) => b.result && b.result !== "VOID");
  const rated = bets.filter((b) => typeof b.clv_pct === "number");
  const positive = rated.filter((b) => (b.clv_pct as number) > 0).length;
  const beatRate = rated.length > 0 ? (positive / rated.length) * 100 : null;
  const clvValues = rated.map((b) => b.clv_pct as number);
  const avgClv =
    rated.length > 0 ? clvValues.reduce((s, v) => s + v, 0) / rated.length : null;
  // Stake-weighted mean CLV — a more robust point estimate than the plain mean,
  // which a couple of high-CLV longshots can dominate (quant A3).
  const stakeSum = rated.reduce((s, b) => s + (b.stake || 0), 0);
  const stakeWeightedClv =
    stakeSum > 0 ? rated.reduce((s, b) => s + (b.stake || 0) * (b.clv_pct as number), 0) / stakeSum : null;
  return {
    rated: rated.length,
    positive,
    beatRate,
    beatRateCI: wilsonInterval(positive, rated.length),  // lead metric: binomial CI
    avgClv,
    avgClvCI: meanCI(clvValues),
    stakeWeightedClv,
    bySource: splitPnl(settled, betSource),
    byMarket: splitPnl(settled, (b) => b.market),
  };
}
