# Trading Command Center — Master Plan

**Author:** Drafted with Claude
**Branch:** `claude/options-trading-system-SIT3P`
**Sprint window:** 10 working days, heavy mode
**Primary deliverable:** Planet Alignment module (`/markets` page)
**Date:** May 6, 2026

---

## Part 1 — Current State Assessment

### What's actually built

You've already shipped Phase 1 and 2. This isn't a greenfield project — it's a maturing system that needs targeted extension. Concretely:

**Backend (FastAPI / SQLAlchemy / Alembic):**

| Module | Status | Notes |
|---|---|---|
| Strategy rules versioning | ✅ Complete | `STRATEGY_RULES_V1` in `config.py` matches the discipline rules from your trade journal |
| Trade CRUD | ✅ Complete | Full lifecycle: open, close, exit reasons, post-mortem fields |
| Trade analytics | ✅ Complete | Equity curve, monthly P&L, breakdowns, risk alerts |
| Daily snapshots | ✅ Complete | `daily_snapshots` table with VIX/SPY context |
| Position model | ✅ Complete | `positions` + `portfolio_history` tables |
| IB connector | ✅ Complete | `ib_insync` with graceful fallback when not installed |
| Price fetcher | ✅ Complete | yfinance with batch + historical |
| Social signals | 🟡 Stub only | Model exists, no fetch/score logic |
| Market research | ❌ Not started | No models, services, or routers — *this is what we're building* |

**Frontend (React / TypeScript / Vite / Tailwind):**

| Page | Status |
|---|---|
| `/` Dashboard | ✅ Working — equity curve, metrics, risk alerts |
| `/trades` Trade Log | ✅ Working — entry/close forms, history table |
| `/portfolio` Portfolio | ✅ Working — positions table, NAV chart |
| `/signals` Social Signals | ❌ Placeholder |
| `/markets` Market Trends | ❌ Placeholder ← **Planet Alignment lives here** |
| `/ai` AI Analysis | ❌ Placeholder |
| `/greeks` Greeks | ❌ Placeholder |

**Infrastructure:**
- Docker Compose: PostgreSQL 16 + Redis 7 + backend + frontend ✅
- Alembic migrations 001 (trades) and 002 (portfolio) ✅
- `.env.example` already lists every API key we'll need ✅

### What this means for the sprint

Three implications shape everything that follows:

1. **The architectural decisions are settled.** FastAPI, SQLAlchemy 2, Pydantic v2, React 18, Tailwind. We extend these patterns — we don't introduce new ones.

2. **The placeholder routes were planned for this exact use case.** `/markets` will become the Planet Alignment heatmap. `/ai` will host the per-stock LLM synthesis. `/signals` will host social signal aggregation.

3. **The data layer is mature enough to support new features without refactoring.** We add new models (`watchlist`, `factor_snapshots`, `alignment_scores`) without touching `trades` or `positions`.

### Gaps that block Planet Alignment

Five concrete gaps need filling, in dependency order:

1. **No fundamentals data layer.** `price_fetcher.py` only handles prices. We need a fundamentals fetcher (P/E, P/B, debt, FCF, sector).
2. **No factor scoring framework.** No code converts raw data into Bull/Bear/Neutral verdicts with thresholds.
3. **No watchlist concept.** Currently every analysis would be ad-hoc per request — we need a tracked universe.
4. **No social/news fetchers.** Reddit, news, analyst sentiment all stubbed at the env level only.
5. **No LLM synthesis service.** The `anthropic` package is in requirements but unused.

---

## Part 2 — Target Architecture

### Module map (where Planet Alignment fits)

```
Trading Command Center
├── Phase 1 ✅ Trade Journal       (trades, strategy rules, analytics)
├── Phase 2 ✅ Portfolio           (positions, IB sync, NAV history)
├── Phase 3 → Planet Alignment    ← THIS SPRINT
│   ├── Watchlist                  (tickers user tracks)
│   ├── Factor scoring engine      (8 factors, rule-based + LLM)
│   ├── Data fetchers              (fundamentals, sector, social, news, analyst)
│   ├── Alignment scoring          (composite scores, weights)
│   └── UI: heatmap + scorecard
├── Phase 4 ⏭ Social Signals       (full Alpha Score, signal-to-trade attribution)
├── Phase 5 ⏭ AI Analysis hub      (deeper LLM workflows, scenario sims)
└── Phase 6 ⏭ Pattern Research     (Euro Premium Fade backtester, IB historical bars)
```

### The Planet Alignment design

Eight factors per ticker. Each produces a numeric score, a verdict (Bull/Bear/Neutral), and a one-line explanation.

