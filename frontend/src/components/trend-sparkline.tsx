"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

interface TrendData {
  month: string;
  avg_price_m2: number;
  num_transactions: number;
}

interface TrendSparklineProps {
  data: TrendData[];
}

function formatMonth(month: string): string {
  const [year, m] = month.split("-");
  const months = [
    "jan", "feb", "mar", "apr", "maj", "jun",
    "jul", "avg", "sep", "okt", "nov", "dec",
  ];
  return `${months[parseInt(m) - 1]} ${year.slice(2)}`;
}

export function TrendSparkline({ data }: TrendSparklineProps) {
  const chartData = data.map((d) => ({
    ...d,
    label: formatMonth(d.month),
  }));

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#E54E05" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#E54E05" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#737373", fontFamily: "Source Sans 3" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#737373", fontFamily: "Source Sans 3" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
            width={40}
          />
          <Tooltip
            formatter={(value) => [
              `${Number(value).toLocaleString("sl-SI")} EUR/m²`,
              "Povprečna cena",
            ]}
            labelFormatter={(label) => label}
            contentStyle={{
              fontSize: 13,
              fontFamily: "Source Sans 3",
              borderRadius: 12,
              border: "1px solid #e5e5e5",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
            }}
          />
          <Area
            type="monotone"
            dataKey="avg_price_m2"
            stroke="#E54E05"
            strokeWidth={2}
            fill="url(#colorPrice)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
