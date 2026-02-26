import { useState } from "react";
import { useTrades, useDashboard } from "../hooks/useTrades";
import TradeEntryForm from "../components/forms/TradeEntryForm";
import TradeCloseForm from "../components/forms/TradeCloseForm";
import TradeHistoryTable from "../components/forms/TradeHistoryTable";
import type { Trade } from "../types";

export default function TradeLog() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [tickerFilter, setTickerFilter] = useState("");
  const { trades, loading, error, refetch, createTrade, closeTrade, deleteTrade } =
    useTrades({
      status: statusFilter || undefined,
      ticker: tickerFilter || undefined,
      limit: 200,
    });
  const { data: dashData } = useDashboard();

  const [showForm, setShowForm] = useState(false);
  const [closingTrade, setClosingTrade] = useState<Trade | null>(null);

  // Risk alerts for the form
  const riskAlerts = dashData?.risk_alerts ?? [];
  const hasBlackout = riskAlerts.some((a) => a.includes("BLACKOUT"));

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {/* Risk alerts banner */}
      {riskAlerts.length > 0 && (
        <div className="space-y-2">
          {riskAlerts.map((alert, i) => (
            <div
              key={i}
              className={alert.includes("BLACKOUT") ? "alert-danger" : "alert-warning"}
            >
              {alert}
            </div>
          ))}
        </div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-bright">Trade Journal</h1>
        <button
          className="btn-primary"
          onClick={() => {
            setShowForm(!showForm);
            setClosingTrade(null);
          }}
        >
          {showForm ? "Cancel" : "+ Log Trade"}
        </button>
      </div>

      {/* Trade entry form */}
      {showForm && (
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-4">New Trade Entry</h2>
          {hasBlackout && (
            <div className="alert-danger mb-4 font-semibold">
              24-HOUR BLACKOUT ACTIVE — A loss was realized recently. Proceed with extreme caution.
            </div>
          )}
          <TradeEntryForm
            onSubmit={async (payload) => {
              await createTrade(payload);
              setShowForm(false);
            }}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {/* Close trade form */}
      {closingTrade && (
        <div className="card">
          <h2 className="text-sm text-muted uppercase tracking-wider mb-4">
            Close Trade: {closingTrade.ticker} ({closingTrade.instrument_type})
          </h2>
          <TradeCloseForm
            trade={closingTrade}
            onSubmit={async (payload) => {
              await closeTrade(closingTrade.id, payload);
              setClosingTrade(null);
            }}
            onCancel={() => setClosingTrade(null)}
          />
        </div>
      )}

      {/* Filters row */}
      <div className="flex gap-3 items-center flex-wrap">
        <select
          className="input w-auto"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
          <option value="expired">Expired</option>
        </select>
        <input
          type="text"
          className="input w-32"
          placeholder="Ticker"
          value={tickerFilter}
          onChange={(e) => setTickerFilter(e.target.value.toUpperCase())}
        />
        <button className="btn-ghost text-xs" onClick={() => refetch()}>
          Refresh
        </button>
      </div>

      {/* Trade history table */}
      {loading ? (
        <div className="text-muted text-sm py-8 text-center">Loading trades...</div>
      ) : error ? (
        <div className="alert-danger">{error}</div>
      ) : (
        <TradeHistoryTable
          trades={trades}
          onClose={(trade) => {
            setClosingTrade(trade);
            setShowForm(false);
          }}
          onDelete={async (id) => {
            if (confirm("Delete this trade? This cannot be undone.")) {
              await deleteTrade(id);
            }
          }}
        />
      )}
    </div>
  );
}
