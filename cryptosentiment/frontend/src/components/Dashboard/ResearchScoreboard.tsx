import React from 'react';

interface ArmStats {
  settled?: number;
  wins?: number;
  losses?: number;
  win_rate_pct?: number;
  expectancy_pct?: number;
  total_net_pct?: number;
  profit_factor?: number;
}

interface ResearchScoreboardProps {
  report: any;
  scoreboard: any;
}

const ResearchScoreboard: React.FC<ResearchScoreboardProps> = ({ report, scoreboard }) => {
  const priceArm: ArmStats = scoreboard?.price || {};
  const infoArm: ArmStats = scoreboard?.info || {};
  const vetoes = scoreboard?.vetoes ?? 0;
  const settledRows = scoreboard?.settled_rows ?? 0;

  const perCoin = report?.per_coin || {};
  const maturity = report?.maturity || { settled_slowest_arm: 0, required_per_arm: 30, to_go: 30 };
  const progressPct = Math.min(100, Math.round((maturity.settled_slowest_arm / maturity.required_per_arm) * 100));

  return (
    <div className="w-full mt-6 space-y-6">
      {/* E006 Head-to-Head Scoreboard */}
      <div className="bg-gray-800 p-6 rounded-lg shadow-md border border-gray-700">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span>🔬</span> E006 Dual-Arm Live Scoreboard
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              H005 Information Test: Does FinBERT majority news veto improve risk-adjusted expectancy over price-only signals?
            </p>
          </div>
          <div className="mt-2 md:mt-0 text-right">
            <span className="text-xs font-mono bg-blue-900/50 text-blue-300 px-2 py-1 rounded border border-blue-700">
              Maturity: {maturity.settled_slowest_arm} / {maturity.required_per_arm} settled trades
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-700 h-2 rounded-full mb-6 overflow-hidden">
          <div
            className="bg-blue-500 h-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Arm Comparison Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Price-Only Arm */}
          <div className="bg-gray-900/70 p-4 rounded-lg border border-gray-700/80">
            <div className="flex justify-between items-center mb-3">
              <span className="font-semibold text-gray-200">Arm A: Price-Only</span>
              <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">Baseline</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-gray-400 text-xs">Settled Trades</p>
                <p className="text-lg font-bold text-white">{priceArm.settled ?? 0}</p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Net Expectancy</p>
                <p className={`text-lg font-bold ${(priceArm.expectancy_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {(priceArm.expectancy_pct ?? 0) > 0 ? '+' : ''}{priceArm.expectancy_pct ?? 0}%
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Profit Factor</p>
                <p className="text-lg font-bold text-white">{priceArm.profit_factor ?? '--'}</p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Win Rate</p>
                <p className="text-lg font-bold text-white">{priceArm.win_rate_pct ?? 0}%</p>
              </div>
            </div>
          </div>

          {/* Info-Enhanced Arm */}
          <div className="bg-gray-900/70 p-4 rounded-lg border border-blue-900/40">
            <div className="flex justify-between items-center mb-3">
              <span className="font-semibold text-blue-300">Arm B: Info-Enhanced (FinBERT Veto)</span>
              <span className="text-xs bg-blue-900/60 text-blue-300 px-2 py-0.5 rounded">Active Test</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-gray-400 text-xs">Settled Trades</p>
                <p className="text-lg font-bold text-white">{infoArm.settled ?? 0}</p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Net Expectancy</p>
                <p className={`text-lg font-bold ${(infoArm.expectancy_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {(infoArm.expectancy_pct ?? 0) > 0 ? '+' : ''}{infoArm.expectancy_pct ?? 0}%
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Profit Factor</p>
                <p className="text-lg font-bold text-white">{infoArm.profit_factor ?? '--'}</p>
              </div>
              <div>
                <p className="text-gray-400 text-xs">Win Rate</p>
                <p className="text-lg font-bold text-white">{infoArm.win_rate_pct ?? 0}%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Vetoes callout */}
        <div className="mt-4 pt-3 border-t border-gray-700/60 flex justify-between items-center text-xs text-gray-400">
          <span>Total FinBERT Sentiment Vetoes Applied: <strong className="text-white">{vetoes}</strong></span>
          <span>Settled Rows: <strong className="text-white">{settledRows}</strong></span>
        </div>
      </div>

      {/* Today's Band & Signal Watch */}
      <div className="bg-gray-800 p-6 rounded-lg shadow-md border border-gray-700">
        <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
          <span>📡</span> Market Signal & Volatility Band Watch
        </h3>
        <p className="text-xs text-gray-400 mb-4">
          Signals trigger when daily price touches 80% empirical volatility bands. Trades settle next-day at market close.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-gray-900/60 text-xs uppercase text-gray-400">
              <tr>
                <th className="p-3">Asset</th>
                <th className="p-3">Price Signal</th>
                <th className="p-3">Info Signal</th>
                <th className="p-3">Position</th>
                <th className="p-3">News Breakdown</th>
                <th className="p-3">Action Watch</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {Object.entries(perCoin).map(([coinId, data]: [string, any]) => {
                const isVetoed = data.vetoed;
                const pos = data.band_position || 'inside';
                const posBadge =
                  pos === 'below_lower'
                    ? 'bg-emerald-900/60 text-emerald-300 border-emerald-700'
                    : pos === 'above_upper'
                    ? 'bg-rose-900/60 text-rose-300 border-rose-700'
                    : 'bg-gray-700/60 text-gray-300 border-gray-600';

                return (
                  <tr key={coinId} className="hover:bg-gray-750">
                    <td className="p-3 font-semibold text-white capitalize">{coinId}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
                        data.signal_price === 'BUY' ? 'bg-emerald-900 text-emerald-300' :
                        data.signal_price === 'SELL' ? 'bg-rose-900 text-rose-300' : 'bg-gray-700 text-gray-300'
                      }`}>
                        {data.signal_price || 'HOLD'}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
                        isVetoed ? 'bg-amber-900 text-amber-300 line-through' :
                        data.signal_info === 'BUY' ? 'bg-emerald-900 text-emerald-300' :
                        data.signal_info === 'SELL' ? 'bg-rose-900 text-rose-300' : 'bg-gray-700 text-gray-300'
                      }`}>
                        {data.signal_info || 'HOLD'}
                      </span>
                      {isVetoed && <span className="ml-1.5 text-xs text-amber-400 font-semibold">(VETOED)</span>}
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-xs border ${posBadge}`}>
                        {pos}
                      </span>
                    </td>
                    <td className="p-3 text-xs">
                      {data.sentiment?.n ? (
                        <span>
                          {data.sentiment.n} total (<span className="text-emerald-400">{data.sentiment.pos}+</span>,{' '}
                          <span className="text-gray-400">{data.sentiment.neu}=</span>,{' '}
                          <span className="text-rose-400">{data.sentiment.neg}-</span>)
                        </span>
                      ) : (
                        <span className="text-gray-500">None</span>
                      )}
                    </td>
                    <td className="p-3 text-xs text-gray-300 font-mono">
                      {data.watch || '--'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ResearchScoreboard;
