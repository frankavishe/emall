"use client";

import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis } from "recharts";

export type OrderStatusDatum = { status: string; count: number };

function titleCase(status: string): string {
  return status.charAt(0) + status.slice(1).toLowerCase();
}

export function OrderStatusBarChart({ data }: { data: OrderStatusDatum[] }) {
  const maxCount = Math.max(0, ...data.map((d) => d.count));

  return (
    <div className="h-64 w-full flex-1">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          barCategoryGap="22%"
          margin={{ top: 24, right: 0, left: 0, bottom: 0 }}
        >
          <XAxis
            dataKey="status"
            tickFormatter={titleCase}
            axisLine={{ stroke: "var(--color-border)" }}
            tickLine={false}
            tickMargin={10}
            tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
          />
          <Tooltip
            cursor={{ fill: "var(--color-card-muted)" }}
            labelFormatter={(label) => titleCase(String(label))}
            contentStyle={{
              borderRadius: 12,
              border: "1px solid var(--color-border)",
              background: "var(--color-card)",
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" radius={[12, 12, 0, 0]} minPointSize={4}>
            <LabelList
              dataKey="count"
              position="top"
              offset={8}
              style={{ fontSize: 13, fontWeight: 600, fill: "var(--color-text-primary)" }}
            />
            {data.map((entry) => (
              <Cell
                key={entry.status}
                fill={
                  entry.count === maxCount && maxCount > 0
                    ? "var(--color-teal-400)"
                    : "var(--color-teal-100)"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
