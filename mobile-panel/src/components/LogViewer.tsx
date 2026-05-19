// Log viewer component for displaying action logs

import type { LogEntry } from "@hooks/useLogger";

interface LogViewerProps {
  logs: LogEntry[];
}

export function LogViewer({ logs }: LogViewerProps) {
  return (
    <section className="log-card">
      <h3>Action Log</h3>
      <div className="log-list">
        {logs.length === 0 ? (
          <div>No actions yet.</div>
        ) : (
          logs.map((log) => (
            <div key={log.id}>
              {log.timestamp} | {log.message}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
