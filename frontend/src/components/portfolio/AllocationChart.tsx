import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import type { ExposureBreakdown } from "../../types";

const COLORS = [
  "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
  "#06b6d4", "#ec4899", "#f97316", "#14b8a6", "#6366f1",
  "#a3e635", "#fb923c",
];

interface Props {
  data: ExposureBreakdown[];
}

export default function AllocationChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-muted text-xs py-4 text-center">No data</p>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            cx="50%"
            cy="50%"
            outerRadius={70}
            innerRadius={35}
            paddingAngle={2}
            stroke="none"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#161b27",
              border: "1px solid #2e3650",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number) => [`€${value.toLocaleString()}`, "Value"]}
          />
        </PieChart>
      </ResponsiveContainer>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 justify-center">
        {data.map((item, i) => (
          <div key={item.label} className="flex items-center gap-1.5 text-xs">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ background: COLORS[i % COLORS.length] }}
            />
            <span className="text-muted">{item.label}</span>
            <span className="font-mono text-bright">{item.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
