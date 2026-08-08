import React from 'react';

type PredictionEntry = {
  date: string;
  predicted: number;
  lower: number;
  upper: number;
  confidence: string;
};

type Props = {
  predictions: PredictionEntry[];
};

const PredictionHistoryTable: React.FC<Props> = ({ predictions }) => {
  return (
    <div className="mt-6 overflow-x-auto">
      <h3 className="text-lg font-semibold mb-4">Prediction History</h3>
      <table className="min-w-full bg-card text-card-foreground rounded-md shadow-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="px-4 py-2 text-left">Date</th>
            <th className="px-4 py-2 text-left">Predicted</th>
            <th className="px-4 py-2 text-left">Lower</th>
            <th className="px-4 py-2 text-left">Upper</th>
            <th className="px-4 py-2 text-left">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((pred, index) => (
            <tr key={index} className="hover:bg-muted transition-colors">
              <td className="px-4 py-2">{pred.date}</td>
              <td className="px-4 py-2">${pred.predicted.toLocaleString()}</td>
              <td className="px-4 py-2">${pred.lower.toLocaleString()}</td>
              <td className="px-4 py-2">${pred.upper.toLocaleString()}</td>
              <td className="px-4 py-2 font-medium">{pred.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PredictionHistoryTable;