import React, { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPct, formatUsd, SIGNAL_CHIP } from "../../lib/utils";
import type { JournalRow } from "../../types";
import Panel from "../ui/Panel";
import Chip from "../ui/Chip";

/** Cumulative point on the arm equity curves. */
interface CurvePoint {
  label: string;
  cumPrice: number | null;
  cumInfo: number | null;
}

/** Build cumulative net-% curves per arm from settled journal rows. */
function buildCurves(rows: JournalRow[]): CurvePoint[] {
  let cumP = 0;
  let cumI = 0;
  const out: CurvePoint[] = [];
  const sorted = [...rows].sort((a, b) =>
    a.date === b.date ? a.coin_id.localeCompare(b.coin_id) : a.date < b.date ? -1 : 1
  );
  for (const r of sorted) {
    if (r.net_price !== null) cumP += r.net_price;
    if (r.net_info !== null) cumI += r.net_info;
    if (r.net_price !== null || r.net_info !== null) {
      out.push({
        label: `${r.date.slice(5)} ${r.coin_id.slice(0, 3)}`,
        cumPrice: Number(cumP.toFixed(3)),
        cumInfo: Number(cumI.toFixed(3)),
      });
    }
  }
  return out;
}

interface ArmTotals {
  settled: number;
  wins: number;
  totalNet: number;
  expectancy: number;
}

function armTotals(rows: JournalRow[], netKey: "net_price" | "net_info"): ArmTotals {
  const nets = rows
    .map((r) => r[netKey])
    .filter((n): n is number => n !== null);
  const wins = nets.filter((n) => n > 0).length;
  const total = nets.reduce((s, n) => s + n, 0);
  return {
    settled: nets.length,
    wins,
    totalNet: total,
    expectancy: nets.length ? total / nets.length : 0,
  };
}

