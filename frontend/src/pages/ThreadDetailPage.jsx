import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';
import { Heart, MessageCircle, Pin, Lock, Trash2, ArrowLeft, Wifi, Pencil, X, Check, Flag } from 'lucide-react';
import { threadsAPI, commentsAPI } from '../lib/api';
import { PAGINATION, ROLES, SORT_OPTIONS, WS_EVENTS } from '../lib/constants';
import { timeAgo, formatNumber, getErrorMessage } from '../lib/utils';
import useAuth from '../hooks/useAuth';
import useWebSocket from '../hooks/useWebSocket';
import Avatar from '../components/ui/Avatar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import CommentTree from '../components/CommentTree';
import MentionText from '../components/MentionText';
import ReportModal from '../components/ReportModal';

export default function ThreadDetailPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get('highlight');
  const navigate = useNavigate();
  const { user } = useAuth();
  const [thread, setThread] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentCursor, setCommentCursor] = useState(null);
  const [hasMoreComments, setHasMoreComments] = useState(false);
  const [loading, setLoading] = useState(true);
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [newComment, setNewComment] = useState('');
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editTags, setEditTags] = useState('');
  const [saving, setSaving] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [wsEvent, setWsEvent] = useState(null);
  const wsSeq = useRef(0);

  // ── WebSocket: real-time thread updates ──────────────────────
  const broadcastToReplies = useCallback((msg) => {
    wsSeq.current += 1;
    setWsEvent({ ...msg, _seq: wsSeq.current });
  }, []);

  const handleWsMessage = useCallback((msg) => {
    switch (msg.type) {
      case WS_EVENTS.NEW_COMMENT: {
        const data = msg.data;
        // Skip comments posted by the current user (already added optimistically)
        if (user && data.author_id === user.id) break;
        if (data.parent_id === null) {
          setComments((prev) => {
            if (prev.some((c) => c.id === data.id)) return prev;
            return [data, ...prev];
          });
        } else {
          broadcastToReplies(msg);
        }
        setThread((t) => t ? { ...t, comment_count: t.comment_count + 1 } : t);
        break;
      }
      case WS_EVENTS.COMMENT_EDITED: {
        const data = msg.data;
        setComments((prev) =>
          prev.map((c) =>
            c.id === data.id
              ? { ...c, content: data.content, is_edited: true, edited_at: data.edited_at }
              : c
          )
        );
        broadcastToReplies(msg);
        break;
      }
      case WS_EVENTS.COMMENT_DELETED: {
        const data = msg.data;
        setComments((prev) =>
          prev.map((c) =>
            c.id === data.comment_id
              ? { ...c, is_deleted: true, content: '[deleted]' }
              : c
          )
        );
        setThread((t) => t ? { ...t, comment_count: Math.max(0, t.comment_count - 1) } : t);
        broadcastToReplies(msg);
        break;
      }
      case WS_EVENTS.LIKE_UPDATE: {
        setLikeCount(msg.data.like_count);
        break;
      }
      case WS_EVENTS.COMMENT_LIKE_UPDATE: {
        setComments((prev) =>
          prev.map((c) =>
            c.id === msg.data.comment_id ? { ...c, like_count: msg.data.like_count } : c
          )
        );
        broadcastToReplies(msg);
        break;
      }
      case WS_EVENTS.THREAD_UPDATED: {
        const data = msg.data;
        setThread((t) => t ? {
          ...t,
          title: data.title,
          description: data.description,
          tags: data.tags,
          is_edited: true,
          edited_at: data.edited_at,
        } : t);
        break;
      }
      case WS_EVENTS.THREAD_DELETED: {
        navigate('/');
        break;
      }
      case WS_EVENTS.THREAD_PINNED: {
        setThread((t) => t ? { ...t, is_pinned: msg.data.is_pinned } : t);
        break;
      }
      case WS_EVENTS.THREAD_LOCKED: {
        setThread((t) => t ? { ...t, is_locked: msg.data.is_locked } : t);
        break;
      }
    }
  }, [user, broadcastToReplies, navigate]);

  const { connected } = useWebSocket(`threads/${id}`, {
    onMessage: handleWsMessage,
    enabled: !loading,
  });

  useEffect(() => {
    const load = async () => {
      try {
        const [threadRes, commentsRes] = await Promise.all([
          threadsAPI.get(id),
          commentsAPI.list(id, { sort: SORT_OPTIONS.NEW, limit: PAGINATION.COMMENTS_PER_PAGE }),
        ]);
        setThread(threadRes.data);
        setLikeCount(threadRes.data.like_count);
        setComments(commentsRes.data.items);
        setCommentCursor(commentsRes.data.next_cursor);
        setHasMoreComments(commentsRes.data.has_more);
      } catch {
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, navigate]);

  // Scroll to highlighted comment (from report dashboard link)
  useEffect(() => {
    if (!highlightId || loading) return;
    const timer = setTimeout(() => {
      const el = document.getElementById(`comment-${highlightId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [highlightId, loading]);

  // Fetch like status when user becomes available (separate effect to avoid race condition)
  useEffect(() => {
    if (!user || !id) return;
    threadsAPI.likeStatus(id)
      .then(({ data }) => setLiked(data.liked))
      .catch(() => {});
  }, [user, id]);

  const handleLike = async () => {
    if (!user) return navigate('/login');
    try {
      const { data } = await threadsAPI.toggleLike(id);
      setLiked(data.liked);
      setLikeCount(data.like_count);
    } catch { /* ignore */ }
  };

  const handlePostComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    setPosting(true);
    setError('');
    try {
      const { data } = await commentsAPI.create(id, { content: newComment });
      setComments((prev) => [data, ...prev]);
      setNewComment('');
      setThread((t) => ({ ...t, comment_count: t.comment_count + 1 }));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setPosting(false);
    }
  };

  const handleDeleteThread = async () => {
    if (!window.confirm('Delete this thread?')) return;
    try {
      await threadsAPI.delete(id);
      navigate('/');
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handlePin = async () => {
    try {
      const { data } = await threadsAPI.togglePin(id);
      setThread(data);
    } catch { /* ignore */ }
  };

  const handleLock = async () => {
    try {
      const { data } = await threadsAPI.toggleLock(id);
      setThread(data);
    } catch { /* ignore */ }
  };

  const startEditing = () => {
    setEditTitle(thread.title);
    setEditDescription(thread.description);
    setEditTags(thread.tags?.join(', ') || '');
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setError('');
  };

  const handleSaveEdit = async () => {
    setSaving(true);
    setError('');
    try {
      const payload = { title: editTitle, description: editDescription };
      const tags = editTags.split(',').map((t) => t.trim()).filter(Boolean);
      if (tags.length > 0) payload.tags = tags;
      else payload.tags = [];
      const { data } = await threadsAPI.update(id, payload);
      setThread(data);
      setEditing(false);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size={28} />
      </div>
    );
  }

  if (!thread) return null;

  const isAuthor = user?.id === thread.author_id;
  const isMod = user?.role === ROLES.MODERATOR || user?.role === ROLES.ADMIN;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-text-secondary hover:text-text transition">
          <ArrowLeft size={16} /> Back
        </button>
        {connected && (
          <span className="flex items-center gap-1 text-xs text-success">
            <Wifi size={12} /> Live
          </span>
        )}
      </div>

      {/* Thread */}
      <article className="bg-surface border border-border rounded-xl p-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Link to={`/u/${thread.author_username}`}>
              <Avatar username={thread.author_username} size="lg" />
            </Link>
            <div>
              <Link to={`/u/${thread.author_username}`} className="font-medium text-sm hover:text-primary-600 hover:underline transition">
                {thread.author_username}
              </Link>
              <p className="text-xs text-text-muted">
                {timeAgo(thread.created_at)}
                {thread.is_edited && (
                  <span className="ml-1 text-text-muted" title={thread.edited_at ? new Date(thread.edited_at).toLocaleString() : ''}>
                    (edited)
                  </span>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {thread.is_pinned && <Badge variant="primary"><Pin size={10} className="mr-0.5" /> Pinned</Badge>}
            {thread.is_locked && <Badge variant="warning"><Lock size={10} className="mr-0.5" /> Locked</Badge>}
          </div>
        </div>

        {/* Title + body */}
        {editing ? (
          <div className="mt-4 space-y-3">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Title</label>
              <input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-text focus:outline-none focus:ring-2 focus:ring-primary-300 transition text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Description</label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-text focus:outline-none focus:ring-2 focus:ring-primary-300 transition resize-y text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Tags (comma separated)</label>
              <input
                value={editTags}
                onChange={(e) => setEditTags(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-text focus:outline-none focus:ring-2 focus:ring-primary-300 transition text-sm"
                placeholder="tag1, tag2, tag3"
              />
            </div>
            {error && (
              <div className="px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">{error}</div>
            )}
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" size="sm" onClick={cancelEditing} disabled={saving}>
                <X size={14} className="mr-1" /> Cancel
              </Button>
              <Button size="sm" onClick={handleSaveEdit} disabled={saving || !editTitle.trim() || !editDescription.trim()}>
                <Check size={14} className="mr-1" /> {saving ? 'Saving…' : 'Save'}
              </Button>
            </div>
          </div>
        ) : (
          <>
            <h1 className="text-xl font-bold mt-4">{thread.title}</h1>
            <div className="mt-3 text-text-secondary whitespace-pre-wrap leading-relaxed">
              <MentionText text={thread.description} />
            </div>
          </>
        )}

        {/* Tags */}
        {thread.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-4">
            {thread.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 mt-5 pt-4 border-t border-border">
          <button
            onClick={handleLike}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition ${
              liked ? 'bg-red-50 text-danger' : 'hover:bg-surface-hover text-text-secondary'
            }`}
          >
            <Heart size={16} fill={liked ? 'currentColor' : 'none'} /> {formatNumber(likeCount)}
          </button>
          <span className="flex items-center gap-1 text-sm text-text-muted">
            <MessageCircle size={16} /> {formatNumber(thread.comment_count)}
          </span>

          <div className="ml-auto flex gap-1">
            {user && !isAuthor && (
              <Button variant="ghost" size="sm" onClick={() => setShowReportModal(true)}>
                <Flag size={14} className="text-text-muted" />
              </Button>
            )}
            {isAuthor && !editing && (
              <Button variant="ghost" size="sm" onClick={startEditing}>
                <Pencil size={14} />
              </Button>
            )}
            {isMod && (
              <>
                <Button variant="ghost" size="sm" onClick={handlePin}>{thread.is_pinned ? 'Unpin' : 'Pin'}</Button>
                <Button variant="ghost" size="sm" onClick={handleLock}>{thread.is_locked ? 'Unlock' : 'Lock'}</Button>
              </>
            )}
            {(isAuthor || isMod) && (
              <Button variant="ghost" size="sm" onClick={handleDeleteThread}>
                <Trash2 size={14} className="text-danger" />
              </Button>
            )}
          </div>
        </div>
      </article>

      {/* Report modal */}
      {showReportModal && (
        <ReportModal
          onClose={() => setShowReportModal(false)}
          onSubmit={(data) => threadsAPI.report(id, data)}
        />
      )}

      {/* Comment form */}
      {user && !thread.is_locked && (
        <form onSubmit={handlePostComment} className="mt-4 bg-surface border border-border rounded-xl p-4">
          {error && (
            <div className="mb-3 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">
              {error}
            </div>
          )}
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Write a comment…"
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-300 transition resize-y text-sm"
          />
          <div className="flex justify-end mt-2">
            <Button size="sm" type="submit" disabled={posting || !newComment.trim()}>
              {posting ? 'Posting…' : 'Comment'}
            </Button>
          </div>
        </form>
      )}

      {thread.is_locked && (
        <div className="mt-4 text-center py-4 text-sm text-text-muted bg-surface border border-border rounded-xl">
          <Lock size={16} className="inline mr-1" /> This thread is locked. No new comments.
        </div>
      )}

      {/* Comments */}
      <div className="mt-4 space-y-2">
        {comments.length === 0 ? (
          <p className="text-center py-8 text-text-muted text-sm">No comments yet. Be the first!</p>
        ) : (
          comments.map((comment) => (
            <CommentTree
              key={comment.id}
              comment={comment}
              threadId={id}
              highlightId={highlightId}
              wsEvent={wsEvent}
              onReplyAdded={(reply) => {
                setComments((prev) => prev.map((c) =>
                  c.id === reply.parent_id ? { ...c, reply_count: c.reply_count + 1 } : c
                ));
              }}
            />
          ))
        )}
        {hasMoreComments && (
          <div className="text-center">
            <Button
              variant="secondary"
              size="sm"
              onClick={async () => {
                try {
                  const { data } = await commentsAPI.list(id, { sort: SORT_OPTIONS.NEW, cursor: commentCursor, limit: PAGINATION.COMMENTS_PER_PAGE });
                  setComments((prev) => [...prev, ...data.items]);
                  setCommentCursor(data.next_cursor);
                  setHasMoreComments(data.has_more);
                } catch (err) {
                  setError(getErrorMessage(err));
                }
              }}
            >
              Load more comments
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
