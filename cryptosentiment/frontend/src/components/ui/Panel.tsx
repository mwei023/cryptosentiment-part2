import React from "react";
import { cn } from "../../lib/utils";

/**
 * Panel — the standard content container: surface, border, header row,
 * and optional right-aligned header slot.
 */
const Panel: React.FC<{
  title?: string;
  subtitle?: string;
  headerRight?: React.ReactNode;
  bodyClassName?: string;
  className?: string;
  children: React.ReactNode;
}> = ({ title, subtitle, headerRight, bodyClassName, className, children }) => (
  <section className={cn("panel", className)}>
    {(title || headerRight) && (
      <header className="panel-head">
        <div className="min-w-0">
          {title && <h2 className="panel-title">{title}</h2>}
          {subtitle && (
            <p className="mt-0.5 text-xs text-ink-dim">{subtitle}</p>
          )}
        </div>
        {headerRight && <div className="shrink-0">{headerRight}</div>}
      </header>
    )}
    <div className={cn("p-5", bodyClassName)}>{children}</div>
  </section>
);

export default Panel;