| # | Factor | Data sources (free first) | Sprint priority |
|---|---|---|---|
| 1 | **Valuation** | yfinance fundamentals | Day 3 (slice 1) |
| 2 | **Earnings momentum** | yfinance earnings history | Day 5 |
| 3 | **Balance sheet** | yfinance balance sheet | Day 5 |
| 4 | **Sector trend** | yfinance sector ETF prices (XLK, XLF, etc.) | Day 4 |
| 5 | **Technical state** | yfinance OHLCV (RSI, MAs) | Day 4 |
| 6 | **Social signal** | Reddit JSON (no auth needed for read), StockTwits | Day 6 |
| 7 | **Analyst sentiment** | yfinance analyst data | Day 6 |
| 8 | **Catalyst proximity** | yfinance calendar | Day 6 |

**Free sources cover all 8 factors at v1.** Paid upgrades (Unusual Whales, Benzinga) become Phase 4 work.

### Composite score model

Two outputs per ticker:

1. **Alignment Score (-100 to +100)** — weighted average of 8 factors. Default weights are equal (12.5% each). Julien-style weights bump valuation and catalyst higher.

2. **Trade-readiness verdict** — derived from score + warnings:
   - `Strong Long` (score > +50, ≥5 factors aligned bullish)
   - `Long Bias` (+20 to +50)
   - `No Trade` (-20 to +20)
   - `Short Bias` (-50 to -20)
   - `Strong Short` (< -50)
   - Always shows warning flags: high short interest, near earnings binary, IV percentile too high, etc.

### LLM synthesis layer

A "Get Claude's take" button per stock calls the Anthropic API with the factor data and produces a 3-paragraph synthesis:
- Setup summary in plain English
- Strongest bullish argument + strongest bearish argument
- Trade structure recommendation (long/short, time horizon, sizing relative to portfolio rules)

Cost: ~$0.01 per synthesis. Rate-limit to 50/day to keep budget under $1/day.

### Database schema (new tables)

```sql
-- Tickers user tracks
CREATE TABLE watchlist (
  id INTEGER PRIMARY KEY,
  ticker VARCHAR(10) UNIQUE NOT NULL,
  added_at DATETIME DEFAULT NOW(),
  notes TEXT,
  custom_weights JSON,   -- per-ticker factor weights override
  is_active BOOLEAN DEFAULT TRUE
);

-- Raw factor data, refreshed daily
CREATE TABLE factor_snapshots (
  id INTEGER PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  factor_name VARCHAR(30) NOT NULL,   -- valuation, sector_trend, etc.
  snapshot_date DATE NOT NULL,
  raw_data JSON NOT NULL,             -- e.g. {"pe": 48, "pe_5y_avg": 30, "sector_pe_median": 17}
  score INTEGER,                      -- -100 to +100
  verdict VARCHAR(10),                -- bull | bear | neutral
  explanation TEXT,                   -- one-line human summary
  source VARCHAR(20),                 -- yfinance | reddit | newsapi | manual
  created_at DATETIME DEFAULT NOW(),
  UNIQUE(ticker, factor_name, snapshot_date)
);

-- Composite scores (one per ticker per day)
CREATE TABLE alignment_scores (
  id INTEGER PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  snapshot_date DATE NOT NULL,
  composite_score INTEGER,            -- -100 to +100
  verdict VARCHAR(20),                -- strong_long | long_bias | no_trade | short_bias | strong_short
  factor_scores JSON,                 -- {"valuation": -45, "sector": +20, ...}
  warnings JSON,                      -- ["high_short_interest", "near_earnings"]
  llm_synthesis TEXT,                 -- optional Claude output, populated on demand
  llm_synthesis_at DATETIME,
  created_at DATETIME DEFAULT NOW(),
  UNIQUE(ticker, snapshot_date)
);
```

This is migration `003_planet_alignment.py` — additive only, doesn't touch existing tables.

### API contract

```
GET    /api/v1/watchlist                      List all watched tickers
POST   /api/v1/watchlist                      Add ticker
DELETE /api/v1/watchlist/{ticker}             Remove ticker
PATCH  /api/v1/watchlist/{ticker}             Update notes/weights

GET    /api/v1/markets/heatmap                All watchlist tickers with latest scores
GET    /api/v1/markets/{ticker}                Full scorecard (8 factors detailed)
POST   /api/v1/markets/{ticker}/refresh        Force refresh of all factors
POST   /api/v1/markets/{ticker}/synthesize     Call Claude for LLM synthesis
GET    /api/v1/markets/{ticker}/history        Historical scores (last 30 days)

POST   /api/v1/markets/scan-all                Trigger nightly scan of all watchlist
                                               (cron-callable; also exposed for manual run)
```

