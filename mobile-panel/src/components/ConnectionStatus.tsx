// Connection status indicator component

import { useAppStore } from "@/store/useAppStore";
import { ConnectionStatus as Status } from "@services/websocket";

export function ConnectionStatus() {
  const connectionStatus = useAppStore((state) => state.connectionStatus);
  const connected = useAppStore((state) => state.connected);
  const phase = useAppStore((state) => state.phase);

  const getStatusColor = () => {
    switch (connectionStatus) {
      case Status.CONNECTED:
        return "bg-green-500";
      case Status.CONNECTING:
      case Status.RECONNECTING:
        return "bg-yellow-500";
      case Status.DISCONNECTED:
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case Status.CONNECTED:
        return "Connected";
      case Status.CONNECTING:
        return "Connecting...";
      case Status.RECONNECTING:
        return "Reconnecting...";
      case Status.DISCONNECTED:
        return "Disconnected";
      default:
        return "Unknown";
    }
  };

  return (
    <div className="connection-status">
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
        <span className="text-sm font-medium">{getStatusText()}</span>
      </div>
      {connected && (
        <div className="text-xs text-gray-400 mt-1">
          LCU: {connected ? "Connected" : "Disconnected"} | Phase: {phase}
        </div>
      )}
    </div>
  );
}