/** JournalPnl — E006 ledger: cumulative arm curves + per-trade log. */
const JournalPnl: React.FC<{ rows: JournalRow[] }> = ({ rows }) => {
  const coins = useMemo(
    () => Array.from(new Set(rows.map((r) => r.coin_id))).sort(),
    [rows]
  );
  const [coinFilter, setCoinFilter] = useState<string>("all");

  const filtered = useMemo(
    () => (coinFilter === "all" ? rows : rows.filter((r) => r.coin_id === coinFilter)),
    [rows, coinFilter]
  );

  const curves = useMemo(() => buildCurves(filtered), [filtered]);
  const priceTotals = useMemo(() => armTotals(filtered, "net_price"), [filtered]);
  const infoTotals = useMemo(() => armTotals(filtered, "net_info"), [filtered]);
  const pendingCount = filtered.filter(
    (r) =>
      (r.signal_price !== "HOLD" && r.net_price === null) ||
      (r.signal_info !== "HOLD" && r.net_info === null)
  ).length;

  const sortedRows = useMemo(
    () =>
      [...filtered].sort((a, b) =>
        a.date === b.date ? a.coin_id.localeCompare(b.coin_id) : a.date < b.date ? -1 : 1
      ),
    [filtered]
  );

  return (
    <Panel
      title="Journal P&L · Forward Test Ledger"
      subtitle="Each non-HOLD arm settles against the next day's close, net of 0.3% round-trip costs"
      headerRight={
        <div className="flex items-center gap-1 rounded-lg border border-surface-line bg-surface-base p-1">
          <button
            onClick={() => setCoinFilter("all")}
            className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition ${
              coinFilter === "all"
                ? "bg-accent/15 text-accent"
                : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            All
          </button>
          {coins.map((c) => (
            <button
              key={c}
              onClick={() => setCoinFilter(c)}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold capitalize transition ${
                coinFilter === c
                  ? "bg-accent/15 text-accent"
                  : "text-ink-muted hover:text-ink-primary"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      }
    >
      {/* Arm totals */}
      <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {(
          [
            { name: "Price arm", t: priceTotals, tone: "text-ink-primary" },
            { name: "Info arm", t: infoTotals, tone: "text-accent" },
          ] as const
        ).map(({ name, t }) => (
          <React.Fragment key={name}>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wider text-ink-dim">
                {name} · settled
              </p>
              <p className="num mt-1 text-lg font-bold text-ink-primary">{t.settled}</p>
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-wider text-ink-dim">
                {name} · total net
              </p>
              <p
                className={`num mt-1 text-lg font-bold ${
                  t.totalNet > 0 ? "text-pos" : t.totalNet < 0 ? "text-neg" : "text-ink-primary"
                }`}
              >
                {t.settled ? formatPct(t.totalNet) : "--"}
              </p>
              <p className="text-[10px] text-ink-dim">
                {t.settled
                  ? `${t.wins}W · exp ${formatPct(t.expectancy, 3)}`
                  : "no settled trades"}
              </p>
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* Cumulative curves */}
      {curves.length === 0 ? (
        <div className="rounded-lg border border-dashed border-surface-line p-6 text-center">
          <p className="text-[13px] text-ink-muted">
            No settled trades yet — the journal just started logging.
          </p>
          <p className="mt-1 text-[11px] text-ink-dim">
            Arms log daily at 00:05 UTC (Celery beat) and settle on the next
            close. The E006 verdict needs 30 settled trades per arm; curves
            and the trade log will populate here as trades settle.
          </p>
        </div>
      ) : (
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={curves} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1C2540" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="label"
                minTickGap={30}
                tick={{ fill: "#8A94AC", fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: "#1C2540" }}
              />
              <YAxis
                tick={{ fill: "#8A94AC", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
                width={64}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0C111E",
                  border: "1px solid #1C2540",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#E9EEF8", fontWeight: 600 }}
                formatter={(value: number, name: string) => [
                  formatPct(value, 2),
                  name === "cumPrice" ? "Price arm" : "Info arm",
                ]}
              />
              <ReferenceLine y={0} stroke="#5B647C" strokeDasharray="4 4" />
              <Line
                type="monotone"
                dataKey="cumPrice"
                stroke="#8A94AC"
                strokeWidth={1.8}
                dot={{ r: 2.5 }}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="cumInfo"
                stroke="#38BDF8"
                strokeWidth={2}
                dot={{ r: 2.5 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Trade log */}
      {sortedRows.length > 0 && (
        <div className="mt-5 border-t border-surface-line pt-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-[13px] font-semibold text-ink-primary">Trade log</h3>
            {pendingCount > 0 && (
              <span className="num text-[11px] text-warn">
                {pendingCount} arm{pendingCount === 1 ? "" : "s"} pending settlement
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left">
              <thead className="border-b border-surface-line">
                <tr>
                  <th className="th">Date</th>
                  <th className="th">Asset</th>
                  <th className="th">Price arm</th>
                  <th className="th">Info arm</th>
                  <th className="th">Entry</th>
                  <th className="th">Net P</th>
                  <th className="th">Net I</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-line/60">
                {sortedRows
                  .slice()
                  .reverse()
                  .map((r, i) => {
                    const vetoed =
                      r.signal_price !== "HOLD" && r.signal_info === "HOLD";
                    const isPending = (net: number | null, sig: string) =>
                      sig !== "HOLD" && net === null;
                    const netCell = (net: number | null, win: boolean | null, sig: string) => {
                      if (net !== null) {
                        return (
                          <span
                            className={`num font-semibold ${
                              win ? "text-pos" : "text-neg"
                            }`}
                          >
                            {formatPct(net, 2)}
                          </span>
                        );
                      }
                      if (isPending(net, sig)) {
                        return (
                          <span className="chip border-warn/30 bg-warn/10 text-warn">
                            pending
                          </span>
                        );
                      }
                      return <span className="text-ink-dim">—</span>;
                    };
                    return (
                      <tr key={i} className="transition hover:bg-surface-raised/60">
                        <td className="td num text-ink-muted">{r.date}</td>
                        <td className="td font-semibold capitalize text-ink-primary">
                          {r.coin_id}
                        </td>
                        <td className="td">
                          <Chip className={SIGNAL_CHIP[r.signal_price as "BUY" | "SELL" | "HOLD"] ?? SIGNAL_CHIP.HOLD}>
                            {r.signal_price}
                          </Chip>
                        </td>
                        <td className="td">
                          {vetoed ? (
                            <Chip className="border-warn/40 bg-warn/10 text-warn" title="FinBERT veto — no trade">
                              HOLD · veto
                            </Chip>
                          ) : (
                            <Chip className={SIGNAL_CHIP[r.signal_info as "BUY" | "SELL" | "HOLD"] ?? SIGNAL_CHIP.HOLD}>
                              {r.signal_info}
                            </Chip>
                          )}
                        </td>
                        <td className="td num text-ink-muted">{formatUsd(r.price)}</td>
                        <td className="td">{netCell(r.net_price, r.win_price, r.signal_price)}</td>
                        <td className="td">{netCell(r.net_info, r.win_info, r.signal_info)}</td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Panel>
  );
};

export default JournalPnl;