### Frontend pages

**`/markets` — Heatmap view (entry point)**

- Grid of cards, one per watchlist ticker
- Each card shows: ticker, current price, composite score (color-coded -100 red to +100 green), verdict label, top 2 warnings
- Filters: show only `Strong Long` / `Strong Short` / has warnings
- "Refresh all" button triggers backend scan-all
- Clicking a card → scorecard

**`/markets/{ticker}` — Scorecard view**

- Header: ticker, price, sector, composite score, verdict
- 8 factor rows, each expandable:
  - Score bar (visual -100 to +100)
  - Verdict pill (Bull/Bear/Neutral)
  - One-line explanation
  - Expand → raw data behind the score
- "Get Claude's take" button → LLM synthesis (cached for 24h)
- "Open trade entry pre-filled" button → jump to `/trades/new?ticker=X` with thesis pre-populated from scorecard
- 30-day score history sparkline at bottom

### Integration with trade entry

When user clicks "Open trade entry pre-filled" from a scorecard, the trade entry form pre-populates:
- `ticker`, `sector`, `underlying_price_entry`
- `thesis` (auto-generated: "Planet alignment scorecard {date}: composite {score}, verdict {verdict}, key factors: ...")
- `market_trend`, `sector_trend` from factor data
- `iv_percentile` if available
- Rule compliance pre-checked items based on factor warnings

This closes the loop: research → entry decision → logged trade → post-mortem references back to the alignment snapshot.

---

## Part 3 — 10-Day Sprint Plan

Days are working days, ~6-8h heavy focus each. "Definition of done" means tested + merged to feature branch.

### Day 1 (Mon) — Foundation: schema + watchlist CRUD

**Goal:** New tables exist, watchlist is fully functional.

- [ ] Create `backend/app/models/markets.py` with `Watchlist`, `FactorSnapshot`, `AlignmentScore`
- [ ] Create `backend/app/schemas/markets.py` with Pydantic schemas
- [ ] Create alembic migration `003_planet_alignment.py`
- [ ] Run migration locally on SQLite
- [ ] Create `backend/app/routers/markets.py` with watchlist CRUD endpoints
- [ ] Wire router into `main.py`
- [ ] Write tests: `test_watchlist_crud.py`
- [ ] Manual smoke test: add NVDA, GOOG, AMZN, MSFT, TSLA via curl

**Done when:** `curl localhost:8000/api/v1/watchlist` returns the 5 tickers.

### Day 2 (Tue) — Fundamentals data fetcher

**Goal:** `fundamentals_fetcher.py` returns clean fundamentals for any US ticker.

- [ ] Create `backend/app/services/fundamentals_fetcher.py`
- [ ] Implement `get_fundamentals(ticker) -> dict` using `yfinance.Ticker.info` and `.financials`
- [ ] Returns: `pe_trailing`, `pe_forward`, `pb`, `debt_to_equity`, `current_ratio`, `fcf_ttm`, `revenue_growth`, `eps_growth`, `sector`, `industry`, `market_cap`, `analyst_target_mean`, `analyst_count`, `recommendation_mean`
- [ ] Handle missing data gracefully (yfinance is inconsistent; many fields can be None)
- [ ] Add caching: 24h TTL via simple file cache or Redis (Redis is already in compose)
- [ ] Tests with VCR-style cassettes for 3 tickers (NVDA, GOOG, TSLA)

**Done when:** `python -c "from app.services.fundamentals_fetcher import get_fundamentals; print(get_fundamentals('NVDA'))"` returns clean dict.

### Day 3 (Wed) — Factor 1: Valuation scorer + first integration test

**Goal:** Valuation factor produces a real score for any ticker.

- [ ] Create `backend/app/services/factor_scorers/__init__.py` (factor scorer pattern)
- [ ] Create `backend/app/services/factor_scorers/valuation.py`
- [ ] Implement `score_valuation(ticker, fundamentals) -> FactorScore`
  - Inputs: P/E vs 5y avg, P/E vs sector median, PEG, analyst target gap
  - Output: score (-100..+100), verdict (bull/bear/neutral), explanation
  - Thresholds documented inline (e.g., "P/E > 1.5x sector → -30; > 2x → -50")
- [ ] Create `score_and_persist(ticker, factor_name)` orchestrator that:
  1. Fetches data
  2. Calls factor scorer
  3. Saves a `FactorSnapshot` row
