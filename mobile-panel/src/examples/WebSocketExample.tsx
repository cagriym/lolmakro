/**
 * Example component demonstrating WebSocket usage
 * 
 * This file shows various patterns for using the WebSocket service
 * in a React application with Zustand state management.
 */

import { useEffect, useState } from "react";
import { useWebSocket } from "@hooks/useWebSocket";
import { useAppStore } from "@/store/useAppStore";
import { ConnectionStatus } from "@services/websocket";

/**
 * Example 1: Basic WebSocket connection with status display
 */
export function BasicWebSocketExample() {
  useWebSocket({ autoConnect: true });

  const connectionStatus = useAppStore((state) => state.connectionStatus);
  const phase = useAppStore((state) => state.phase);
  const connected = useAppStore((state) => state.connected);

  return (
    <div className="example">
      <h2>Basic WebSocket Connection</h2>
      <div>
        <p>Connection Status: {connectionStatus}</p>
        <p>LCU Connected: {connected ? "Yes" : "No"}</p>
        <p>Game Phase: {phase}</p>
      </div>
    </div>
  );
}

/**
 * Example 2: WebSocket with reconnection monitoring
 */
export function ReconnectionExample() {
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastReconnectDelay, setLastReconnectDelay] = useState(0);

  useWebSocket({
    autoConnect: true,
    onReconnecting: (attempt, delay) => {
      setReconnectAttempts(attempt);
      setLastReconnectDelay(delay);
    },
  });

  const connectionStatus = useAppStore((state) => state.connectionStatus);

  return (
    <div className="example">
      <h2>Reconnection Monitoring</h2>
      <div>
        <p>Status: {connectionStatus}</p>
        {connectionStatus === ConnectionStatus.RECONNECTING && (
          <div>
            <p>Reconnection Attempt: {reconnectAttempts}</p>
            <p>Next Retry In: {lastReconnectDelay}ms</p>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Example 3: Champion Select state monitoring
 */
export function ChampSelectExample() {
  useWebSocket({ autoConnect: true });

  const phase = useAppStore((state) => state.phase);
  const champSelect = useAppStore((state) => state.champSelect);
  const mySelection = useAppStore((state) => state.mySelection);

  if (phase !== "ChampSelect") {
    return (
      <div className="example">
        <h2>Champion Select Monitor</h2>
        <p>Not in champion select (Current phase: {phase})</p>
      </div>
    );
  }

  return (
    <div className="example">
      <h2>Champion Select Monitor</h2>
      <div>
        <h3>Session Info</h3>
        {champSelect && (
          <div>
            <p>Timer Phase: {champSelect.timer.phase}</p>
            <p>Team Size: {champSelect.myTeam.length}</p>
            <p>Local Player Cell: {champSelect.localPlayerCellId}</p>
          </div>
        )}

        <h3>My Selection</h3>
        {mySelection ? (
          <div>
            <p>Champion ID: {mySelection.championId}</p>
            <p>Spell 1: {mySelection.spell1Id}</p>
            <p>Spell 2: {mySelection.spell2Id}</p>
          </div>
        ) : (
          <p>No champion selected yet</p>
        )}
      </div>
    </div>
  );
}

/**
 * Example 4: Manual connection control
 */
export function ManualConnectionExample() {
  const [autoConnect, setAutoConnect] = useState(false);
  const { connect, disconnect, isConnected } = useWebSocket({ autoConnect });

  const connectionStatus = useAppStore((state) => state.connectionStatus);

  return (
    <div className="example">
      <h2>Manual Connection Control</h2>
      <div>
        <p>Status: {connectionStatus}</p>
        <p>Connected: {isConnected() ? "Yes" : "No"}</p>
        
        <div className="controls">
          <button onClick={connect} disabled={isConnected()}>
            Connect
          </button>
          <button onClick={disconnect} disabled={!isConnected()}>
            Disconnect
          </button>
          <button onClick={() => setAutoConnect(!autoConnect)}>
            Toggle Auto-Connect: {autoConnect ? "ON" : "OFF"}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Example 5: Connection status indicator with visual feedback
 */
export function ConnectionIndicatorExample() {
  useWebSocket({ autoConnect: true });

  const connectionStatus = useAppStore((state) => state.connectionStatus);
  const connected = useAppStore((state) => state.connected);

  const getStatusColor = () => {
    switch (connectionStatus) {
      case ConnectionStatus.CONNECTED:
        return "#10b981"; // green
      case ConnectionStatus.CONNECTING:
      case ConnectionStatus.RECONNECTING:
        return "#f59e0b"; // yellow
      case ConnectionStatus.DISCONNECTED:
        return "#ef4444"; // red
      default:
        return "#6b7280"; // gray
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case ConnectionStatus.CONNECTED:
        return "Connected to backend";
      case ConnectionStatus.CONNECTING:
        return "Connecting to backend...";
      case ConnectionStatus.RECONNECTING:
        return "Reconnecting to backend...";
      case ConnectionStatus.DISCONNECTED:
        return "Disconnected from backend";
      default:
        return "Unknown status";
    }
  };

  return (
    <div className="example">
      <h2>Connection Status Indicator</h2>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            width: "16px",
            height: "16px",
            borderRadius: "50%",
            backgroundColor: getStatusColor(),
            transition: "background-color 0.3s ease",
          }}
        />
        <div>
          <p style={{ margin: 0, fontWeight: "bold" }}>{getStatusText()}</p>
          {connected && (
            <p style={{ margin: 0, fontSize: "12px", color: "#6b7280" }}>
              LCU is connected
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Example 6: Real-time state updates with effect
 */
export function StateUpdateExample() {
  const [updateCount, setUpdateCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useWebSocket({ autoConnect: true });

  const phase = useAppStore((state) => state.phase);
  const champSelect = useAppStore((state) => state.champSelect);

  useEffect(() => {
    // Track state updates
    setUpdateCount((prev) => prev + 1);
    setLastUpdate(new Date());
  }, [phase, champSelect]);

  return (
    <div className="example">
      <h2>Real-Time State Updates</h2>
      <div>
        <p>Total Updates: {updateCount}</p>
        <p>Last Update: {lastUpdate?.toLocaleTimeString() || "Never"}</p>
        <p>Current Phase: {phase}</p>
        <p>In Champion Select: {champSelect ? "Yes" : "No"}</p>
      </div>
    </div>
  );
}

/**
 * Example 7: All examples combined
 */
export function AllExamples() {
  return (
    <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
      <h1>WebSocket Service Examples</h1>
      
      <div style={{ display: "grid", gap: "20px", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
        <BasicWebSocketExample />
        <ReconnectionExample />
        <ChampSelectExample />
        <ManualConnectionExample />
        <ConnectionIndicatorExample />
        <StateUpdateExample />
      </div>
    </div>
  );
}
