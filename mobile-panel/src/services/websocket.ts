// WebSocket service for real-time state synchronization

import type { AppState } from "@/types";

function getApiBase(): string {
  const envBase = import.meta.env.VITE_API_BASE;
  if (envBase) return envBase;
  return window.location.origin;
}

function toWsUrl(httpBase: string): string {
  const url = new URL(httpBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws";
  url.search = "";
  return url.toString();
}

export interface WebSocketOptions {
  onMessage: (state: AppState) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onReconnecting?: (attempt: number, delay: number) => void;
  initialReconnectDelay?: number;
  maxReconnectDelay?: number;
  reconnectBackoffMultiplier?: number;
}

export enum ConnectionStatus {
  DISCONNECTED = "disconnected",
  CONNECTING = "connecting",
  CONNECTED = "connected",
  RECONNECTING = "reconnecting",
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;
  private options: Required<WebSocketOptions>;
  private reconnectAttempts = 0;
  private currentReconnectDelay: number;
  private status: ConnectionStatus = ConnectionStatus.DISCONNECTED;

  constructor(options: WebSocketOptions) {
    this.options = {
      initialReconnectDelay: 1000,
      maxReconnectDelay: 30000,
      reconnectBackoffMultiplier: 1.5,
      onOpen: () => {},
      onClose: () => {},
      onError: () => {},
      onReconnecting: () => {},
      ...options,
    };
    this.currentReconnectDelay = this.options.initialReconnectDelay;
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.status = this.reconnectAttempts > 0 
      ? ConnectionStatus.RECONNECTING 
      : ConnectionStatus.CONNECTING;

    try {
      this.ws = new WebSocket(toWsUrl(getApiBase()));

      this.ws.onopen = () => {
        this.status = ConnectionStatus.CONNECTED;
        this.reconnectAttempts = 0;
        this.currentReconnectDelay = this.options.initialReconnectDelay;
        this.options.onOpen();
      };

      this.ws.onmessage = (event) => {
        try {
          const state = JSON.parse(event.data) as AppState;
          this.options.onMessage(state);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      this.ws.onclose = () => {
        this.status = ConnectionStatus.DISCONNECTED;
        this.options.onClose();
        this.ws = null;
        
        if (!this.closed) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.options.onError(error);
      };
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      this.status = ConnectionStatus.DISCONNECTED;
      if (!this.closed) {
        this.scheduleReconnect();
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.currentReconnectDelay,
      this.options.maxReconnectDelay
    );

    this.options.onReconnecting(this.reconnectAttempts, delay);

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);

    // Exponential backoff
    this.currentReconnectDelay = Math.min(
      this.currentReconnectDelay * this.options.reconnectBackoffMultiplier,
      this.options.maxReconnectDelay
    );
  }

  disconnect(): void {
    this.closed = true;
    this.status = ConnectionStatus.DISCONNECTED;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn("Cannot send message: WebSocket is not connected");
    }
  }

  isConnected(): boolean {
    return this.status === ConnectionStatus.CONNECTED;
  }
}
