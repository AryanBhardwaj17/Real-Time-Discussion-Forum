import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Flame, Clock, TrendingUp, MessageCircle, Heart, Pin } from 'lucide-react';
import { threadsAPI } from '../lib/api';
import { SORT_OPTIONS, PAGINATION, WS_EVENTS } from '../lib/constants';
import { timeAgo, truncate, formatNumber } from '../lib/utils';
import useAuth from '../hooks/useAuth';
import useWebSocket from '../hooks/useWebSocket';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import Avatar from '../components/ui/Avatar';

const SORT_TABS = [
  { key: SORT_OPTIONS.HOT, label: 'Hot', icon: Flame },
  { key: SORT_OPTIONS.NEW, label: 'New', icon: Clock },
  { key: SORT_OPTIONS.TOP, label: 'Top', icon: TrendingUp },
];

export default function HomePage() {
  const { user } = useAuth();
  const [threads, setThreads] = useState([]);
  const [sort, setSort] = useState(SORT_OPTIONS.HOT);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // ── WebSocket: listen for new threads posted by other users ──
  const handleWsMessage = useCallback((msg) => {
    if (msg.type === WS_EVENTS.NEW_THREAD && msg.data) {
      // Skip threads posted by the current user (already navigated away)
      if (user && msg.data.author_id === user.id) return;
      setThreads((prev) => {
        if (prev.some((t) => t.id === msg.data.id)) return prev;
        // Insert after pinned threads so pins stay at the top
        const firstNonPinned = prev.findIndex((t) => !t.is_pinned);
        if (firstNonPinned === -1) return [...prev, msg.data];
        return [...prev.slice(0, firstNonPinned), msg.data, ...prev.slice(firstNonPinned)];
      });
    } else if (msg.type === WS_EVENTS.THREAD_UPDATED && msg.data) {
      setThreads((prev) => prev.map((t) =>
        t.id === msg.data.id
          ? { ...t, title: msg.data.title, description: msg.data.description, tags: msg.data.tags, is_edited: msg.data.is_edited, edited_at: msg.data.edited_at }
          : t
      ));
    } else if (msg.type === WS_EVENTS.THREAD_DELETED && msg.data) {
      setThreads((prev) => prev.filter((t) => t.id !== msg.data.id));
    } else if (msg.type === WS_EVENTS.THREAD_PINNED && msg.data) {
      setThreads((prev) => prev.map((t) =>
        t.id === msg.data.id ? { ...t, is_pinned: msg.data.is_pinned } : t
      ));
    } else if (msg.type === WS_EVENTS.THREAD_LOCKED && msg.data) {
      setThreads((prev) => prev.map((t) =>
        t.id === msg.data.id ? { ...t, is_locked: msg.data.is_locked } : t
      ));
    } else if (msg.type === WS_EVENTS.LIKE_UPDATE && msg.data) {
      setThreads((prev) => prev.map((t) =>
        t.id === msg.data.thread_id ? { ...t, like_count: msg.data.like_count } : t
      ));
    } else if (msg.type === WS_EVENTS.NEW_COMMENT && msg.data?.thread_id) {
      setThreads((prev) => prev.map((t) =>
        t.id === msg.data.thread_id ? { ...t, comment_count: (t.comment_count || 0) + 1 } : t
      ));
    } else if (msg.type === WS_EVENTS.COMMENT_DELETED && msg.data?.thread_id) {
      setThreads((prev) => prev.map((t) =>
        t.id === msg.data.thread_id ? { ...t, comment_count: Math.max(0, (t.comment_count || 0) - 1) } : t
      ));
    }
  }, [user]);

  useWebSocket('feed', {
    onMessage: handleWsMessage,
    enabled: !loading,
  });

  const fetchThreads = async (sortBy, nextCursor = null) => {
    const isLoadMore = nextCursor !== null;
    if (isLoadMore) setLoadingMore(true); else setLoading(true);

    try {
      const { data } = await threadsAPI.list({ sort: sortBy, cursor: nextCursor, limit: PAGINATION.THREADS_PER_PAGE });
      setThreads((prev) => (isLoadMore ? [...prev, ...data.items] : data.items));
      setCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch { /* ignore */ } finally {
      if (isLoadMore) setLoadingMore(false); else setLoading(false);
    }
  };

  useEffect(() => {
    setThreads([]);
    setCursor(null);
    fetchThreads(sort);
  }, [sort]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size={28} />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-1 bg-surface border border-border rounded-lg p-0.5">
          {SORT_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSort(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition ${
                sort === tab.key ? 'bg-primary-600 text-white' : 'text-text-secondary hover:text-text'
              }`}
            >
              <tab.icon size={14} /> {tab.label}
            </button>
          ))}
        </div>

        {user && (
          <Link to="/new">
            <Button size="sm">
              <Plus size={16} className="mr-1" /> New Thread
            </Button>
          </Link>
        )}
      </div>

      {/* Thread list */}
      {threads.length === 0 ? (
        <div className="text-center py-20 text-text-muted">
          <MessageCircle size={40} className="mx-auto mb-3 opacity-50" />
          <p className="text-lg font-medium">No threads yet</p>
          <p className="text-sm">Be the first to start a discussion!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {threads.map((thread) => (
            <ThreadCard key={thread.id} thread={thread} />
          ))}
        </div>
      )}

      {/* Load more */}
      {hasMore && (
        <div className="text-center mt-4">
          <Button variant="secondary" onClick={() => fetchThreads(sort, cursor)} disabled={loadingMore}>
            {loadingMore ? 'Loading…' : 'Load More'}
          </Button>
        </div>
      )}
    </div>
  );
}

function ThreadCard({ thread }) {
  return (
    <Link
      to={`/threads/${thread.id}`}
      className="block bg-surface border border-border rounded-xl p-4 hover:border-primary-200 hover:shadow-sm transition"
    >
      <div className="flex gap-3">
        <Link to={`/u/${thread.author_username}`} onClick={(e) => e.stopPropagation()}>
          <Avatar username={thread.author_username} size="md" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {thread.is_pinned && (
              <Pin size={13} className="text-primary-500 shrink-0" />
            )}
            <h2 className="font-semibold text-text leading-snug">{thread.title}</h2>
          </div>
          <p className="text-sm text-text-secondary mt-1 line-clamp-2">
            {truncate(thread.description, 180)}
          </p>

          {/* Tags */}
          {thread.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {thread.tags.map((tag) => (
                <Badge key={tag}>{tag}</Badge>
              ))}
            </div>
          )}

          {/* Meta */}
          <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
            <Link
              to={`/u/${thread.author_username}`}
              onClick={(e) => e.stopPropagation()}
              className="font-medium text-text-secondary hover:text-primary-600 hover:underline transition"
            >
              {thread.author_username}
            </Link>
            <span>{timeAgo(thread.created_at)}</span>
            <span className="flex items-center gap-0.5">
              <Heart size={12} /> {formatNumber(thread.like_count)}
            </span>
            <span className="flex items-center gap-0.5">
              <MessageCircle size={12} /> {formatNumber(thread.comment_count)}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
