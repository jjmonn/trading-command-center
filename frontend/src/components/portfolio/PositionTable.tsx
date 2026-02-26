import clsx from "clsx";
import type { Position } from "../../types";

interface Props {
  positions: Position[];
  onEdit: (p: Position) => void;
  onDelete: (id: number) => void;
}

function pnlClass(val: number | null | undefined): string {
  if (val === null || val === undefined) return "text-muted";
  return val >= 0 ? "pnl-pos" : "pnl-neg";
}

export default function PositionTable({ positions, onEdit, onDelete }: Props) {
  if (positions.length === 0) {
    return (
      <div className="text-muted text-sm py-8 text-center">
        No positions. Add manual positions or sync from IB.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="tbl-head">Ticker</th>
            <th className="tbl-head">Type</th>
            <th className="tbl-head text-right">Qty</th>
            <th className="tbl-head text-right">Avg Cost</th>
            <th className="tbl-head text-right">Mkt Price</th>
            <th className="tbl-head text-right">Mkt Value</th>
            <th className="tbl-head text-right">P&L</th>
            <th className="tbl-head text-right">P&L %</th>
            <th className="tbl-head text-right">Weight</th>
            <th className="tbl-head text-right">DTE</th>
            <th className="tbl-head">Sector</th>
            <th className="tbl-head">Source</th>
            <th className="tbl-head text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.id} className="hover:bg-surface-2/50 transition-colors">
              <td className="tbl-cell font-mono font-semibold text-bright">{p.ticker}</td>
              <td className="tbl-cell text-xs text-muted">{p.instrument_type.replace(/_/g, " ")}</td>
              <td className="tbl-cell text-right font-mono">{p.quantity}</td>
              <td className="tbl-cell text-right font-mono">
                {p.avg_cost != null ? Number(p.avg_cost).toFixed(2) : "—"}
              </td>
              <td className="tbl-cell text-right font-mono">
                {p.market_price != null ? Number(p.market_price).toFixed(2) : "—"}
              </td>
              <td className="tbl-cell text-right font-mono">
                {p.market_value != null ? `€${Number(p.market_value).toLocaleString("en", { minimumFractionDigits: 0 })}` : "—"}
              </td>
              <td className={clsx("tbl-cell text-right font-mono", pnlClass(p.unrealized_pnl != null ? Number(p.unrealized_pnl) : null))}>
                {p.unrealized_pnl != null ? `€${Number(p.unrealized_pnl).toFixed(0)}` : "—"}
              </td>
              <td className={clsx("tbl-cell text-right font-mono", pnlClass(p.pnl_pct != null ? p.pnl_pct : null))}>
                {p.pnl_pct != null ? `${p.pnl_pct.toFixed(1)}%` : "—"}
              </td>
              <td className="tbl-cell text-right font-mono text-muted">
                {p.weight_pct != null ? `${p.weight_pct.toFixed(1)}%` : "—"}
              </td>
              <td className={clsx("tbl-cell text-right font-mono", {
                "text-loss": p.dte != null && p.dte < 30,
                "text-warn": p.dte != null && p.dte >= 30 && p.dte < 60,
                "text-muted": p.dte == null || p.dte >= 60,
              })}>
                {p.dte != null ? p.dte : "—"}
              </td>
              <td className="tbl-cell text-xs text-muted">{p.sector ?? "—"}</td>
              <td className="tbl-cell">
                <span className={clsx("badge text-xs", {
                  "badge-open": p.source === "ib",
                  "badge-closed": p.source === "manual",
                })}>
                  {p.source ?? "manual"}
                </span>
              </td>
              <td className="tbl-cell text-center whitespace-nowrap">
                <button className="text-xs text-info hover:text-blue-400 mr-2" onClick={() => onEdit(p)}>
                  Edit
                </button>
                <button className="text-xs text-loss hover:text-red-400" onClick={() => onDelete(p.id)}>
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
