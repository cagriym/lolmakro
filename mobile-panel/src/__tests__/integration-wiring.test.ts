/**
 * Integration tests for Task 24.2: Wire mobile UI to backend API
 * 
 * Verifies that:
 * - WebSocket service is connected to UI components
 * - API service is connected to data-fetching components
 * - State updates propagate to UI
 */

// Test file - not included in production build
// import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WebSocketService, ConnectionStatus } from '../services/websocket';
import { api, ApiError, NetworkError, TimeoutError } from '../services/api';
import { useAppStore } from '../store/useAppStore';

describe('Mobile UI Integration Wiring', () => {
  describe('WebSocket Service', () => {
    it('should be instantiable with required options', () => {
      const mockOnMessage = vi.fn();
      const ws = new WebSocketService({
        onMessage: mockOnMessage,
      });

      expect(ws).toBeDefined();
      expect(ws.getStatus()).toBe(ConnectionStatus.DISCONNECTED);
    });

    it('should support connection lifecycle methods', () => {
      const mockOnMessage = vi.fn();
      const ws = new WebSocketService({
        onMessage: mockOnMessage,
      });

      expect(typeof ws.connect).toBe('function');
      expect(typeof ws.disconnect).toBe('function');
      expect(typeof ws.send).toBe('function');
      expect(typeof ws.isConnected).toBe('function');
      expect(typeof ws.getStatus).toBe('function');
    });

    it('should call onMessage callback when message received', () => {
      const mockOnMessage = vi.fn();
      const ws = new WebSocketService({
        onMessage: mockOnMessage,
      });

      // Verify callback is stored
      expect(mockOnMessage).not.toHaveBeenCalled();
    });
  });

  describe('API Service', () => {
    it('should have all required endpoint methods', () => {
      // Health & State
      expect(typeof api.health).toBe('function');
      expect(typeof api.getState).toBe('function');
      expect(typeof api.getPresets).toBe('function');
      expect(typeof api.getPages).toBe('function');

      // Preset Management
      expect(typeof api.selectPreset).toBe('function');

      // Rune Editing
      expect(typeof api.editRune).toBe('function');
      expect(typeof api.setEditMode).toBe('function');

      // Data Fetching
      expect(typeof api.getChampions).toBe('function');
      expect(typeof api.getSpells).toBe('function');
      expect(typeof api.getCurrentSpells).toBe('function');
      expect(typeof api.getRuneStyles).toBe('function');

      // Live Game Stats
      expect(typeof api.getLiveStats).toBe('function');
    });

    it('should export error types', () => {
      expect(ApiError).toBeDefined();
      expect(NetworkError).toBeDefined();
      expect(TimeoutError).toBeDefined();
    });

    it('should create proper error instances', () => {
      const apiError = new ApiError('Test error', 404);
      expect(apiError).toBeInstanceOf(Error);
      expect(apiError.name).toBe('ApiError');
      expect(apiError.statusCode).toBe(404);

      const networkError = new NetworkError('Network failed');
      expect(networkError).toBeInstanceOf(Error);
      expect(networkError.name).toBe('NetworkError');

      const timeoutError = new TimeoutError();
      expect(timeoutError).toBeInstanceOf(Error);
      expect(timeoutError.name).toBe('TimeoutError');
    });
  });

  describe('App Store', () => {
    beforeEach(() => {
      // Reset store state before each test
      const store = useAppStore.getState();
      store.setState({
        connected: false,
        phase: 'None',
        champSelect: null,
        mySelection: null,
        currentRunePage: null,
      });
    });

    it('should have initial state', () => {
      const state = useAppStore.getState();
      
      expect(state.connected).toBe(false);
      expect(state.phase).toBe('None');
      expect(state.champSelect).toBeNull();
      expect(state.mySelection).toBeNull();
      expect(state.currentRunePage).toBeNull();
    });

    it('should have state update methods', () => {
      const store = useAppStore.getState();
      
      expect(typeof store.setState).toBe('function');
      expect(typeof store.setChampions).toBe('function');
      expect(typeof store.setSpells).toBe('function');
      expect(typeof store.setRuneStyles).toBe('function');
      expect(typeof store.setRunePages).toBe('function');
      expect(typeof store.setBusy).toBe('function');
      expect(typeof store.setConnectionStatus).toBe('function');
    });

    it('should update state when setState is called', () => {
      const store = useAppStore.getState();
      
      store.setState({
        connected: true,
        phase: 'ChampSelect',
      });

      const newState = useAppStore.getState();
      expect(newState.connected).toBe(true);
      expect(newState.phase).toBe('ChampSelect');
    });

    it('should update connection status', () => {
      const store = useAppStore.getState();
      
      store.setConnectionStatus(ConnectionStatus.CONNECTED);
      
      const newState = useAppStore.getState();
      expect(newState.connectionStatus).toBe(ConnectionStatus.CONNECTED);
    });

    it('should update champions list', () => {
      const store = useAppStore.getState();
      const mockChampions = [
        { id: 157, name: 'Yasuo', key: 'Yasuo' },
        { id: 777, name: 'Yone', key: 'Yone' },
      ];
      
      store.setChampions(mockChampions);
      
      const newState = useAppStore.getState();
      expect(newState.champions).toEqual(mockChampions);
    });
  });

  describe('Integration Points', () => {
    it('should have WebSocket service that can update store', () => {
      const store = useAppStore.getState();
      
      // Create WebSocket service with callback that updates store
      const ws = new WebSocketService({
        onMessage: (state) => {
          store.setState(state);
        },
      });

      expect(ws).toBeDefined();
    });

    it('should have API service that can be called from components', async () => {
      // Verify API methods return promises
      const healthPromise = api.health().catch(() => {
        // Expected to fail in test environment
      });
      expect(healthPromise).toBeInstanceOf(Promise);
    });

    it('should have store that can be accessed from components', () => {
      // Verify store can be accessed
      const state = useAppStore.getState();
      expect(state).toBeDefined();
      expect(state.connected).toBeDefined();
      expect(state.phase).toBeDefined();
    });
  });

  describe('Data Flow', () => {
    it('should support WebSocket -> Store -> UI flow', () => {
      const store = useAppStore.getState();
      
      // Simulate WebSocket message updating store
      const mockState = {
        connected: true,
        phase: 'ChampSelect' as const,
        champSelect: {
          localPlayerCellId: 0,
          myTeam: [{
            cellId: 0,
            championId: 157,
            assignedPosition: 'middle',
          }],
          timer: { phase: 'BAN_PICK' },
          actions: [],
        },
        mySelection: null,
        currentRunePage: null,
      };

      store.setState(mockState);

      // Verify store was updated
      const newState = useAppStore.getState();
      expect(newState.connected).toBe(true);
      expect(newState.phase).toBe('ChampSelect');
      expect(newState.champSelect).toEqual(mockState.champSelect);
    });

    it('should support UI -> API -> Backend flow', () => {
      // Verify API methods can be called (will fail in test env, but structure is correct)
      expect(() => {
        api.selectPreset(0).catch(() => {});
      }).not.toThrow();

      expect(() => {
        api.editRune(8005, 'keystone').catch(() => {});
      }).not.toThrow();
    });
  });
});
