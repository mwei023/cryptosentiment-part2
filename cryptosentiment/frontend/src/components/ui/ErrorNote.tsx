import React from "react";
import { cn } from "../../lib/utils";

/** ErrorNote — inline error banner with FastAPI detail message. */
const ErrorNote: React.FC<{ message?: string | null; className?: string }> = ({
  message,
  className,
}) => {
  if (!message) return null;
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-2 rounded-lg border border-neg/30 bg-neg/10 px-3.5 py-2.5 text-[13px] text-neg",
        className
      )}
    >
      <span aria-hidden className="mt-0.5">⚠</span>
      <span className="min-w-0 break-words">{message}</span>
    </div>
  );
};

export default ErrorNote;
