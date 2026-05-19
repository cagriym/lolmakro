// Custom hook for WebSocket connection management

import { useEffect, useRef } from "react";
import { WebSocketService, ConnectionStatus } from "@services/websocket";
import { useAppStore } from "@/store/useAppStore";

export interface UseWebSocketOptions {
  autoConnect?: boolean;
  onReconnecting?: (attempt: number, delay: number) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { autoConnect = true, onReconnecting } = options;
  const wsServiceRef = useRef<WebSocketService | null>(null);
  const setState = useAppStore((state) => state.setState);
  const setConnectionStatus = useAppStore((state) => state.setConnectionStatus);

  useEffect(() => {
    if (!autoConnect) {
      return;
    }

    const wsService = new WebSocketService({
      onMessage: (newState) => {
        // Update Zustand store with new state from backend
        setState({
          connected: newState.connected,
          phase: newState.phase,
          champSelect: newState.champSelect,
          mySelection: newState.mySelection,
          currentRunePage: newState.currentRunePage,
          isLolWindowActive: newState.isLolWindowActive,
        });
      },
      onOpen: () => {
        console.log("WebSocket connected");
        setConnectionStatus(ConnectionStatus.CONNECTED);
      },
      onClose: () => {
        console.log("WebSocket disconnected");
        setConnectionStatus(ConnectionStatus.DISCONNECTED);
      },
      onError: (error) => {
        console.error("WebSocket error:", error);
        setConnectionStatus(ConnectionStatus.DISCONNECTED);
      },
      onReconnecting: (attempt, delay) => {
        console.log(`WebSocket reconnecting (attempt ${attempt}, delay ${delay}ms)`);
        setConnectionStatus(ConnectionStatus.RECONNECTING);
        onReconnecting?.(attempt, delay);
      },
    });

    wsServiceRef.current = wsService;
    wsService.connect();

    return () => {
      wsService.disconnect();
      wsServiceRef.current = null;
    };
  }, [autoConnect, setState, setConnectionStatus, onReconnecting]);

  return {
    wsService: wsServiceRef.current,
    connect: () => wsServiceRef.current?.connect(),
    disconnect: () => wsServiceRef.current?.disconnect(),
    send: (data: any) => wsServiceRef.current?.send(data),
    isConnected: () => wsServiceRef.current?.isConnected() ?? false,
  };
}
