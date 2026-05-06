# Trading Command Center — Architecture

**Status:** Active development (Phase 3 of 7)
**Branch:** `claude/options-trading-system-SIT3P`
**Owner:** Single user (Julien) — solo retail trader, ~€8,300 portfolio
**Stack:** Python 3.11 / FastAPI / SQLAlchemy 2 / React 18 / TypeScript / Vite / Tailwind

This document is the single source of truth for design rules. If a new feature
violates a rule here, either justify it in the PR description and update this
document, or pick a different approach.

---

## 1. Project structure

```
trading-command-center/
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/         # 001_initial, 002_portfolio, 003_planet_alignment, …
│   ├── app/
│   │   ├── main.py           # FastAPI app, router registration, on_startup seeds
│   │   ├── config.py         # Settings + STRATEGY_RULES_V1 + RULE_CHECKLIST
│   │   ├── database.py       # engine, SessionLocal, Base, get_db
│   │   ├── models/           # SQLAlchemy models (one file per domain)
│   │   ├── schemas/          # Pydantic v2 request/response schemas
│   │   ├── routers/          # FastAPI routers (one file per domain, REST verbs)
│   │   ├── services/         # Business logic — never import from routers
│   │   │   └── factor_scorers/   # Planet Alignment factors
│   │   └── utils/            # Pure helpers, no app dependencies
│   └── tests/                # pytest, mirror app/ structure
├── frontend/
│   └── src/
│       ├── pages/            # Top-level routed components (TradeLog, Portfolio, …)
│       ├── components/       # Reusable, organized by feature folder
│       ├── hooks/            # useTrades, usePortfolio, useMarkets …
│       ├── types/            # TypeScript interfaces — mirror backend schemas
│       └── lib/              # api client, formatters, constants
├── docker-compose.yml
├── ARCHITECTURE.md           # ← this file
└── .claude/
    └── TCC_MASTER_PLAN_ADDITIONAL_CONTEXT.md
```

**Rule 1.1** — One model file per domain (`trades.py`, `portfolio.py`, `markets.py`,
`social.py`). No god-models.

**Rule 1.2** — Every new domain ships in lockstep: model + schema + router +
tests. No "add the model now, schema later."

**Rule 1.3** — Mirror `backend/app/services/X` with `backend/tests/test_X.py`.
Discoverable by name.

---

## 2. Layering & dependencies

```
┌──────────────────────────────────────────────┐
│  routers/        thin HTTP layer             │
│   ↓ depends on                               │
│  services/       business logic              │
│   ↓ depends on                               │
│  models/, schemas/, database/, utils/        │
└──────────────────────────────────────────────┘
```

**Rule 2.1** — Routers are thin. They (a) parse input via Pydantic, (b) call a
service function, (c) return a Pydantic response. No business rules in routers.

**Rule 2.2** — Services never import from `routers/`. Services may import models,
schemas, other services, and utils.

**Rule 2.3** — Models never import from services or routers. Models are dumb
data containers + relationships.

**Rule 2.4** — Schemas never import from models. They're transport-only. Use
`ConfigDict(from_attributes=True)` for ORM → schema conversion.

**Rule 2.5** — `services/` is where I/O lives (yfinance, IB, Anthropic, file
cache). Each external dependency has exactly one wrapper module — no scattered
`yf.Ticker(...)` calls across the codebase.

---

## 3. Database & migrations

**Rule 3.1** — SQLite for dev, PostgreSQL for prod. Both must work. No SQLite-only
features (no `STRICT` mode, no `JSON1` extensions beyond what SQLAlchemy emulates).

**Rule 3.2** — Every schema change ships as an Alembic migration. Numbered
sequentially (`001_initial_schema.py`, `002_portfolio_tables.py`, `003_planet_alignment.py`).
Never edit a merged migration; always add a new one.

**Rule 3.3** — Migrations are reversible. Every `upgrade()` has a working `downgrade()`.

**Rule 3.4** — Use `server_default=sa.func.now()` for timestamps, not `now()` SQL
literal — works on both SQLite and Postgres. Use `sa.text("1")` / `sa.text("0")`
for boolean defaults.

**Rule 3.5** — Index columns that appear in `WHERE`, `JOIN`, or `ORDER BY` of
high-traffic queries: ticker, snapshot_date, status, entry_datetime.

**Rule 3.6** — `UniqueConstraint` for composite uniqueness (e.g. `(ticker,
factor_name, snapshot_date)` in `factor_snapshots`). Always name them
(`uq_factor_snapshot`).

**Rule 3.7** — JSON columns for flexible payloads (raw_data, factor_scores,
warnings, custom_weights, rules_followed). Don't model nested structures as
relational tables unless you query into them.

**Rule 3.8** — Soft-delete (set `is_active=False`) for user-facing data
(watchlist, positions). Hard-delete only for clearly transient/derived data.

---

## 4. Validation & schemas

**Rule 4.1** — Pydantic v2, not v1. Use `ConfigDict`, `Field`, validators decorated
with `@field_validator`.

**Rule 4.2** — Three schema variants per resource:
- `XCreate` — POST input (required fields only)
- `XUpdate` — PATCH input (all fields optional)
- `XResponse` — output (full shape including computed fields)

**Rule 4.3** — Tickers are uppercased and trimmed at the schema layer. Never
trust raw input.

**Rule 4.4** — Cross-field validation in services, not schemas, when it requires
DB lookups (e.g. "no new positions if portfolio < €9000"). Schemas only validate
self-contained shape.

**Rule 4.5** — Reject `extra` fields in schemas by default — silently ignoring
extras hides typos.

---

## 5. Error handling

**Rule 5.1** — HTTPException with the right status code from routers:
- 400 — bad request shape (Pydantic handles this)
- 404 — resource not found
- 409 — conflict (duplicate, blackout active)
- 422 — validation (Pydantic handles this)
- 500 — unexpected; let it propagate, FastAPI logs

**Rule 5.2** — External I/O (yfinance, IB, Anthropic) wraps in try/except, logs
the exception, returns a sentinel value (None, empty list, dict with `"error"`
key). Network blips do not 500 the API.

**Rule 5.3** — Factor scorers must NEVER raise. They return `FactorScore` even
on missing data — with `score=None, verdict="neutral", explanation="insufficient
data"`. One bad factor doesn't kill the whole scan.

**Rule 5.4** — Database errors propagate. If the DB is down, return 500 — that's
the correct signal.

---

## 6. External integrations

| Integration | Module | Failure mode |
|---|---|---|
| yfinance | `services/price_fetcher.py`, `services/fundamentals_fetcher.py` | Returns None / empty dict + log |
| Interactive Brokers | `services/ib_connector.py` | `HAS_IB` flag, graceful fallback when not installed |
| Anthropic | `services/llm_synthesizer.py` (Day 9) | Rate-limited (50/day), 24h cache |
| Reddit JSON | `services/social_fetcher.py` (Day 6) | Optional factor — skipped if unavailable |

**Rule 6.1** — Each external dep is `try: import X except ImportError` guarded.
The app boots even when optional deps are missing.

**Rule 6.2** — Every external call goes through file-based cache (24h TTL for
fundamentals, 4h during market hours for prices) before hitting the network.

**Rule 6.3** — Never put API keys or secrets in code. Always `.env` via
`pydantic-settings`. Optional fields use `Optional[str] = None`.

---

## 7. Planet Alignment (Phase 3) specifics

### 7.1 Factor scorer pattern

Every factor scorer is a function that returns a `FactorScore` dataclass:

```python
@dataclass
class FactorScore:
    factor_name: str         # "valuation", "technical", …
    score: int | None        # -100 to +100, or None on insufficient data
    verdict: str             # "bull" | "bear" | "neutral"
    explanation: str         # one-line human summary
    raw_data: dict           # the inputs used, for audit trail
    source: str              # "yfinance" | "reddit" | "manual"
```

**Rule 7.1.1** — Scorers are pure functions: `(ticker, fundamentals) -> FactorScore`.
No DB writes inside the scorer; persistence happens in the orchestrator.

**Rule 7.1.2** — Scoring thresholds are documented inline as a comment block at
the top of the scorer function — anyone should be able to read the rules without
running the code.

**Rule 7.1.3** — Score is clamped to `[-100, +100]`. Verdict thresholds:
`score < -30 → bear`, `score > +30 → bull`, else `neutral`.

**Rule 7.1.4** — `explanation` is a single sentence under 100 chars. It's what
shows up on the heatmap card.

