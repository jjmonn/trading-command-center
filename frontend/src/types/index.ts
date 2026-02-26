// ─── Trade types ──────────────────────────────────────────────────────────────

export type TradeStatus = "open" | "closed" | "expired";

export type InstrumentType =
  | "stock"
  | "call_option"
  | "put_option"
  | "call_warrant"
  | "put_warrant"
  | "turbo_long"
  | "turbo_short";

export type NewsType =
  | "earnings"
  | "buyback"
  | "analyst_upgrade"
  | "analyst_downgrade"
  | "geopolitical"
  | "sector_news"
  | "guidance"
  | "product_launch"
  | "regulatory"
  | "technical_setup"
  | "flow_signal";

export type MarketTrend = "bullish" | "bearish" | "neutral" | "choppy";

export type EmotionalState =
  | "calm"
  | "anxious"
  | "excited"
  | "revenge"
  | "fomo"
  | "confident";

export type StrategyCategory =
  | "momentum_news"
  | "earnings_event"
  | "trend_swing"
  | "core_holding"
  | "flow_follow"
  | "thematic";

export type ExitReason =
  | "profit_target"
  | "stop_loss"
  | "time_stop"
  | "thesis_invalidated"
  | "trailing_stop"
  | "manual"
  | "expiry";

export interface Trade {
  id: number;
  status: TradeStatus;
  entry_datetime: string;
  exit_datetime?: string;

  ticker: string;
  instrument_type: InstrumentType;
  sector?: string;
  underlying_price_entry?: number;
  underlying_price_exit?: number;
  strike?: number;
  expiry_date?: string;
  dte_at_entry?: number;

  entry_price: number;
  exit_price?: number;
  quantity: number;
  fees_entry?: number;
  fees_exit?: number;
  currency?: string;

  news_type?: NewsType;
  news_headline?: string;
  market_trend?: MarketTrend;
  sector_trend?: string;
  vix_at_entry?: number;
  iv_percentile?: number;

  thesis: string;
  strategy_category?: StrategyCategory;
  profit_target_price?: number;
  profit_target_pct?: number;
  stop_loss_price?: number;
  stop_loss_pct?: number;
  time_stop_date?: string;

  exit_reason?: ExitReason;

  rules_followed?: string[];
  rules_violated?: string[];
  rule_compliance_score?: number;

  notes_what_worked?: string;
  notes_what_didnt?: string;
  lessons_learned?: string;
  emotional_state_entry?: EmotionalState;
  emotional_state_exit?: EmotionalState;
  would_take_again?: boolean;

  gross_pnl?: number;
  net_pnl?: number;
  gross_pnl_pct?: number;
  net_pnl_pct?: number;
  duration_hours?: number;

  created_at: string;
  updated_at?: string;
}

export interface TradeCreate {
  entry_datetime?: string;
  ticker: string;
  instrument_type: InstrumentType;
  sector?: string;
  underlying_price_entry?: number;
  strike?: number;
  expiry_date?: string;
  dte_at_entry?: number;
  entry_price: number;
  quantity: number;
  fees_entry?: number;
  currency?: string;
  news_type?: NewsType;
  news_headline?: string;
  news_url?: string;
  market_trend?: MarketTrend;
  sector_trend?: string;
  vix_at_entry?: number;
  iv_percentile?: number;
  iv_at_entry?: number;
  thesis: string;
  strategy_category?: StrategyCategory;
  profit_target_price?: number;
  profit_target_pct?: number;
  stop_loss_price?: number;
  stop_loss_pct?: number;
  time_stop_date?: string;
  emotional_state_entry: EmotionalState;
  rules_followed?: string[];
  rules_violated?: string[];
  rule_compliance_score?: number;
}

export interface TradeClose {
  exit_price: number;
  exit_datetime?: string;
  fees_exit?: number;
  exit_reason: ExitReason;
  emotional_state_exit?: EmotionalState;
  notes_what_worked?: string;
  notes_what_didnt?: string;
  lessons_learned?: string;
  would_take_again?: boolean;
  max_favorable_excursion?: number;
  max_adverse_excursion?: number;
}

// ─── Analytics types ──────────────────────────────────────────────────────────

export interface AnalyticsSummary {
  total_closed_trades: number;
  open_trades: number;
  win_rate: number | null;
  expectancy: number | null;
  profit_factor: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  avg_duration_hours: number | null;
  total_net_pnl: number;
  total_gross_pnl: number;
  rule_compliance_avg: number | null;
  recent_streak: number;
}

export interface EquityCurvePoint {
  date: string;
  cumulative_pnl: number;
  drawdown_pct: number;
}

export interface MonthlyPnLPoint {
  year: number;
  month: number;
  net_pnl: number;
  trade_count: number;
}

export interface BreakdownItem {
  label: string;
  count: number;
  win_rate: number | null;
  expectancy: number | null;
  total_pnl: number;
}

export interface DashboardData {
  summary: AnalyticsSummary;
  equity_curve: EquityCurvePoint[];
  monthly_pnl: MonthlyPnLPoint[];
  by_news_type: BreakdownItem[];
  by_sector: BreakdownItem[];
  by_strategy: BreakdownItem[];
  by_emotional_state: BreakdownItem[];
  risk_alerts: string[];
}

// ─── Rule checklist ────────────────────────────────────────────────────────────

export interface RuleChecklistItem {
  id: string;
  category: "entry" | "position" | "risk" | "psychological";
  text: string;
}

// ─── Portfolio types ──────────────────────────────────────────────────────────

export interface Position {
  id: number;
  ib_con_id?: number;
  ticker: string;
  instrument_type: string;
  quantity: number;
  avg_cost?: number;
  market_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  realized_pnl?: number;
  currency?: string;
  strike?: number;
  expiry?: string;
  option_type?: string;
  sector?: string;
  source?: string;
  is_active?: boolean;
  notes?: string;
  last_updated?: string;
  // Computed
  pnl_pct?: number;
  dte?: number;
  weight_pct?: number;
}

export interface PositionCreate {
  ticker: string;
  instrument_type: string;
  quantity: number;
  avg_cost?: number;
  market_price?: number;
  currency?: string;
  strike?: number;
  expiry?: string;
  option_type?: string;
  sector?: string;
  notes?: string;
}

export interface PositionUpdate {
  quantity?: number;
  avg_cost?: number;
  market_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  sector?: string;
  notes?: string;
  is_active?: boolean;
}

export interface PortfolioSummary {
  total_nav: number;
  cash_balance: number;
  invested_value: number;
  unrealized_pnl: number;
  total_long_exposure: number;
  total_short_exposure: number;
  net_exposure: number;
  cash_pct: number;
  leverage_ratio: number;
  num_positions: number;
  risk_alerts: string[];
}

export interface ExposureBreakdown {
  label: string;
  value: number;
  pct: number;
}

export interface PortfolioHistoryPoint {
  id: number;
  timestamp: string;
  total_nav?: number;
  cash_balance?: number;
  invested_value?: number;
  unrealized_pnl?: number;
}

export interface PortfolioDashboard {
  summary: PortfolioSummary;
  positions: Position[];
  by_sector: ExposureBreakdown[];
  by_instrument: ExposureBreakdown[];
  by_currency: ExposureBreakdown[];
  history: PortfolioHistoryPoint[];
}

export interface IBStatus {
  connected: boolean;
  host: string;
  port: number;
  message: string;
}
