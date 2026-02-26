import clsx from "clsx";

interface Props {
  label: string;
  value: string;
  color?: "profit" | "loss";
}

export default function MetricCard({ label, value, color }: Props) {
  return (
    <div className="card flex flex-col items-start gap-1">
      <span className="metric-label">{label}</span>
      <span
        className={clsx("metric-value text-xl", {
          "text-profit": color === "profit",
          "text-loss": color === "loss",
          "text-bright": !color,
        })}
      >
        {value}
      </span>
    </div>
  );
}
