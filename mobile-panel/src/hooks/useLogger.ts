// Custom hook for managing action logs

import { useState, useCallback } from "react";

export interface LogEntry {
  id: string;
  timestamp: string;
  message: string;
}

export function useLogger(maxLogs: number = 35) {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const addLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString("en-US", { 
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
    
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp,
      message,
    };

    setLogs((prev) => [entry, ...prev].slice(0, maxLogs));
  }, [maxLogs]);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  return { logs, addLog, clearLogs };
}
