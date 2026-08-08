import React from 'react';

type Props = {
  confidence: string;
};

const ConfidenceMeter: React.FC<Props> = ({ confidence }) => {
  const value = parseInt(confidence);
  let bgColor = 'bg-green-500';

  if (value < 50) bgColor = 'bg-red-500';
  else if (value < 75) bgColor = 'bg-yellow-500';

  return (
    <div className="mt-6">
      <p className="font-medium mb-1">Confidence Score: {confidence}</p>
      <div className="w-full h-4 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${bgColor} transition-all duration-500`}
          style={{ width: `${value}%` }}
        ></div>
      </div>
    </div>
  );
};

export default ConfidenceMeter;