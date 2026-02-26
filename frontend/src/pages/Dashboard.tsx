import { useDashboard } from "../hooks/useTrades";
import EquityChart from "../components/charts/EquityChart";
import MonthlyHeatmap from "../components/charts/MonthlyHeatmap";
import BreakdownChart from "../components/charts/BreakdownChart";
import MetricCard from "../components/cards/MetricCard";

export default function Dashboard() {
  const { data, loading, error, refetch } = useDashboard();

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted">
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-6">
        <div className="alert-danger">Failed to load dashboard: {error}</div>
      </div>
    );
  }

  if (!data) return null;

  const { summary: s, equity_curve, monthly_pnl, by_news_type, by_sector, by_strategy, by_emotional_state, risk_alerts } = data;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Risk alerts */}
      {risk_alerts.length > 0 && (
        <div className="space-y-2">
          {risk_alerts.map((alert, i) => (
            <div
              key={i}
              className={alert.includes("BLACKOUT") ? "alert-danger" : "alert-warning"}
            >
              {alert}
            </div>
          ))}
        </div>
      )}

      {/* Metric cards row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <MetricCard
          label="Total P&L"
          value={`€${s.total_net_pnl.toLocaleString("en", { minimumFractionDigits: 0 })}`}
          color={s.total_net_pnl >= 0 ? "profit" : "loss"}
        />
        <MetricCard
          label="Win Rate"
          value={s.win_rate !== null ? `${(s.win_rate * 100).toFixed(1)}%` : "—"}
        />
        <MetricCard
          label="Expectancy"
          value={s.expectancy !== null ? `€${s.expectancy.toFixed(0)}` : "—"}
          color={s.expectancy !== null ? (s.expectancy >= 0 ? "profit" : "loss") : undefined}
        />
        <MetricCard
          label="Profit Factor"
          value={s.profit_factor !== null ? s.profit_factor.toFixed(2) : "—"}
        />
        <MetricCard
          label="Sharpe"
          value={s.sharpe_ratio !== null ? s.sharpe_ratio.toFixed(2) : "—"}
        />
        <MetricCard
          label="Max DD"
          value={s.max_drawdown !== null ? `${(s.max_drawdown * 100).toFixed(1)}%` : "—"}
          color={s.max_drawdown !== null && s.max_drawdown > 0.15 ? "loss" : undefined}
        />
        <MetricCard
          label="Streak"
          value={s.recent_streak > 0 ? `+${s.recent_streak}` : String(s.recent_streak)}
          color={s.recent_streak >= 0 ? "profit" : "loss"}
        />
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Closed Trades" value={String(s.total_closed_trades)} />
        <MetricCard label="Open Trades" value={String(s.open_trades)} />
        <MetricCard
          label="Avg Duration"
          value={s.avg_duration_hours !== null ? `${s.avg_duration_hours.toFixed(0)}h` : "—"}
        />
        <MetricCard
          label="Rule Compliance"
          value={s.rule_compliance_avg !== null ? `${(s.rule_compliance_avg * 100).toFixed(0)}%` : "—"}
        />
      </div>

      {/* Equity curve */}
      <div className="card">
        <h2 className="text-sm text-muted uppercase tracking-wider mb-3">Equity Curve</h2>
        {equity_curve.length > 0 ? (
          <EquityChart data={equity_curve} />
        ) : (
          <p className="text-muted text-sm py-8 text-center">
            No closed trades yet. Log and close trades to see the equity curve.
          </p>
        )}
      </div>

      {/* Monthly P&L heatmap */}
      <div className="card">
        <h2 className="text-sm text-muted uppercase tracking-wider mb-3">Monthly P&L</h2>
        {monthly_pnl.length > 0 ? (
          <MonthlyHeatmap data={monthly_pnl} />
        ) : (
          <p className="text-muted text-sm py-4 text-center">No monthly data yet.</p>
        )}
      </div>

      {/* Breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">By News Type</h2>
          <BreakdownChart data={by_news_type} />
        </div>
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">By Sector</h2>
          <BreakdownChart data={by_sector} />
        </div>
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">By Strategy</h2>
          <BreakdownChart data={by_strategy} />
        </div>
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">By Emotional State</h2>
          <BreakdownChart data={by_emotional_state} />
        </div>
      </div>

      {/* Refresh */}
      <div className="text-center pb-4">
        <button className="btn-ghost text-xs" onClick={() => refetch()}>
          Refresh Dashboard
        </button>
      </div>
    </div>
  );
}
