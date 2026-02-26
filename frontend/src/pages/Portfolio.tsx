import { useState } from "react";
import { usePortfolioDashboard, useIBConnection } from "../hooks/usePortfolio";
import MetricCard from "../components/cards/MetricCard";
import PositionTable from "../components/portfolio/PositionTable";
import AllocationChart from "../components/portfolio/AllocationChart";
import PositionForm from "../components/portfolio/PositionForm";
import NAVChart from "../components/portfolio/NAVChart";
import type { Position } from "../types";

export default function Portfolio() {
  const { data, loading, error, refetch } = usePortfolioDashboard();
  const ib = useIBConnection();

  const [showForm, setShowForm] = useState(false);
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-muted">Loading portfolio...</div>;
  }
  if (error) {
    return <div className="flex-1 p-6"><div className="alert-danger">{error}</div></div>;
  }
  if (!data) return null;

  const { summary: s, positions, by_sector, by_instrument, by_currency, history } = data;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Risk alerts */}
      {s.risk_alerts.length > 0 && (
        <div className="space-y-2">
          {s.risk_alerts.map((alert, i) => (
            <div key={i} className="alert-warning">{alert}</div>
          ))}
        </div>
      )}

      {/* IB connection bar */}
      <div className="card flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${ib.status?.connected ? "bg-profit" : "bg-loss"}`} />
          <span className="text-sm text-muted">
            IB: {ib.status?.message || "Unknown"}
          </span>
        </div>
        <div className="flex gap-2">
          {!ib.status?.connected ? (
            <button
              className="btn-ghost text-xs"
              onClick={async () => { await ib.connect(); refetch(); }}
            >
              Connect IB
            </button>
          ) : (
            <>
              <button
                className="btn-primary text-xs"
                onClick={async () => { await ib.sync(); refetch(); }}
              >
                Sync Positions
              </button>
              <button
                className="btn-ghost text-xs"
                onClick={async () => { await ib.disconnect(); }}
              >
                Disconnect
              </button>
            </>
          )}
          <button
            className="btn-ghost text-xs"
            onClick={async () => { await ib.refreshPrices(); refetch(); }}
          >
            Refresh Prices
          </button>
        </div>
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard
          label="Total NAV"
          value={`€${s.total_nav.toLocaleString("en", { minimumFractionDigits: 0 })}`}
        />
        <MetricCard
          label="Cash"
          value={`€${s.cash_balance.toLocaleString("en", { minimumFractionDigits: 0 })}`}
        />
        <MetricCard
          label="Invested"
          value={`€${s.invested_value.toLocaleString("en", { minimumFractionDigits: 0 })}`}
        />
        <MetricCard
          label="Unrealized P&L"
          value={`€${s.unrealized_pnl.toLocaleString("en", { minimumFractionDigits: 0 })}`}
          color={s.unrealized_pnl >= 0 ? "profit" : "loss"}
        />
        <MetricCard
          label="Cash %"
          value={`${s.cash_pct.toFixed(1)}%`}
          color={s.cash_pct < 20 ? "loss" : undefined}
        />
        <MetricCard
          label="Positions"
          value={String(s.num_positions)}
        />
      </div>

      {/* Exposure bar */}
      <div className="card">
        <div className="flex items-center gap-6 text-sm font-mono">
          <span className="text-muted">Long:</span>
          <span className="text-profit">€{s.total_long_exposure.toLocaleString()}</span>
          <span className="text-muted">Short:</span>
          <span className="text-loss">€{s.total_short_exposure.toLocaleString()}</span>
          <span className="text-muted">Net:</span>
          <span className="text-bright">€{s.net_exposure.toLocaleString()}</span>
          <span className="text-muted">Leverage:</span>
          <span className={s.leverage_ratio > 1 ? "text-warn" : "text-bright"}>
            {s.leverage_ratio.toFixed(2)}x
          </span>
        </div>
      </div>

      {/* Positions table + add button */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm text-muted uppercase tracking-wider">Positions</h2>
        <button
          className="btn-ghost text-xs"
          onClick={() => { setShowForm(!showForm); setEditingPosition(null); }}
        >
          {showForm ? "Cancel" : "+ Add Manual Position"}
        </button>
      </div>

      {showForm && (
        <div className="card">
          <PositionForm
            position={editingPosition}
            onSubmit={async () => { setShowForm(false); setEditingPosition(null); refetch(); }}
            onCancel={() => { setShowForm(false); setEditingPosition(null); }}
          />
        </div>
      )}

      <PositionTable
        positions={positions}
        onEdit={(p) => { setEditingPosition(p); setShowForm(true); }}
        onDelete={async (id) => {
          if (confirm("Delete this position?")) {
            const { default: axios } = await import("axios");
            await axios.delete(`/api/v1/portfolio/positions/${id}`);
            refetch();
          }
        }}
      />

      {/* Allocation charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">By Sector</h2>
          <AllocationChart data={by_sector} />
        </div>
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">By Instrument</h2>
          <AllocationChart data={by_instrument} />
        </div>
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">By Currency</h2>
          <AllocationChart data={by_currency} />
        </div>
      </div>

      {/* NAV history chart */}
      {history.length > 0 && (
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-3">Portfolio NAV History</h2>
          <NAVChart data={history} />
        </div>
      )}
    </div>
  );
}
