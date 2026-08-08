import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

type SentimentData = {
  name: string;
  value: number;
};

interface SentimentPieChartProps {
  data: SentimentData[];
}

const COLORS = ['#10b981', '#ef4444']; // Green for POSITIVE, Red for NEGATIVE

const SentimentPieChart: React.FC<SentimentPieChartProps> = ({ data }) => {
  return (
    <PieChart width={300} height={250}>
      <Pie
        data={data}
        cx="50%"
        cy="50%"
        outerRadius={80}
        fill="#8884d8"
        dataKey="value"
        label
      >
        {data.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
        ))}
      </Pie>
      <Tooltip />
      <Legend />
    </PieChart>
  );
};

export default SentimentPieChart;