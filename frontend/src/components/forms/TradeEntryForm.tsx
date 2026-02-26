import { useState } from "react";
import { useRuleChecklist } from "../../hooks/useTrades";
import type { TradeCreate, InstrumentType, EmotionalState, StrategyCategory, NewsType, MarketTrend } from "../../types";

const INSTRUMENT_TYPES: InstrumentType[] = [
  "stock", "call_option", "put_option", "call_warrant", "put_warrant", "turbo_long", "turbo_short",
];
const EMOTIONAL_STATES: EmotionalState[] = ["calm", "anxious", "excited", "revenge", "fomo", "confident"];
const STRATEGY_CATEGORIES: StrategyCategory[] = [
  "momentum_news", "earnings_event", "trend_swing", "core_holding", "flow_follow", "thematic",
];
const NEWS_TYPES: NewsType[] = [
  "earnings", "buyback", "analyst_upgrade", "analyst_downgrade", "geopolitical",
  "sector_news", "guidance", "product_launch", "regulatory", "technical_setup", "flow_signal",
];
const MARKET_TRENDS: MarketTrend[] = ["bullish", "bearish", "neutral", "choppy"];

interface Props {
  onSubmit: (payload: TradeCreate) => Promise<void>;
  onCancel: () => void;
}

export default function TradeEntryForm({ onSubmit, onCancel }: Props) {
  const checklist = useRuleChecklist();
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form state
  const [ticker, setTicker] = useState("");
  const [instrumentType, setInstrumentType] = useState<InstrumentType>("call_option");
  const [sector, setSector] = useState("");
  const [entryPrice, setEntryPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [feesEntry, setFeesEntry] = useState("0");
  const [currency, setCurrency] = useState("EUR");
  const [underlyingPriceEntry, setUnderlyingPriceEntry] = useState("");
  const [strike, setStrike] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [dteAtEntry, setDteAtEntry] = useState("");
  const [barrierLevel, setBarrierLevel] = useState("");

  // Context
  const [newsType, setNewsType] = useState<NewsType | "">("");
  const [newsHeadline, setNewsHeadline] = useState("");
  const [newsUrl, setNewsUrl] = useState("");
  const [marketTrend, setMarketTrend] = useState<MarketTrend | "">("");
  const [sectorTrend, setSectorTrend] = useState("");
  const [vixAtEntry, setVixAtEntry] = useState("");
  const [ivPercentile, setIvPercentile] = useState("");
  const [ivAtEntry, setIvAtEntry] = useState("");

  // Pre-trade planning
  const [thesis, setThesis] = useState("");
  const [strategyCategory, setStrategyCategory] = useState<StrategyCategory | "">("");
  const [profitTargetPct, setProfitTargetPct] = useState("25");
  const [stopLossPct, setStopLossPct] = useState("15");
  const [profitTargetPrice, setProfitTargetPrice] = useState("");
  const [stopLossPrice, setStopLossPrice] = useState("");
  const [timeStopDate, setTimeStopDate] = useState("");

  // Psychology
  const [emotionalState, setEmotionalState] = useState<EmotionalState>("calm");

  // Rule compliance
  const [checkedRules, setCheckedRules] = useState<Set<string>>(new Set());

  function toggleRule(ruleId: string) {
    setCheckedRules((prev) => {
      const next = new Set(prev);
      if (next.has(ruleId)) next.delete(ruleId);
      else next.add(ruleId);
      return next;
    });
  }

  const violatedRules = checklist.filter((r) => !checkedRules.has(r.id)).map((r) => r.id);
  const complianceScore = checklist.length > 0
    ? checkedRules.size / checklist.length
    : 1;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!ticker.trim()) { setFormError("Ticker is required"); return; }
    if (!entryPrice || Number(entryPrice) <= 0) { setFormError("Entry price must be positive"); return; }
    if (!quantity || Number(quantity) <= 0) { setFormError("Quantity must be positive"); return; }
    if (thesis.trim().length < 10) { setFormError("Thesis must be at least 10 characters"); return; }
    if (!profitTargetPct && !profitTargetPrice) { setFormError("Profit target is required"); return; }
    if (!stopLossPct && !stopLossPrice) { setFormError("Stop loss is required"); return; }

    const payload: TradeCreate = {
      ticker: ticker.toUpperCase().trim(),
      instrument_type: instrumentType,
      entry_price: Number(entryPrice),
      quantity: Number(quantity),
      fees_entry: Number(feesEntry) || 0,
      currency,
      thesis: thesis.trim(),
      emotional_state_entry: emotionalState,
      rules_followed: [...checkedRules],
      rules_violated: violatedRules,
      rule_compliance_score: Number(complianceScore.toFixed(2)),
    };

    if (sector) payload.sector = sector;
    if (underlyingPriceEntry) payload.underlying_price_entry = Number(underlyingPriceEntry);
    if (strike) payload.strike = Number(strike);
    if (expiryDate) payload.expiry_date = expiryDate;
    if (dteAtEntry) payload.dte_at_entry = Number(dteAtEntry);
    if (newsType) payload.news_type = newsType;
    if (newsHeadline) payload.news_headline = newsHeadline;
    if (newsUrl) payload.news_url = newsUrl;
    if (marketTrend) payload.market_trend = marketTrend;
    if (sectorTrend) payload.sector_trend = sectorTrend;
    if (vixAtEntry) payload.vix_at_entry = Number(vixAtEntry);
    if (ivPercentile) payload.iv_percentile = Number(ivPercentile);
    if (ivAtEntry) payload.iv_at_entry = Number(ivAtEntry);
    if (strategyCategory) payload.strategy_category = strategyCategory;
    if (profitTargetPct) payload.profit_target_pct = Number(profitTargetPct);
    if (stopLossPct) payload.stop_loss_pct = Number(stopLossPct);
    if (profitTargetPrice) payload.profit_target_price = Number(profitTargetPrice);
    if (stopLossPrice) payload.stop_loss_price = Number(stopLossPrice);
    if (timeStopDate) payload.time_stop_date = timeStopDate;
    if (barrierLevel) (payload as Record<string, unknown>).barrier_level = Number(barrierLevel);

    setSubmitting(true);
    try {
      await onSubmit(payload);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create trade";
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  const isDerivative = instrumentType !== "stock";

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {formError && <div className="alert-danger">{formError}</div>}

      {/* Emotional state warning */}
      {(emotionalState === "revenge" || emotionalState === "fomo") && (
        <div className="alert-danger font-semibold">
          You selected "{emotionalState}" — consider NOT placing this trade. Review your rules.
        </div>
      )}

      {/* Section 1: Instrument */}
      <fieldset className="space-y-3">
        <legend className="text-xs text-muted uppercase tracking-wider font-semibold mb-2">Instrument</legend>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="label">Ticker *</label>
            <input className="input" value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="NVDA" required />
          </div>
          <div>
            <label className="label">Type *</label>
            <select className="input" value={instrumentType} onChange={(e) => setInstrumentType(e.target.value as InstrumentType)}>
              {INSTRUMENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Entry Price *</label>
            <input className="input" type="number" step="0.0001" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} required />
          </div>
          <div>
            <label className="label">Quantity *</label>
            <input className="input" type="number" step="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="label">Sector</label>
            <input className="input" value={sector} onChange={(e) => setSector(e.target.value)} placeholder="Technology" />
          </div>
          <div>
            <label className="label">Fees</label>
            <input className="input" type="number" step="0.01" value={feesEntry} onChange={(e) => setFeesEntry(e.target.value)} />
          </div>
          <div>
            <label className="label">Currency</label>
            <select className="input" value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="EUR">EUR</option>
              <option value="USD">USD</option>
            </select>
          </div>
          <div>
            <label className="label">Underlying Price</label>
            <input className="input" type="number" step="0.01" value={underlyingPriceEntry} onChange={(e) => setUnderlyingPriceEntry(e.target.value)} />
          </div>
        </div>
        {isDerivative && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="label">Strike</label>
              <input className="input" type="number" step="0.01" value={strike} onChange={(e) => setStrike(e.target.value)} />
            </div>
            <div>
              <label className="label">Expiry Date</label>
              <input className="input" type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
            </div>
            <div>
              <label className="label">DTE at Entry</label>
              <input className="input" type="number" value={dteAtEntry} onChange={(e) => setDteAtEntry(e.target.value)} />
            </div>
            {(instrumentType === "turbo_long" || instrumentType === "turbo_short") && (
              <div>
                <label className="label">Barrier Level</label>
                <input className="input" type="number" step="0.01" value={barrierLevel} onChange={(e) => setBarrierLevel(e.target.value)} />
              </div>
            )}
          </div>
        )}
      </fieldset>

      {/* Section 2: Market context */}
      <fieldset className="space-y-3">
        <legend className="text-xs text-muted uppercase tracking-wider font-semibold mb-2">Market Context</legend>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="label">News Type</label>
            <select className="input" value={newsType} onChange={(e) => setNewsType(e.target.value as NewsType)}>
              <option value="">—</option>
              {NEWS_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Market Trend</label>
            <select className="input" value={marketTrend} onChange={(e) => setMarketTrend(e.target.value as MarketTrend)}>
              <option value="">—</option>
              {MARKET_TRENDS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Sector Trend</label>
            <input className="input" value={sectorTrend} onChange={(e) => setSectorTrend(e.target.value)} placeholder="bullish" />
          </div>
          <div>
            <label className="label">VIX at Entry</label>
            <input className="input" type="number" step="0.01" value={vixAtEntry} onChange={(e) => setVixAtEntry(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="label">IV Percentile</label>
            <input className="input" type="number" step="0.01" value={ivPercentile} onChange={(e) => setIvPercentile(e.target.value)} />
          </div>
          <div>
            <label className="label">IV at Entry</label>
            <input className="input" type="number" step="0.01" value={ivAtEntry} onChange={(e) => setIvAtEntry(e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="label">News Headline</label>
            <input className="input" value={newsHeadline} onChange={(e) => setNewsHeadline(e.target.value)} placeholder="e.g. NVDA beats Q4 earnings..." />
          </div>
        </div>
        <div>
          <label className="label">News URL</label>
          <input className="input" type="url" value={newsUrl} onChange={(e) => setNewsUrl(e.target.value)} placeholder="https://..." />
        </div>
      </fieldset>

      {/* Section 3: Pre-trade planning (REQUIRED) */}
      <fieldset className="space-y-3">
        <legend className="text-xs text-muted uppercase tracking-wider font-semibold mb-2">
          Pre-Trade Planning <span className="text-loss">*</span>
        </legend>
        <div>
          <label className="label">Thesis * (why this trade, max 2 sentences)</label>
          <textarea
            className="input"
            rows={2}
            value={thesis}
            onChange={(e) => setThesis(e.target.value)}
            placeholder="NVDA set to benefit from AI capex cycle. Earnings beat confirms thesis, IV crush is manageable at this DTE."
            required
          />
          {thesis.length > 0 && thesis.length < 10 && (
            <span className="text-loss text-xs mt-1">Minimum 10 characters</span>
          )}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="label">Strategy Category</label>
            <select className="input" value={strategyCategory} onChange={(e) => setStrategyCategory(e.target.value as StrategyCategory)}>
              <option value="">—</option>
              {STRATEGY_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Profit Target % *</label>
            <input className="input" type="number" step="0.01" value={profitTargetPct} onChange={(e) => setProfitTargetPct(e.target.value)} />
          </div>
          <div>
            <label className="label">Stop Loss % *</label>
            <input className="input" type="number" step="0.01" value={stopLossPct} onChange={(e) => setStopLossPct(e.target.value)} />
          </div>
          <div>
            <label className="label">Time Stop Date</label>
            <input className="input" type="date" value={timeStopDate} onChange={(e) => setTimeStopDate(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Profit Target Price</label>
            <input className="input" type="number" step="0.0001" value={profitTargetPrice} onChange={(e) => setProfitTargetPrice(e.target.value)} />
          </div>
          <div>
            <label className="label">Stop Loss Price</label>
            <input className="input" type="number" step="0.0001" value={stopLossPrice} onChange={(e) => setStopLossPrice(e.target.value)} />
          </div>
        </div>
      </fieldset>

      {/* Section 4: Emotional state */}
      <fieldset className="space-y-3">
        <legend className="text-xs text-muted uppercase tracking-wider font-semibold mb-2">
          Emotional State <span className="text-loss">*</span>
        </legend>
        <div className="flex gap-2 flex-wrap">
          {EMOTIONAL_STATES.map((state) => (
            <button
              key={state}
              type="button"
              className={`badge cursor-pointer transition-colors ${
                emotionalState === state
                  ? state === "revenge" || state === "fomo"
                    ? "bg-loss/30 text-loss ring-1 ring-loss"
                    : state === "calm" || state === "confident"
                    ? "bg-profit/30 text-profit ring-1 ring-profit"
                    : "bg-warn/30 text-warn ring-1 ring-warn"
                  : "bg-surface-2 text-muted hover:text-bright"
              }`}
              onClick={() => setEmotionalState(state)}
            >
              {state}
            </button>
          ))}
        </div>
      </fieldset>

      {/* Section 5: Rule compliance checklist */}
      {checklist.length > 0 && (
        <fieldset className="space-y-3">
          <legend className="text-xs text-muted uppercase tracking-wider font-semibold mb-2">
            Rule Compliance Checklist
            <span className={`ml-2 ${complianceScore >= 0.8 ? "text-profit" : complianceScore >= 0.5 ? "text-warn" : "text-loss"}`}>
              ({(complianceScore * 100).toFixed(0)}%)
            </span>
          </legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
            {checklist.map((rule) => (
              <label
                key={rule.id}
                className="flex items-start gap-2 p-2 rounded hover:bg-surface-2 cursor-pointer text-sm"
              >
                <input
                  type="checkbox"
                  className="mt-0.5 accent-profit"
                  checked={checkedRules.has(rule.id)}
                  onChange={() => toggleRule(rule.id)}
                />
                <span className={checkedRules.has(rule.id) ? "text-bright" : "text-muted"}>
                  <span className="text-xs text-muted uppercase">[{rule.category}]</span>{" "}
                  {rule.text}
                </span>
              </label>
            ))}
          </div>
          {violatedRules.length > 0 && (
            <div className="alert-warning text-xs">
              {violatedRules.length} rule(s) not confirmed. Proceed only if you have a valid reason.
            </div>
          )}
        </fieldset>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Saving..." : "Log Trade"}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