- [ ] Endpoint: `POST /api/v1/markets/{ticker}/refresh` runs all factors (only valuation today)
- [ ] Endpoint: `GET /api/v1/markets/{ticker}` returns latest snapshot
- [ ] Tests: `test_valuation_scorer.py` with synthetic fundamentals data

**Done when:** Hit refresh endpoint for WMT, get back `{"valuation": {"score": -45, "verdict": "bear", "explanation": "P/E 48x vs sector median 17x; trades 60% above 5yr avg"}}`.

### Day 4 (Thu) — Factors 4 & 5: Sector trend + Technical

**Goal:** Two more factors live. Heatmap data is starting to look useful.

- [ ] Create `backend/app/services/factor_scorers/sector_trend.py`
  - Map ticker → sector ETF (NVDA → XLK, JPM → XLF, etc.)
  - Compute 1M, 3M, 6M ETF returns
  - Compare to SPY same-period returns (sector relative strength)
  - Score: outperforming + accelerating = +50; underperforming + decelerating = -50
- [ ] Create `backend/app/services/factor_scorers/technical.py`
  - RSI(14) — pull from yfinance OHLCV + computed locally
  - Distance from 50-day and 200-day moving averages
  - Distance from 52w high/low
  - Score logic: overbought RSI + extended from MA = bearish bias and vice versa
- [ ] Update `score_and_persist` orchestrator to handle multiple factors
- [ ] Add caching layer (Redis): factor snapshots cached for 4h during market hours, 24h otherwise

**Done when:** All 5 watchlist tickers have valuation + sector_trend + technical snapshots in DB.

### Day 5 (Fri) — Factors 2 & 3: Earnings momentum + Balance sheet

**Goal:** Five factors complete. Backend-only sprint until Day 7.

- [ ] Create `backend/app/services/factor_scorers/earnings_momentum.py`
  - Last 4 quarter beats vs misses (yfinance earnings history)
  - Revenue growth trend (accelerating/decelerating)
  - EPS revisions trend
  - Score reflects positive surprise momentum
- [ ] Create `backend/app/services/factor_scorers/balance_sheet.py`
  - Debt/EBITDA, current ratio, FCF trajectory, cash position
  - Score reflects financial health (good = +, distressed = -)
- [ ] Composite score calculator: `compute_alignment_score(ticker)` writes to `alignment_scores` table
- [ ] Endpoint: `POST /api/v1/markets/scan-all` runs full scan on all watchlist tickers
- [ ] Tests for both new scorers

**Done when:** Composite score computed and stored for all watchlist tickers.

### Day 6 (Mon week 2) — Factors 6, 7, 8: Social, Analyst, Catalyst

**Goal:** All 8 factors live. Backend feature-complete.

- [ ] **Social** (`social_signal.py`): Reddit JSON API (no auth) — count mentions in r/wallstreetbets, r/stocks, r/options last 7 days. Sentiment proxy via mention velocity.
- [ ] **Analyst** (`analyst_sentiment.py`): yfinance analyst data — buy/hold/sell ratio, recent rating changes (use `recommendations_summary`), target dispersion
- [ ] **Catalyst** (`catalyst_proximity.py`): Days to next earnings, ex-div, known events. Score reflects proximity to high-uncertainty events (close = elevated risk = neutral score with warning flag)
- [ ] Warning flag system: each factor can emit warnings (`high_short_interest`, `near_earnings`, `iv_extremely_high`, etc.)
- [ ] Update composite scorer to incorporate warnings into verdict logic

**Done when:** All 8 factors run successfully on the watchlist. `GET /api/v1/markets/heatmap` returns rich data.

### Day 7 (Tue) — Frontend: Heatmap page

**Goal:** `/markets` page shows real data.

- [ ] Replace `/markets` placeholder with `MarketsHeatmap.tsx`
- [ ] Create `frontend/src/hooks/useMarkets.ts` (`useWatchlist`, `useHeatmap`, `useScorecard`)
- [ ] Create `frontend/src/components/markets/HeatmapCard.tsx`
  - Score bar (color gradient red→neutral→green)
  - Verdict pill
  - Top 2 warnings as small badges
- [ ] Filters: dropdown for verdict, toggle for "has warnings"
- [ ] "Refresh all" button → POST `/api/v1/markets/scan-all`, show loading state
- [ ] "Add ticker" inline form
- [ ] Update sidebar — remove "coming in a later phase" placeholder

**Done when:** You can open the app, see all your watchlist tickers in a grid with live colored scores.

### Day 8 (Wed) — Frontend: Scorecard page

**Goal:** Click-through detail view works end-to-end.

