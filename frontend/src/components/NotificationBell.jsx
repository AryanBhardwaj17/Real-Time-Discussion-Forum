import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { notificationsAPI, authAPI } from '../lib/api';
import { POLL_INTERVALS, WS_EVENTS } from '../lib/constants';
import useAuth from '../hooks/useAuth';
import useClickOutside from '../hooks/useClickOutside';
import useWebSocket from '../hooks/useWebSocket';
import { timeAgo } from '../lib/utils';
import MentionText from './MentionText';

export default function NotificationBell() {
  const { user, setUser, fetchUser } = useAuth();
  const navigate = useNavigate();
  const [count, setCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useClickOutside(ref, () => setOpen(false));

  // ── WebSocket: real-time notification push ──────────────────
  const handleWsMessage = useCallback((msg) => {
    if (msg.type === WS_EVENTS.FORCE_LOGOUT) {
      authAPI.logout().catch(() => {});
      setUser(null);
      window.location.href = '/login?deactivated=1';
      return;
    }
    if (msg.type === WS_EVENTS.ROLE_CHANGED) {
      // Refresh token so new JWT carries the updated role, then re-fetch user context
      authAPI.refreshToken()
        .then(() => fetchUser())
        .catch(() => {});
      return;
    }
    if (msg.type === WS_EVENTS.NOTIFICATION) {
      setCount((c) => c + 1);
      setNotifications((prev) => [msg.data, ...prev]);
    }
    if (msg.type === WS_EVENTS.NOTIFICATION_RETRACTED) {
      setCount((c) => Math.max(0, c - 1));
      setNotifications((prev) =>
        prev.filter(
          (n) =>
            !(n.notification_type === msg.data.notification_type &&
              n.reference_id === msg.data.reference_id)
        )
      );
    }
  }, []);

  const { connected } = useWebSocket('notifications', {
    onMessage: handleWsMessage,
    enabled: !!user,
  });

  // Polling fallback — slower interval when WS is connected
  useEffect(() => {
    if (!user) return;
    const poll = () => notificationsAPI.unreadCount().then((r) => setCount(r.data.count)).catch(() => {});
    poll();
    const interval = setInterval(
      poll,
      connected ? POLL_INTERVALS.NOTIFICATIONS_WS_FALLBACK : POLL_INTERVALS.NOTIFICATIONS
    );
    return () => clearInterval(interval);
  }, [user, connected]);

  const handleOpen = async () => {
    if (!open) {
      try {
        const { data } = await notificationsAPI.list({ limit: 10, unread_only: true });
        setNotifications(data.items);
      } catch { /* ignore */ }
    }
    setOpen(!open);
  };

  const markRead = async (id) => {
    await notificationsAPI.markRead(id);
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    setCount((c) => Math.max(0, c - 1));
  };

  const markAllRead = async () => {
    await notificationsAPI.markAllRead();
    setNotifications([]);
    setCount(0);
  };

  const handleNotifClick = async (n) => {
    await markRead(n.id);
    setOpen(false);
    const threadId = n.thread_id || (n.reference_type === 'thread' ? n.reference_id : null);
    if (threadId) navigate(`/threads/${threadId}`);
  };

  return (
    <div className="relative" ref={ref}>
      <button onClick={handleOpen} className="relative p-2 rounded-lg hover:bg-surface-hover transition">
        <Bell size={18} className="text-text-secondary" />
        {count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-danger text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-80 bg-surface border border-border rounded-lg shadow-lg">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <span className="text-sm font-semibold">Notifications</span>
            {notifications.length > 0 && (
              <button onClick={markAllRead} className="text-xs text-primary-600 hover:underline">
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-3 py-6 text-sm text-text-muted text-center">No unread notifications</p>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleNotifClick(n)}
                  className="px-3 py-2 hover:bg-surface-hover cursor-pointer border-b border-border last:border-0"
                >
                  <p className="text-sm"><MentionText text={n.content} /></p>
                  <p className="text-xs text-text-muted mt-0.5">{timeAgo(n.created_at)}</p>
                </div>
              ))
            )}
          </div>
          <Link
            to="/notifications"
            onClick={() => setOpen(false)}
            className="block text-center text-xs text-primary-600 py-2 border-t border-border hover:underline"
          >
            View all
          </Link>
        </div>
      )}
    </div>
  );
}
