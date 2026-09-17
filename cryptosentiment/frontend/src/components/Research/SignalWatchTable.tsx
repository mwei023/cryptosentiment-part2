import React from "react";
import { cn, formatNum, SIGNAL_CHIP } from "../../lib/utils";
import type { DailyReport } from "../../types";
import Panel from "../ui/Panel";
import Chip from "../ui/Chip";

/** Dual-arm signal chip; vetoed info-arm shows struck-through HOLD. */
function SignalChip({ signal, vetoed }: { signal?: string; vetoed?: boolean }) {
  const s = (signal ?? "HOLD") as "BUY" | "SELL" | "HOLD";
  if (vetoed) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <Chip className="border-warn/40 bg-warn/10 text-warn" title="FinBERT veto — no trade">
          HOLD
        </Chip>
        <span className="num text-[10px] text-warn">veto</span>
      </span>
    );
  }
  return <Chip className={SIGNAL_CHIP[s]}>{s}</Chip>;
}

/** SignalWatchTable — today's price-arm vs info-arm per coin, from the report. */
const SignalWatchTable: React.FC<{ report: DailyReport | null }> = ({ report }) => {
  const rows = Object.entries(report?.per_coin ?? {});

  return (
    <Panel
      title="Today's Dual-Arm Signals"
      subtitle={
        report?.date
          ? `Report ${report.date} · settlement watch: non-HOLD arms settle on tomorrow's close`
          : "Per-coin price vs info signals"
      }
      bodyClassName="p-0"
    >
      {rows.length === 0 ? (
        <p className="p-5 text-[13px] text-ink-dim">
          No report data available.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left">
            <thead className="border-b border-surface-line">
              <tr>
                <th className="th">Asset</th>
                <th className="th">Price arm</th>
                <th className="th">Info arm</th>
                <th className="th">Conf (p → i)</th>
                <th className="th">News</th>
                <th className="th">Watch</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-line/60">
              {rows.map(([coin, r]) => (
                <tr key={coin} className="transition hover:bg-surface-raised/60">
                  <td className="td font-semibold capitalize text-ink-primary">
                    {coin}
                    {r.error && (
                      <span className="ml-2 text-[11px] font-normal text-neg">
                        error
                      </span>
                    )}
                  </td>
                  <td className="td">
                    <SignalChip signal={r.signal_price} />
                  </td>
                  <td className="td">
                    <SignalChip signal={r.signal_info} vetoed={r.vetoed} />
                  </td>
                  <td className="td num text-ink-muted">
                    {r.conf_price != null ? formatNum(r.conf_price, 1) : "--"}
                    {" → "}
                    {r.conf_info != null ? formatNum(r.conf_info, 1) : "--"}
                  </td>
                  <td className="td text-[12px]">
                    {r.sentiment?.n ? (
                      <span className="num">
                        <span className="text-pos">{r.sentiment.pos}+</span>{" "}
                        <span className="text-ink-dim">{r.sentiment.neu}=</span>{" "}
                        <span className="text-neg">{r.sentiment.neg}−</span>
                        <span className="ml-1.5 text-ink-dim">
                          /{r.sentiment.n}
                        </span>
                      </span>
                    ) : (
                      <span className="text-ink-dim">—</span>
                    )}
                  </td>
                  <td
                    className={cn(
                      "td max-w-[280px] text-[11px] leading-snug text-ink-muted",
                      r.error && "text-neg"
                    )}
                  >
                    {r.error ?? r.watch ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
};

export default SignalWatchTable;
