import clsx from "clsx";
import type { Trade } from "../../types";

interface Props {
  trades: Trade[];
  onClose: (trade: Trade) => void;
  onDelete: (id: number) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" });
}

function pnlClass(pnl: number | null | undefined): string {
  if (pnl === null || pnl === undefined) return "text-muted";
  return pnl >= 0 ? "pnl-pos" : "pnl-neg";
}

export default function TradeHistoryTable({ trades, onClose, onDelete }: Props) {
  if (trades.length === 0) {
    return (
      <div className="text-muted text-sm py-8 text-center">
        No trades found. Click "Log Trade" to record your first entry.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="tbl-head">Date</th>
            <th className="tbl-head">Ticker</th>
            <th className="tbl-head">Type</th>
            <th className="tbl-head">Status</th>
            <th className="tbl-head text-right">Entry</th>
            <th className="tbl-head text-right">Exit</th>
            <th className="tbl-head text-right">Qty</th>
            <th className="tbl-head text-right">Net P&L</th>
            <th className="tbl-head text-right">P&L %</th>
            <th className="tbl-head">Strategy</th>
            <th className="tbl-head">Emotion</th>
            <th className="tbl-head text-right">Compliance</th>
            <th className="tbl-head text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="hover:bg-surface-2/50 transition-colors">
              <td className="tbl-cell text-muted text-xs whitespace-nowrap">
                {formatDate(t.entry_datetime)}
              </td>
              <td className="tbl-cell font-mono font-semibold text-bright">
                {t.ticker}
              </td>
              <td className="tbl-cell text-xs text-muted">
                {t.instrument_type.replace(/_/g, " ")}
              </td>
              <td className="tbl-cell">
                <span
                  className={clsx("badge", {
                    "badge-open": t.status === "open",
                    "badge-closed": t.status === "closed",
                    "badge-loss": t.status === "expired",
                  })}
                >
                  {t.status}
                </span>
              </td>
              <td className="tbl-cell text-right font-mono">
                {Number(t.entry_price).toFixed(2)}
              </td>
              <td className="tbl-cell text-right font-mono">
                {t.exit_price !== null && t.exit_price !== undefined ? Number(t.exit_price).toFixed(2) : "—"}
              </td>
              <td className="tbl-cell text-right font-mono">{t.quantity}</td>
              <td className={clsx("tbl-cell text-right font-mono", pnlClass(t.net_pnl !== undefined ? Number(t.net_pnl) : null))}>
                {t.net_pnl !== null && t.net_pnl !== undefined
                  ? `€${Number(t.net_pnl).toFixed(2)}`
                  : "—"}
              </td>
              <td className={clsx("tbl-cell text-right font-mono", pnlClass(t.net_pnl_pct !== undefined ? Number(t.net_pnl_pct) : null))}>
                {t.net_pnl_pct !== null && t.net_pnl_pct !== undefined
                  ? `${Number(t.net_pnl_pct).toFixed(1)}%`
                  : "—"}
              </td>
              <td className="tbl-cell text-xs text-muted">
                {t.strategy_category?.replace(/_/g, " ") ?? "—"}
              </td>
              <td className="tbl-cell text-xs">
                <span
                  className={clsx({
                    "text-profit": t.emotional_state_entry === "calm" || t.emotional_state_entry === "confident",
                    "text-loss": t.emotional_state_entry === "revenge" || t.emotional_state_entry === "fomo",
                    "text-warn": t.emotional_state_entry === "anxious" || t.emotional_state_entry === "excited",
                    "text-muted": !t.emotional_state_entry,
                  })}
                >
                  {t.emotional_state_entry ?? "—"}
                </span>
              </td>
              <td className="tbl-cell text-right font-mono text-xs">
                {t.rule_compliance_score !== null && t.rule_compliance_score !== undefined
                  ? `${(Number(t.rule_compliance_score) * 100).toFixed(0)}%`
                  : "—"}
              </td>
              <td className="tbl-cell text-center whitespace-nowrap">
                {t.status === "open" && (
                  <button
                    className="text-xs text-info hover:text-blue-400 mr-2"
                    onClick={() => onClose(t)}
                  >
                    Close
                  </button>
                )}
                <button
                  className="text-xs text-loss hover:text-red-400"
                  onClick={() => onDelete(t.id)}
                >
                  Del
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