- [ ] Create `frontend/src/pages/MarketScorecard.tsx` at route `/markets/:ticker`
- [ ] Add route to `App.tsx`
- [ ] Header section: ticker, price, sector, composite score, verdict
- [ ] 8 factor rows component (`FactorRow.tsx`) — each expandable to show raw data
- [ ] 30-day score history sparkline (recharts LineChart)
- [ ] Warning flags banner at top if any
- [ ] Responsive: works on desktop, decent on tablet

**Done when:** Click WMT card → see full scorecard with 8 factors, expand any factor to see raw P/E data, sparkline shows score history.

### Day 9 (Thu) — LLM synthesis + trade entry integration

**Goal:** "Get Claude's take" works. Trade entry pre-fill works.

- [ ] Create `backend/app/services/llm_synthesizer.py`
- [ ] Implement `synthesize_for_ticker(ticker) -> str` using `anthropic` package
  - Build prompt from latest `AlignmentScore` + all `FactorSnapshot` records
  - Cache result for 24h (write to `alignment_scores.llm_synthesis`)
  - Rate limit: 50 calls/day via simple counter in Redis
- [ ] Endpoint: `POST /api/v1/markets/{ticker}/synthesize`
- [ ] Frontend: "Get Claude's take" button on scorecard
- [ ] Show synthesis in collapsible panel; show "regenerate" if older than 24h
- [ ] Trade entry pre-fill:
  - "Open trade entry pre-filled" button on scorecard
  - Navigate to `/trades?prefill=NVDA` (read query param)
  - `TradeEntryForm` reads prefill param, calls `GET /api/v1/markets/{ticker}` to populate fields
  - Auto-generate thesis text from scorecard

**Done when:** Click "Get Claude's take" → 3-paragraph synthesis appears. Click "Open trade entry pre-filled" → trade form opens with ticker, sector, IV, thesis populated.

### Day 10 (Fri) — Polish, scheduled scans, docs

**Goal:** Production-ready for personal use. Daily scans run automatically.

- [ ] Background task scheduling: simple cron-style approach using `apscheduler` (lightweight, no Celery/Redis worker needed for v1)
  - Daily at 7am Paris time: scan all watchlist tickers
  - Skip weekends
- [ ] Add `/api/v1/markets/scan-status` endpoint showing last scan time per ticker
- [ ] Error handling pass: every scorer wraps in try/except, logs failures, continues with other factors
- [ ] Add seed data: pre-populate watchlist with the tickers from your trade journal (NVDA, GOOG, AMZN, MSFT, WMT, TSLA, INTC, SPOT, ASML, BNP)
- [ ] Update `README.md` with Planet Alignment section: setup, how to use, what each factor means
- [ ] Smoke test the full flow: add ticker → scan runs → heatmap updates → click scorecard → click synthesize → click pre-fill trade
- [ ] Tag release `v0.3.0` on the feature branch

**Done when:** A complete user flow works without any manual backend tinkering. README documents the new module. Branch is ready to merge.

### Buffer days (if needed)

If something slips, the cuts in priority order:

1. **Cut LLM synthesis caching** to next sprint (still works, just costs more)
2. **Cut sparkline history** (just show current score)
3. **Cut Day 10 scheduler**, run scans manually for first week
4. **Cut social factor** to v2 — Reddit JSON parsing can be flaky

Do NOT cut: any of the 5 core factors (valuation, earnings, balance sheet, sector, technical), the heatmap UI, or the scorecard UI. Those define the product.

---

## Part 4 — Planet Alignment Full Spec

### The 8 factors in detail

#### 1. Valuation
**Goal:** Is the stock priced reasonably given its earnings, growth, and peers?

**Inputs:**
- Trailing P/E ratio (from yfinance)
- Forward P/E ratio
- 5-year average P/E (computed from historical earnings × historical prices, or pulled from yfinance if available)
- Sector median P/E (lookup table by GICS sector)
- PEG ratio
- Analyst average target vs current price

**Scoring:**
| Condition | Score contribution |
|---|---|
| P/E > 2x sector median | -30 |
| P/E > 1.5x sector median | -20 |
| P/E within ±20% sector median | 0 |
| P/E < 0.7x sector median (and earnings positive) | +20 |
| Current price > analyst PT mean | -10 to -20 (linear with gap %) |
| Current price < 80% of analyst PT mean | +20 |
| PEG > 2 | -15 |
| PEG < 1 | +15 |

Sum, clamp to [-100, +100].

**Verdict thresholds:** score < -30 = bear, > +30 = bull, else neutral.

