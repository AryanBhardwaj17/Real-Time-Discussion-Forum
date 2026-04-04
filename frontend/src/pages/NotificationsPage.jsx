import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificationsAPI } from '../lib/api';
import { PAGINATION } from '../lib/constants';
import { timeAgo } from '../lib/utils';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import MentionText from '../components/MentionText';

export default function NotificationsPage() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async (nextCursor = null) => {
    try {
      const { data } = await notificationsAPI.list({ cursor: nextCursor, limit: PAGINATION.NOTIFICATIONS_PER_PAGE });
      setNotifications((prev) => (nextCursor ? [...prev, ...data.items] : data.items));
      setCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchNotifications(); }, []);

  const markRead = async (id) => {
    await notificationsAPI.markRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
  };

  const markAllRead = async () => {
    try {
      await notificationsAPI.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // Silently fail — polling will sync state
    }
  };

  const handleClick = async (n) => {
    if (!n.is_read) {
      try { await markRead(n.id); } catch { /* ignore */ }
    }
    const threadId = n.thread_id || (n.reference_type === 'thread' ? n.reference_id : null);
    if (threadId) navigate(`/threads/${threadId}`);
  };

  if (loading) {
    return <div className="flex justify-center py-20"><Spinner size={28} /></div>;
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Notifications</h1>
        {notifications.some((n) => !n.is_read) && (
          <Button variant="secondary" size="sm" onClick={markAllRead}>
            Mark all read
          </Button>
        )}
      </div>

      {notifications.length === 0 ? (
        <p className="text-center py-12 text-text-muted">No notifications</p>
      ) : (
        <div className="space-y-1">
          {notifications.map((n) => (
            <div
              key={n.id}
              onClick={() => handleClick(n)}
              className={`px-4 py-3 rounded-lg border transition cursor-pointer ${
                n.is_read
                  ? 'bg-surface border-border hover:bg-surface-hover'
                  : 'bg-primary-50 border-primary-200 hover:bg-primary-100'
              }`}
            >
              <div className="flex justify-between items-start">
                <p className="text-sm"><MentionText text={n.content} /></p>
                {!n.is_read && <span className="w-2 h-2 bg-primary-500 rounded-full shrink-0 mt-1"></span>}
              </div>
              <p className="text-xs text-text-muted mt-1">{timeAgo(n.created_at)}</p>
            </div>
          ))}
        </div>
      )}

      {hasMore && (
        <div className="text-center mt-4">
          <Button variant="secondary" onClick={() => fetchNotifications(cursor)}>
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
