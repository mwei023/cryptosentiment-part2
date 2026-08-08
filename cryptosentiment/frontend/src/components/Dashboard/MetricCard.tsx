import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string | number;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, change }) => {
  const isPositive = typeof change === 'string'
    ? change.includes('+') || change.includes('Positive')
    : (change || 0) > 0;

  return (
    <div className="bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-sm">
      <h3 className="text-sm font-medium text-gray-300">{title}</h3>
      <p className="text-2xl font-bold mt-2 text-white">${value}</p>
      {change && (
        <p className={`text-sm mt-1 ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
          {typeof change === 'number' ? `${change.toFixed(2)}%` : change}
        </p>
      )}
    </div>
  );
};

export default MetricCard;