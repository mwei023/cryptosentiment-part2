import React from "react";
import { cn } from "../../lib/utils";

/** Chip — small status pill used for signals, band position, labels. */
const Chip: React.FC<{
  className?: string;
  children: React.ReactNode;
  title?: string;
}> = ({ className, children, title }) => (
  <span className={cn("chip", className)} title={title}>
    {children}
  </span>
);

export default Chip;