#### 2. Earnings momentum
**Goal:** Are recent earnings results building positive or negative narrative momentum?

**Inputs:**
- Last 4 quarterly EPS beats/misses (yfinance `earnings_history`)
- Revenue growth trajectory (last 4 quarters YoY)
- Forward EPS revisions trend (analyst estimate changes — if not available, skip this sub-factor)

**Scoring:** beat-rate, magnitude of beats, revenue acceleration/deceleration.

#### 3. Balance sheet health
**Goal:** Can this company survive a downturn?

**Inputs:** debt-to-equity, current ratio, FCF (TTM), cash position, interest coverage if computable.

**Scoring:** distress indicators add negative score; strong cash + low debt adds positive.

#### 4. Sector trend
**Goal:** Is the sector working with you or against you?

**Inputs:**
- Map ticker to sector ETF (lookup table: tech→XLK, financials→XLF, etc.)
- 1M, 3M, 6M returns of sector ETF
- Compare to SPY same period (sector relative strength)
- Sector RSI

**Scoring:** outperforming + uptrending = +; underperforming + downtrending = -.

#### 5. Technical state
**Goal:** Is the chart in a position to support entry, or is it overextended?

**Inputs:**
- RSI(14)
- Distance from 50-day and 200-day moving averages
- Distance from 52w high and 52w low
- 20-day price volatility

**Scoring:** stretched extremes = neutral or counter-trend bias; healthy trend = pro-trend bias.

#### 6. Social signal
**Goal:** Is retail attention building or fading? (Note: this is a contrarian indicator at extremes.)

**Inputs:**
- Reddit mention volume (r/wallstreetbets, r/stocks, r/options) past 7 days vs prior 7 days
- StockTwits sentiment score (if API key available, else skip)
- Mention velocity (acceleration of mentions)

**Scoring nuance:** moderate growing attention = +; explosive viral attention (>500% mention spike) = -50 with warning flag (peak euphoria signal).

#### 7. Analyst sentiment
**Goal:** What does Wall Street think, and is consensus changing?

**Inputs:**
- Buy/Hold/Sell ratio (yfinance `recommendations`)
- Recent rating changes (last 30 days)
- Target price dispersion (high/low spread relative to mean — wide = uncertainty)
- Recommendation mean (1=Strong Buy, 5=Strong Sell)

**Scoring:** rising buy ratio + tight target dispersion = bullish; downgrades + widening dispersion = bearish.

#### 8. Catalyst proximity
**Goal:** What's coming up that could move the stock?

**Inputs:**
- Days to next earnings
- Days to ex-dividend
- Known calendar events (FDA dates for biotech, product launches if available)

**Scoring:** This factor is often *neutral with warnings* — proximity to earnings doesn't determine direction, it determines risk profile. Inside 7 days = `near_earnings_warning`.

### Composite scoring algorithm

```python
def compute_composite(factor_scores: dict, weights: dict | None = None) -> dict:
    """
    factor_scores: {"valuation": -45, "sector_trend": 20, ...}
    weights: optional {"valuation": 0.20, ...}, defaults to equal (0.125 each)
    """
    if weights is None:
        weights = {f: 1/len(factor_scores) for f in factor_scores}

    composite = sum(score * weights[f] for f, score in factor_scores.items())
    composite = max(-100, min(100, composite))

    # Count alignment
    bullish = sum(1 for s in factor_scores.values() if s > 30)
    bearish = sum(1 for s in factor_scores.values() if s < -30)

    # Verdict logic
    if composite > 50 and bullish >= 5:
        verdict = "strong_long"
    elif composite > 20:
        verdict = "long_bias"
    elif composite < -50 and bearish >= 5:
        verdict = "strong_short"
    elif composite < -20:
        verdict = "short_bias"
    else:
        verdict = "no_trade"

    return {
        "composite_score": int(composite),
        "verdict": verdict,
        "bullish_count": bullish,
        "bearish_count": bearish,
    }
```

### LLM synthesis prompt template

```
You are advising Julien, an experienced corporate finance professional and
catalyst-driven trader. He uses warrants and options on Paris-listed
exchanges, with positions typically held weeks to months.

Below is the planet alignment data for {TICKER} as of {DATE}.

Composite score: {COMPOSITE} ({VERDICT})
Current price: {PRICE}
Sector: {SECTOR}

Factor breakdown:
{FACTOR_TABLE}

Warnings: {WARNINGS}

His current portfolio:
{PORTFOLIO_SUMMARY}

His active rules (excerpt):
- Max position size: 10% of portfolio (€{MAX_SIZE} at current portfolio)
- Test position max: €300
- No new positions when portfolio < €9,000
- 24h blackout after realized loss
- No binary earnings bets the week of earnings
- No Paris warrant trading 9:00-16:30 CET after US earnings

Provide a 3-paragraph analysis:
1. What the planet alignment tells us about this setup
2. The strongest bullish argument and the strongest bearish argument
3. A specific trade structure recommendation (or "no trade") that respects
   his rules — including instrument type, expiry, strike, sizing, stop,
   and what could invalidate the thesis

Be direct. If this isn't a good setup, say so plainly.
```

