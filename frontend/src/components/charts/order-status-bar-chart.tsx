"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts";

export type OrderStatusDatum = { status: string; count: number };

export function OrderStatusBarChart({ data }: { data: OrderStatusDatum[] }) {
  const maxCount = Math.max(0, ...data.map((d) => d.count));

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barCategoryGap="30%">
          <XAxis
            dataKey="status"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
          />
          <Tooltip
            cursor={{ fill: "var(--color-card-muted)" }}
            contentStyle={{
              borderRadius: 12,
              border: "1px solid var(--color-border)",
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" radius={[8, 8, 8, 8]}>
            {data.map((entry) => (
              <Cell
                key={entry.status}
                fill={entry.count === maxCount && maxCount > 0 ? "var(--color-teal-400)" : "var(--color-teal-100)"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