### 7.2 Orchestration

`score_and_persist(ticker, factor_name)` is the one entry point:
1. Fetch fundamentals (cached)
2. Dispatch to the right scorer
3. Upsert a `FactorSnapshot` row keyed on `(ticker, factor_name, snapshot_date)`
4. Return the `FactorSnapshot`

**Rule 7.2.1** — Upsert, never insert-only. Re-running the scan for the same day
overwrites the previous snapshot.

**Rule 7.2.2** — `compute_alignment_score(ticker, snapshot_date)` reads all
`FactorSnapshot` rows for that day, computes the composite, upserts an
`AlignmentScore` row.

**Rule 7.2.3** — Composite formula and verdict logic live in ONE function
(`compute_composite`) — never duplicated.

### 7.3 Composite scoring (canonical)

```python
def compute_composite(factor_scores: dict[str, int],
                      weights: dict[str, float] | None = None) -> dict:
    if weights is None:
        weights = {f: 1/len(factor_scores) for f in factor_scores}
    composite = sum(s * weights[f] for f, s in factor_scores.items())
    composite = max(-100, min(100, composite))

    bullish = sum(1 for s in factor_scores.values() if s > 30)
    bearish = sum(1 for s in factor_scores.values() if s < -30)

    if composite > 50 and bullish >= 5:   verdict = "strong_long"
    elif composite > 20:                  verdict = "long_bias"
    elif composite < -50 and bearish >=5: verdict = "strong_short"
    elif composite < -20:                 verdict = "short_bias"
    else:                                 verdict = "no_trade"

    return {"composite_score": int(composite), "verdict": verdict, ...}
```

---

## 8. Trade discipline rules (built into the data model)

These are not just suggestions — they're enforced at the API layer.

**Rule 8.1** — Every `TradeCreate` requires a `thesis` (≥10 chars), profit target
OR profit target %, stop loss OR stop loss %, and emotional state.

**Rule 8.2** — 24-hour blackout: if the most recent closed trade was a loss
within 24h, `risk_alerts` includes "BLACKOUT". Frontend displays a danger banner;
the server still allows the trade (user override) but logs it.

**Rule 8.3** — Portfolio < €9000: warning, not blocker.

**Rule 8.4** — Cash < 20%: warning. Concentration > 30% in one position: warning.

**Rule 8.5** — Strategy rules are versioned. When `STRATEGY_RULES_V1` changes,
bump to V2 — never edit V1. Trades reference the version they were placed under.

---

## 9. Frontend conventions

**Rule 9.1** — TypeScript strict mode. No `any` unless wrapping a third-party lib
that genuinely has no types.

**Rule 9.2** — Types in `frontend/src/types/index.ts` mirror backend Pydantic
schemas exactly. When the backend changes, update types in the same PR.

**Rule 9.3** — One hook per resource (`useTrades`, `usePortfolio`, `useMarkets`).
Hooks own loading/error state, never component-local axios calls.

**Rule 9.4** — Pages route components live in `pages/`. Reusable components
organized by feature: `components/forms/`, `components/portfolio/`,
`components/markets/`.

**Rule 9.5** — Tailwind utility classes only. No inline styles, no CSS modules.
Custom utilities (`btn-primary`, `card`, `alert-danger`) defined once in
`index.css`.

**Rule 9.6** — Dark-mode first. Use `text-bright`, `text-muted`, `bg-card`
semantic tokens — not `text-white`, `bg-gray-900` literals.

**Rule 9.7** — Financial numbers are monospace (`font-mono`). Always show the
currency symbol. Use `toLocaleString` for thousand separators.

**Rule 9.8** — Profit colored `text-profit`, loss colored `text-loss`. Never
green/red literals.

---

## 10. Testing

**Rule 10.1** — pytest, FastAPI TestClient. SQLite in-memory with `StaticPool`
(see `tests/test_portfolio.py` fixture as canonical reference).

**Rule 10.2** — Every router has a test file. Every service has a test file.
Test names describe behavior, not implementation: `test_blackout_after_loss`,
not `test_check_risk_alerts_returns_blackout_when_recent_loss_exists`.

**Rule 10.3** — Mock external I/O. yfinance is mocked at `app.services.X.yf`.
Never make a real network call from a test.