---

## Part 5 — First Implementation Slice (ready to start Day 1)

To remove ambiguity for Day 1, here's the actual code for the first three deliverables.

### Migration `003_planet_alignment.py`

```python
"""Add Planet Alignment tables — Phase 3

Revision ID: 003
Revises: 002
Create Date: 2026-05-06
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False, unique=True),
        sa.Column("added_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text),
        sa.Column("custom_weights", sa.JSON),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
    )
    op.create_index("ix_watchlist_ticker", "watchlist", ["ticker"])

    op.create_table(
        "factor_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("factor_name", sa.String(30), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("raw_data", sa.JSON, nullable=False),
        sa.Column("score", sa.Integer),
        sa.Column("verdict", sa.String(10)),
        sa.Column("explanation", sa.Text),
        sa.Column("source", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.UniqueConstraint("ticker", "factor_name", "snapshot_date",
                            name="uq_factor_snapshot"),
    )
    op.create_index("ix_factor_ticker_date", "factor_snapshots",
                    ["ticker", "snapshot_date"])

    op.create_table(
        "alignment_scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("composite_score", sa.Integer),
        sa.Column("verdict", sa.String(20)),
        sa.Column("factor_scores", sa.JSON),
        sa.Column("warnings", sa.JSON),
        sa.Column("llm_synthesis", sa.Text),
        sa.Column("llm_synthesis_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.UniqueConstraint("ticker", "snapshot_date",
                            name="uq_alignment_score"),
    )
    op.create_index("ix_alignment_ticker_date", "alignment_scores",
                    ["ticker", "snapshot_date"])


def downgrade() -> None:
    op.drop_index("ix_alignment_ticker_date", "alignment_scores")
    op.drop_table("alignment_scores")
    op.drop_index("ix_factor_ticker_date", "factor_snapshots")
    op.drop_table("factor_snapshots")
    op.drop_index("ix_watchlist_ticker", "watchlist")
    op.drop_table("watchlist")
```

### Models `backend/app/models/markets.py`

```python
"""Planet Alignment models — Phase 3."""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, JSON, String, Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    added_at = Column(DateTime, server_default=func.now())
    notes = Column(Text)
    custom_weights = Column(JSON)
    is_active = Column(Boolean, default=True)


class FactorSnapshot(Base):
    __tablename__ = "factor_snapshots"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    factor_name = Column(String(30), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    raw_data = Column(JSON, nullable=False)
    score = Column(Integer)
    verdict = Column(String(10))
    explanation = Column(Text)
    source = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "factor_name", "snapshot_date",
                         name="uq_factor_snapshot"),
    )


class AlignmentScore(Base):
    __tablename__ = "alignment_scores"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    composite_score = Column(Integer)
    verdict = Column(String(20))
    factor_scores = Column(JSON)
    warnings = Column(JSON)
    llm_synthesis = Column(Text)
    llm_synthesis_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "snapshot_date", name="uq_alignment_score"),
    )
```

### Schemas `backend/app/schemas/markets.py`

```python
"""Pydantic schemas for Planet Alignment."""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class WatchlistCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    notes: Optional[str] = None
    custom_weights: Optional[dict[str, float]] = None


class WatchlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticker: str
    added_at: datetime
    notes: Optional[str] = None
    custom_weights: Optional[dict[str, float]] = None
    is_active: bool


class FactorSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    factor_name: str
    snapshot_date: date
    raw_data: dict[str, Any]
    score: Optional[int] = None
    verdict: Optional[str] = None
    explanation: Optional[str] = None
    source: Optional[str] = None


class AlignmentScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ticker: str
    snapshot_date: date
    composite_score: Optional[int] = None
    verdict: Optional[str] = None
    factor_scores: Optional[dict[str, int]] = None
    warnings: Optional[list[str]] = None
    llm_synthesis: Optional[str] = None
    llm_synthesis_at: Optional[datetime] = None


class HeatmapEntry(BaseModel):
    """One row of the heatmap view."""
    ticker: str
    current_price: Optional[float] = None
    composite_score: Optional[int] = None
    verdict: Optional[str] = None
    top_warnings: list[str] = Field(default_factory=list)
    last_updated: Optional[datetime] = None


class ScorecardResponse(BaseModel):
    """Full scorecard for one ticker."""
    ticker: str
    sector: Optional[str] = None
    current_price: Optional[float] = None
    snapshot_date: date
    composite_score: Optional[int] = None
    verdict: Optional[str] = None
    factor_scores: dict[str, int] = Field(default_factory=dict)
    factor_details: list[FactorSnapshotResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    score_history_30d: list[dict] = Field(default_factory=list)
    llm_synthesis: Optional[str] = None
    llm_synthesis_at: Optional[datetime] = None
```

