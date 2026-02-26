import clsx from "clsx";
import type { MonthlyPnLPoint } from "../../types";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

interface Props {
  data: MonthlyPnLPoint[];
}

export default function MonthlyHeatmap({ data }: Props) {
  if (data.length === 0) return null;

  const years = [...new Set(data.map((d) => d.year))].sort();
  const lookup = new Map(data.map((d) => [`${d.year}-${d.month}`, d]));

  const maxAbs = Math.max(1, ...data.map((d) => Math.abs(d.net_pnl)));

  function cellColor(pnl: number): string {
    const intensity = Math.min(Math.abs(pnl) / maxAbs, 1);
    if (pnl > 0) return `rgba(34, 197, 94, ${0.15 + intensity * 0.6})`;
    if (pnl < 0) return `rgba(239, 68, 68, ${0.15 + intensity * 0.6})`;
    return "transparent";
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr>
            <th className="tbl-head">Year</th>
            {MONTHS.map((m) => (
              <th key={m} className="tbl-head text-center">
                {m}
              </th>
            ))}
            <th className="tbl-head text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {years.map((year) => {
            const yearTotal = data
              .filter((d) => d.year === year)
              .reduce((s, d) => s + d.net_pnl, 0);
            return (
              <tr key={year}>
                <td className="tbl-cell text-muted">{year}</td>
                {MONTHS.map((_, mi) => {
                  const entry = lookup.get(`${year}-${mi + 1}`);
                  return (
                    <td
                      key={mi}
                      className="tbl-cell text-center"
                      style={{ background: entry ? cellColor(entry.net_pnl) : undefined }}
                      title={
                        entry
                          ? `€${entry.net_pnl.toFixed(0)} (${entry.trade_count} trades)`
                          : undefined
                      }
                    >
                      {entry ? (
                        <span
                          className={clsx({
                            "text-profit": entry.net_pnl > 0,
                            "text-loss": entry.net_pnl < 0,
                            "text-muted": entry.net_pnl === 0,
                          })}
                        >
                          {entry.net_pnl >= 0 ? "+" : ""}
                          {entry.net_pnl.toFixed(0)}
                        </span>
                      ) : (
                        <span className="text-border">—</span>
                      )}
                    </td>
                  );
                })}
                <td
                  className={clsx("tbl-cell text-right font-semibold", {
                    "text-profit": yearTotal > 0,
                    "text-loss": yearTotal < 0,
                    "text-muted": yearTotal === 0,
                  })}
                >
                  €{yearTotal.toFixed(0)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
