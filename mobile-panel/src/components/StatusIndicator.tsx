// Status indicator component for connection status

interface StatusIndicatorProps {
  label: string;
  status: "ok" | "bad" | "neutral";
}

export function StatusIndicator({ label, status }: StatusIndicatorProps) {
  return (
    <span className={`pill ${status}`}>
      {label}
    </span>
  );
}
