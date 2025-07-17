import React from 'react';
import { useTheme } from '../lib/theme';

const Sidebar: React.FC<{
  coin: string;
  setCoin: (coin: string) => void;
}> = ({ coin, setCoin }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="w-64 bg-card min-h-screen p-4">
      <h2 className="text-lg font-semibold mb-4">Crypto Selector</h2>
      
      <input
        type="text"
        value={coin}
        onChange={(e) => setCoin(e.target.value)}
        placeholder="Enter coin ID"
        className="w-full p-2 border rounded-md bg-muted"
      />

      <button
        onClick={toggleTheme}
        className="mt-4 w-full py-2 px-4 bg-accent hover:bg-muted rounded-md"
      >
        Toggle {theme === 'dark' ? 'Light' : 'Dark'} Mode
      </button>
    </div>
  );
};

export default Sidebar;