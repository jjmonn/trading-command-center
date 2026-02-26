import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import type { BreakdownItem } from "../../types";

interface Props {
  data: BreakdownItem[];
}

export default function BreakdownChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-muted text-xs py-4 text-center">No data yet.</p>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={Math.max(120, data.length * 32 + 20)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 20, bottom: 0, left: 0 }}
        >
          <XAxis
            type="number"
            tick={{ fill: "#6b7280", fontSize: 10 }}
            tickFormatter={(v: number) => `€${v}`}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fill: "#6b7280", fontSize: 10 }}
            width={100}
          />
          <Tooltip
            contentStyle={{
              background: "#161b27",
              border: "1px solid #2e3650",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number) => [`€${value.toFixed(2)}`, "P&L"]}
          />
          <Bar dataKey="total_pnl" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.total_pnl >= 0 ? "#22c55e" : "#ef4444"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Table below the chart */}
      <table className="w-full text-xs font-mono mt-2">
        <thead>
          <tr>
            <th className="tbl-head">Label</th>
            <th className="tbl-head text-right">Count</th>
            <th className="tbl-head text-right">Win Rate</th>
            <th className="tbl-head text-right">Expectancy</th>
            <th className="tbl-head text-right">Total P&L</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.label}>
              <td className="tbl-cell text-bright">{row.label}</td>
              <td className="tbl-cell text-right text-muted">{row.count}</td>
              <td className="tbl-cell text-right">
                {row.win_rate !== null ? `${(row.win_rate * 100).toFixed(0)}%` : "—"}
              </td>
              <td className="tbl-cell text-right">
                {row.expectancy !== null ? `€${row.expectancy.toFixed(0)}` : "—"}
              </td>
              <td
                className={`tbl-cell text-right ${
                  row.total_pnl >= 0 ? "text-profit" : "text-loss"
                }`}
              >
                €{row.total_pnl.toFixed(0)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
