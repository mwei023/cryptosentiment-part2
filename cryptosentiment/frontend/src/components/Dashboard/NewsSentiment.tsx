import React from 'react';

// Define the shape of each news item
type NewsItem = {
  label: string;
  score: number;
  text: string;
};

// Define props for the component
interface NewsSentimentProps {
  news: NewsItem[];
}

const NewsSentimentPanel: React.FC<NewsSentimentProps> = ({ news }) => {
  if (!news || news.length === 0) return null;

  return (
    <div className="mt-6 bg-gray-800 p-4 rounded-lg shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Latest News & Sentiment</h3>
      
      <div className="space-y-3">
        {news.map((item: NewsItem, index: number) => (
          <div key={index} className="p-3 border border-gray-700 rounded-md hover:bg-gray-700 transition-colors">
            <p>{item.text}</p>
            <p className={`font-medium ${item.label === "POSITIVE" ? "text-green-500" : "text-red-500"}`}>
              {item.label} ({(item.score * 100).toFixed(1)}%)
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NewsSentimentPanel;