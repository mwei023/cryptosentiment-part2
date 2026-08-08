import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface DataPoint {
  name: string;
  Predicted: number;
  Lower: number;
  Upper: number;
}

interface PredictionChartProps {
  data: DataPoint[];
}

const PredictionChart: React.FC<PredictionChartProps> = ({ data }) => {
  return (
    <div className="w-full mt-6 bg-gray-800 p-4 rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Price Prediction</h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#4b5563" />
          
          <XAxis 
            dataKey="name" 
            tick={{ fill: '#e5e7eb' }} 
            axisLine={{ stroke: '#4b5563' }}
          />
          
          <YAxis 
            tick={{ fill: '#e5e7eb' }} 
            axisLine={{ stroke: '#4b5563' }}
          />

          <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }} />
          
          <Legend wrapperStyle={{ color: '#fff' }} />
          
          <Line 
            type="monotone" 
            dataKey="Predicted" 
            stroke="#3b82f6" 
            strokeWidth={2} 
            dot={{ r: 4 }} 
            activeDot={{ r: 6 }}
          />
          
          <Line 
            type="monotone" 
            dataKey="Lower" 
            stroke="#ef4444"
            strokeDasharray="5 5"
            dot={false}
          />
          
          <Line 
            type="monotone" 
            dataKey="Upper" 
            stroke="#10b981" 
            strokeDasharray="5 5"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PredictionChart;