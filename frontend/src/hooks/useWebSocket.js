import { useEffect, useRef, useState, useCallback } from 'react';

const MAX_RECONNECT_DELAY = 30000;
const INITIAL_RECONNECT_DELAY = 1000;

/**
 * Reusable WebSocket hook with auto-reconnect.
 *
 * Auth is handled transparently: the gateway reads the HttpOnly access_token
 * cookie and injects an auth handshake message into the backend WS connection.
 * The frontend doesn't need to know about tokens at all.
 *
 * @param {string} path  - WebSocket path (e.g. "threads/abc-123" or "notifications")
 * @param {object} opts
 * @param {function} opts.onMessage - callback for incoming messages (parsed JSON)
 * @param {boolean}  opts.enabled   - whether the connection should be active (default true)
 * @returns {{ connected: boolean }}
 */
export default function useWebSocket(path, { onMessage, enabled = true } = {}) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const reconnectDelay = useRef(INITIAL_RECONNECT_DELAY);
  const onMessageRef = useRef(onMessage);
  const connectRef = useRef(null);

  // Keep callback ref up to date without triggering reconnects
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/${path}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectDelay.current = INITIAL_RECONNECT_DELAY;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Filter out heartbeat pings from the backend
        if (data.type === 'ping') return;
        onMessageRef.current?.(data);
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      // Schedule reconnect with exponential backoff
      reconnectTimer.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, MAX_RECONNECT_DELAY);
        connectRef.current?.();
      }, reconnectDelay.current);
    };

    ws.onerror = () => {
      // onclose will fire after onerror, triggering reconnect
      ws.close();
    };
  }, [path]);

  // Keep connectRef in sync so the onclose handler can call it
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    if (!enabled) {
      // Clean up if disabled
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect
        wsRef.current.close();
        wsRef.current = null;
      }
      clearTimeout(reconnectTimer.current);
      return;
    }

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close();
        wsRef.current = null;
      }
      clearTimeout(reconnectTimer.current);
    };
  }, [enabled, connect]);

  return { connected };
}