### Day 1 commands to execute

```bash
# In your project root, on the feature branch
cd backend

# Create the new files
touch app/models/markets.py app/schemas/markets.py app/routers/markets.py
touch alembic/versions/003_planet_alignment.py
touch tests/test_watchlist_crud.py

# (paste the code from this plan into each file)

# Wire up in main.py — add:
#   from app.models import markets as _market_models  # noqa: F401
#   from app.routers import markets
#   app.include_router(markets.router, prefix="/api/v1")

# Run migration
alembic upgrade head

# Verify
sqlite3 trading.db ".schema watchlist"
sqlite3 trading.db ".schema factor_snapshots"
sqlite3 trading.db ".schema alignment_scores"

# Run tests
pytest tests/test_watchlist_crud.py -v

# Smoke test the API
uvicorn app.main:app --reload &
curl -X POST localhost:8000/api/v1/watchlist \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","notes":"AI infrastructure conviction"}'
curl localhost:8000/api/v1/watchlist
```

---

## Risks & open questions

### Things that could derail the sprint

1. **yfinance reliability.** Rate limits, missing data fields, occasional breakage. Mitigation: file-based cache with 24h TTL means a single failed fetch doesn't block the day's analysis.

2. **Reddit API changes.** Reddit has historically tightened access. Mitigation: keep social factor optional (composite score works with N-1 factors), and Pushshift-style alternatives exist as backup.

3. **LLM cost runaway.** A loop bug calling synthesis repeatedly could rack up costs. Mitigation: hard rate limit 50/day in Redis, plus per-ticker 24h cache.

4. **Frontend velocity.** If you're more comfortable in backend than React, Days 7-9 could slip. Mitigation: the heatmap can ship as a server-rendered HTML page initially (FastAPI templates) and be Reactified later.

### Decisions you should make before Day 1

1. **Database for dev:** SQLite (faster iteration) vs Postgres via Docker (matches prod). Recommend SQLite for solo dev sprint; switch to Postgres for production.

2. **Frontend dev mode:** Run `npm run dev` outside Docker (faster HMR) vs full Docker compose. Recommend outside for sprint speed.

3. **LLM model:** Claude 4.6 Sonnet (cheaper, faster) vs Claude 4.7 Opus (smarter, costlier). Recommend Sonnet for default, Opus toggleable via env var when you want premium analysis.

4. **Watchlist seed:** Confirm starting universe — I'd suggest the 10 from your trade journal (NVDA, GOOG, AMZN, MSFT, WMT, TSLA, INTC, SPOT, ASML, BNP) plus 5 you're researching (CAR, VST, MU, AAPL, SBUX).

### Out of scope for this sprint (Phase 4+ work)

- Pattern research / European Premium Fade backtester (Phase 6)
- Real-time options Greeks (Phase 5)
- Full Social Signals page with Alpha Score (Phase 4)
- Paid data integrations (Unusual Whales, Benzinga)
- Mobile-optimized UI
- Multi-user auth (single-user assumption)
- Historical IB tick data ingestion
- Automated execution — this remains a research+journal tool, not an order-routing system

---

## Sprint readiness checklist

Before you start Day 1, confirm:

- [ ] Branch `claude/options-trading-system-SIT3P` is current
- [ ] Local environment runs (`docker-compose up` or local Python + Postgres)
- [ ] Existing tests pass (`pytest backend/tests`)
- [ ] You've got at least one Anthropic API key in `.env` (for Day 9)
- [ ] You've decided on dev DB (SQLite vs Postgres)
- [ ] You've blocked time on calendar — ~6h/day for 10 working days
- [ ] You've confirmed the 15-ticker starting watchlist
- [ ] The trade journal spreadsheet from earlier is available as reference

---

*This document is a living plan. Update it as you ship — strike through completed items, add a "Day N retro" note when reality differs from plan, and use it to keep yourself honest about scope creep.*