**Rule 10.4** — Edge cases are first-class tests: zero trades, all wins, all
losses, NaN inputs, missing fields, divide-by-zero, empty DB.

**Rule 10.5** — All tests must pass before commit. CI is `pytest backend/tests/`.

---

## 11. Money & numbers

**Rule 11.1** — Currency is EUR by default (`portfolio_currency = "EUR"`).
Position currency is per-position; FX conversion happens at display time.

**Rule 11.2** — Prices stored as `Numeric(10, 4)` for instruments, `Numeric(10, 2)`
for portfolio totals. Quantities as `Integer`.

**Rule 11.3** — P&L computation is direction-aware: puts/turbo_short invert the
price delta. Always go through `compute_trade_pnl` — never reimplement.

**Rule 11.4** — Percentages stored as decimals (0.05 = 5%) at the DB layer,
displayed as % at the UI layer. Keep the boundary clean.

---

## 12. Security & secrets

**Rule 12.1** — Single-user system. No auth in v1 — assume the FastAPI server is
on localhost or behind a reverse proxy with auth.

**Rule 12.2** — API keys (Anthropic, news, Reddit) live only in `.env`. Never
in source, never in logs, never in error responses.

**Rule 12.3** — No SQL string concatenation, ever. SQLAlchemy ORM or parameterized
queries only.

**Rule 12.4** — User-supplied free-text fields (notes, thesis, lessons_learned)
are stored as-is and rendered with React's default escaping. Never `dangerouslySetInnerHTML`.

---

## 13. Performance budgets

**Rule 13.1** — Heatmap endpoint must return in < 500ms with 30 watchlist
tickers. Achieved by reading pre-computed `AlignmentScore` rows, not
recomputing on request.

**Rule 13.2** — Scan-all (POST /markets/scan-all) is async-friendly: must
complete < 60s for 30 tickers. Network-bound; rely on yfinance caching.

**Rule 13.3** — Frontend bundle target: < 500KB gzipped. Recharts is the only
heavy dep allowed.

**Rule 13.4** — DB queries in routers must be O(1) per resource or O(N)
where N is the page size. No N+1 queries; use eager loading via `joinedload`
when relationships are accessed.

---

## 14. Naming conventions

**Rule 14.1** — Python: `snake_case` for functions/vars, `PascalCase` for classes,
`UPPER_SNAKE` for constants/module-level dicts.

**Rule 14.2** — TypeScript: `camelCase` for vars/functions, `PascalCase` for
types/components, `UPPER_SNAKE` for constants.

**Rule 14.3** — Database: `snake_case` for tables and columns. Plural table
names (`trades`, `positions`, `factor_snapshots`). Singular model class names
(`Trade`, `Position`, `FactorSnapshot`).

**Rule 14.4** — REST endpoints: plural resource names, kebab-case for
multi-word (`/api/v1/factor-snapshots`). Verbs only for non-CRUD actions
(`/markets/scan-all`, `/markets/{ticker}/refresh`).

---

## 15. Phases & status

| Phase | Module | Status |
|---|---|---|
| 1 | Trade Journal | ✅ Shipped |
| 2 | Portfolio (IB integration) | ✅ Shipped |
| 3 | Planet Alignment | 🚧 Days 1-2 done, Day 3 in progress |
| 4 | Social Signals (full Alpha Score) | ⏭ Backlog |
| 5 | Greeks & options analytics | ⏭ Backlog |
| 6 | Pattern Research / Backtester | ⏭ Backlog |
| 7 | AI Analysis hub | ⏭ Backlog |

---

## 16. Operational rules for humans (and Claude)

**Rule 16.1** — Every commit message starts with the phase + day:
`Phase 3 Day 3: Valuation scorer + score_and_persist orchestrator`.

**Rule 16.2** — Don't add features outside the current day's scope. If you find
something broken or missing, file it in the master plan as a new item rather
than fixing it inline.

**Rule 16.3** — When in doubt, prefer the simpler choice. This is a personal
trading tool, not a SaaS product. No multi-tenancy, no microservices, no event
buses.

**Rule 16.4** — Every change ships green: all tests pass before commit. No
"will fix in next commit."

**Rule 16.5** — When patterns conflict between this doc and a working file,
the working file wins (it's been validated). Update this doc to match reality.

---

*Last updated: Phase 3 Day 3 — May 6, 2026*
