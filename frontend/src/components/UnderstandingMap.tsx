import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { UnderstandingMapEntry } from "../types/session";

export function UnderstandingMap({ entries }: { entries: UnderstandingMapEntry[] }) {
  const data = entries.map((entry) => ({
    concept: entry.concept_name,
    felt: entry.felt ?? 0,
    shown: entry.shown,
  }));

  return (
    <div className="w-full">
      <h2 className="mb-3 text-lg font-semibold">Understanding map</h2>
      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 70)}>
        <BarChart data={data} layout="vertical" margin={{ left: 16, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} />
          <YAxis type="category" dataKey="concept" width={140} />
          <Tooltip />
          <Legend />
          <Bar dataKey="felt" name="Felt (self-rated)" fill="#cbd5e1" radius={[0, 4, 4, 0]} />
          <Bar dataKey="shown" name="Shown (demonstrated)" fill="#f59e0b" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
