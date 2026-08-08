import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

type TrendData = {
  date: string;
  confidence: number;
};

type Props = {
  data: TrendData[];
};

const ConfidenceTrend: React.FC<Props> = ({ data }) => {
  return (
    <div className="mt-6 bg-card p-4 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-2">Confidence Trend</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <XAxis dataKey="date" />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Line type="monotone" dataKey="confidence" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ConfidenceTrend;