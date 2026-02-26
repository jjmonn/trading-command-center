import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import type { EquityCurvePoint } from "../../types";

interface Props {
  data: EquityCurvePoint[];
}

export default function EquityChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2e3650" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#6b7280", fontSize: 11 }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          yAxisId="pnl"
          tick={{ fill: "#6b7280", fontSize: 11 }}
          tickFormatter={(v: number) => `€${v}`}
        />
        <YAxis
          yAxisId="dd"
          orientation="right"
          tick={{ fill: "#6b7280", fontSize: 11 }}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip
          contentStyle={{
            background: "#161b27",
            border: "1px solid #2e3650",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value: number, name: string) =>
            name === "cumulative_pnl"
              ? [`€${value.toFixed(2)}`, "Cumulative P&L"]
              : [`${value.toFixed(2)}%`, "Drawdown"]
          }
        />
        <ReferenceLine yAxisId="pnl" y={0} stroke="#2e3650" />
        <Area
          yAxisId="dd"
          type="monotone"
          dataKey="drawdown_pct"
          fill="#ef444430"
          stroke="#ef4444"
          strokeWidth={1}
        />
        <Line
          yAxisId="pnl"
          type="monotone"
          dataKey="cumulative_pnl"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
