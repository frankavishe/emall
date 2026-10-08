"use client";

import { RadialBar, RadialBarChart, PolarAngleAxis, ResponsiveContainer } from "recharts";

type RadialGaugeProps = {
  value: number;
  max?: number;
  caption: string;
  /** Appended to the centre figure, e.g. "%". */
  suffix?: string;
};

export function RadialGauge({ value, max = 100, caption, suffix = "" }: RadialGaugeProps) {
  const data = [{ name: caption, value: Math.min(value, max) }];

  return (
    <div className="relative h-56 w-full">
      <svg width={0} height={0}>
        <defs>
          <linearGradient id="gaugeGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--color-teal-gradient-from)" />
            <stop offset="100%" stopColor="var(--color-teal-gradient-to)" />
          </linearGradient>
        </defs>
      </svg>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          data={data}
          innerRadius="78%"
          outerRadius="100%"
          startAngle={90}
          endAngle={-270}
          barSize={14}
        >
          <PolarAngleAxis type="number" domain={[0, max]} angleAxisId={0} tick={false} />
          <RadialBar
            dataKey="value"
            cornerRadius={8}
            fill="url(#gaugeGradient)"
            background={{ fill: "var(--color-card-muted)" }}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold tracking-tight text-text-primary">
          {Math.round(value)}
          {suffix}
        </span>
        <span className="text-xs text-text-muted">{caption}</span>
      </div>
    </div>
  );
}
