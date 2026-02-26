import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import type { PortfolioHistoryPoint } from "../../types";

interface Props {
  data: PortfolioHistoryPoint[];
}

export default function NAVChart({ data }: Props) {
  if (data.length === 0) return null;

  const chartData = data.map((d) => ({
    date: d.timestamp.slice(0, 10),
    nav: d.total_nav ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2e3650" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#6b7280", fontSize: 11 }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          tick={{ fill: "#6b7280", fontSize: 11 }}
          tickFormatter={(v: number) => `€${v.toLocaleString()}`}
        />
        <Tooltip
          contentStyle={{
            background: "#161b27",
            border: "1px solid #2e3650",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value: number) => [`€${value.toLocaleString()}`, "NAV"]}
        />
        <Line type="monotone" dataKey="nav" stroke="#3b82f6" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
