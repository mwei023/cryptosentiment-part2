import React from "react";
import { CORE_COINS, isKnownCoin } from "../../hooks/useDashboard";
import { cn } from "../../lib/utils";
import Spinner from "../ui/Spinner";

const TopBar: React.FC<{
  coin: string;
  onCoinChange: (coin: string) => void;
  onRefresh: () => void;
  refreshing: boolean;
  lastRefreshed: Date | null;
}> = ({ coin, onCoinChange, onRefresh, refreshing, lastRefreshed }) => {
  const known = CORE_COINS.find((c) => c.id === coin);
  const isCustom = !known && coin.trim().length > 0;

  return (
    <header className="sticky top-0 z-20 border-b border-surface-line bg-surface-base/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
        {/* Brand */}          <div className="flex items-center gap-3">
            <div
              title="CryptoSentiment Research Terminal"
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-accent/40 bg-accent/15 text-sm font-bold text-accent"
            >
              CS
            </div>
          <div className="leading-tight">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-ink-primary">
                CryptoSentiment
              </span>
              <span className="chip border-accent/30 bg-accent/10 font-mono text-[10px] text-accent">
                v0.3 · E006
              </span>
            </div>
            <p className="text-[11px] text-ink-dim">
              Empirical forecasting · FinBERT sentiment · dual-arm forward test
            </p>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-3">
          {/* Coin picker */}
          <label className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-dim">
              Asset
            </span>
            <select
              value={isKnownCoin(coin) || coin === "" ? coin : "__custom"}
              onChange={(e) => {
                if (e.target.value === "__custom") return;
                onCoinChange(e.target.value);
              }}
              className="rounded-lg border border-surface-line bg-surface-overlay px-3 py-1.5 text-[13px] font-semibold text-ink-primary focus:border-accent/50 focus:outline-none"
            >
              {CORE_COINS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.symbol})
                </option>
              ))}
              {isCustom && (
                <option value="__custom">{coin} (custom slug)</option>
              )}
            </select>
          </label>

          {/* Custom coin slug entry (any CoinGecko id) */}
          <input
            value={coin}
            onChange={(e) => onCoinChange(e.target.value.trim())}
            spellCheck={false}
            placeholder="or type any coingecko id…"
            className={cn(
              "num w-44 rounded-lg border border-surface-line bg-surface-overlay px-3 py-1.5 text-xs text-ink-primary placeholder:text-ink-dim focus:border-accent/50 focus:outline-none",
              isCustom && "border-accent/50"
            )}
          />

          {/* Refresh */}
          <button onClick={onRefresh} disabled={refreshing} className="btn btn-ghost">
            {refreshing ? (
              <Spinner />
            ) : (
              <svg
                aria-hidden
                viewBox="0 0 20 20"
                fill="none"
                className="h-3.5 w-3.5"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 10a6 6 0 0 1 10.2-4.2L16 7.5M16 10a6 6 0 0 1-10.2 4.2L4 12.5"
                />
                <path strokeLinecap="round" d="M16 3v4.5h-4.5M4 17v-4.5h4.5" />
              </svg>
            )}
            Refresh
          </button>
          {lastRefreshed && (
            <span className="num hidden text-[11px] text-ink-dim lg:inline">
              {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    </header>
  );
};

export default TopBar;
