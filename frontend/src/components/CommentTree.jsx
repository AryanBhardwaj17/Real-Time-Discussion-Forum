import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Heart, MessageCircle, ChevronDown, ChevronUp, Trash2, Reply, Pencil, X, Check, Flag } from 'lucide-react';
import { commentsAPI } from '../lib/api';
import { MAX_COMMENT_DEPTH, PAGINATION, ROLES } from '../lib/constants';
import { timeAgo, formatNumber } from '../lib/utils';
import useAuth from '../hooks/useAuth';
import Avatar from './ui/Avatar';
import Button from './ui/Button';
import MentionText from './MentionText';
import ReportModal from './ReportModal';

export default function CommentTree({ comment, threadId, depth = 0, onReplyAdded, highlightId, wsEvent }) {
  const { user } = useAuth();
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(comment.like_count);

  useEffect(() => {
    if (!user) return;
    commentsAPI.likeStatus(comment.id)
      .then(({ data }) => setLiked(data.liked))
      .catch(() => {});
  }, [user, comment.id]);
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [posting, setPosting] = useState(false);
  const [replies, setReplies] = useState([]);
  const [showReplies, setShowReplies] = useState(false);
  const [loadingReplies, setLoadingReplies] = useState(false);
  const [replyCursor, setReplyCursor] = useState(null);
  const [hasMoreReplies, setHasMoreReplies] = useState(false);
  const [deleted, setDeleted] = useState(comment.is_deleted);
  const [editingComment, setEditingComment] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const [currentContent, setCurrentContent] = useState(comment.content);
  const [isEdited, setIsEdited] = useState(comment.is_edited || false);
  const [editedAt, setEditedAt] = useState(comment.edited_at);
  const [showReportModal, setShowReportModal] = useState(false);
  const [replyCount, setReplyCount] = useState(comment.reply_count);

  // Handle WS events for nested replies
  useEffect(() => {
    if (!wsEvent) return;
    const { type, data } = wsEvent;

    switch (type) {
      case 'new_comment': {
        if (data.parent_id === comment.id) {
          setReplies((prev) => {
            if (prev.some((r) => r.id === data.id)) return prev;
            return [data, ...prev];
          });
          setReplyCount((c) => c + 1);
        }
        break;
      }
      case 'comment_edited': {
        setReplies((prev) =>
          prev.map((r) =>
            r.id === data.id
              ? { ...r, content: data.content, is_edited: true, edited_at: data.edited_at }
              : r
          )
        );
        break;
      }
      case 'comment_deleted': {
        setReplies((prev) =>
          prev.map((r) =>
            r.id === data.comment_id
              ? { ...r, is_deleted: true, content: '[deleted]' }
              : r
          )
        );
        break;
      }
      case 'comment_like_update': {
        if (data.comment_id === comment.id) {
          setLikeCount(data.like_count);
        }
        setReplies((prev) =>
          prev.map((r) =>
            r.id === data.comment_id ? { ...r, like_count: data.like_count } : r
          )
        );
        break;
      }
    }
  }, [wsEvent, comment.id]);

  // Sync with parent prop changes (e.g. real-time WS updates)
  useEffect(() => {
    setDeleted(comment.is_deleted);
  }, [comment.is_deleted]);

  useEffect(() => {
    setCurrentContent(comment.content);
  }, [comment.content]);

  useEffect(() => {
    setIsEdited(comment.is_edited || false);
    setEditedAt(comment.edited_at);
  }, [comment.is_edited, comment.edited_at]);

  const handleLike = async () => {
    if (!user) return;
    try {
      const { data } = await commentsAPI.toggleLike(comment.id);
      setLiked(data.liked);
      setLikeCount(data.like_count);
    } catch { /* ignore */ }
  };

  const handleReply = async (e) => {
    e.preventDefault();
    if (!replyContent.trim()) return;
    setPosting(true);
    try {
      const { data } = await commentsAPI.create(threadId, {
        content: replyContent,
        parent_id: comment.id,
      });
      setReplies((prev) => [data, ...prev]);
      setReplyCount((c) => c + 1);
      setReplyContent('');
      setShowReplyForm(false);
      setShowReplies(true);
      onReplyAdded?.(data);
    } catch { /* ignore */ } finally {
      setPosting(false);
    }
  };

  const loadReplies = async () => {
    if (showReplies && replies.length > 0) {
      setShowReplies(false);
      return;
    }
    setLoadingReplies(true);
    try {
      const { data } = await commentsAPI.replies(comment.id, { limit: PAGINATION.REPLIES_PER_PAGE });
      setReplies(data.items);
      setReplyCursor(data.next_cursor);
      setHasMoreReplies(data.has_more);
      setShowReplies(true);
    } catch { /* ignore */ } finally {
      setLoadingReplies(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this comment?')) return;
    try {
      await commentsAPI.delete(comment.id);
      setDeleted(true);
    } catch { /* ignore */ }
  };

  const startEditingComment = () => {
    setEditContent(currentContent);
    setEditingComment(true);
  };

  const handleSaveComment = async () => {
    if (!editContent.trim()) return;
    setSavingEdit(true);
    try {
      const { data } = await commentsAPI.update(comment.id, { content: editContent });
      setCurrentContent(data.content);
      setIsEdited(true);
      setEditedAt(data.edited_at);
      setEditingComment(false);
    } catch { /* ignore */ } finally {
      setSavingEdit(false);
    }
  };

  const isAuthor = user?.id === comment.author_id;
  const isMod = user?.role === ROLES.MODERATOR || user?.role === ROLES.ADMIN;
  const isHighlighted = highlightId === comment.id;
  return (
    <div id={`comment-${comment.id}`} className={`${depth > 0 ? 'ml-6 pl-4 border-l-2 border-border' : ''}`}>
      <div className={`bg-surface border rounded-lg p-3 transition-all duration-1000 ${isHighlighted ? 'border-primary-400 ring-2 ring-primary-200 bg-primary-50' : 'border-border'}`}>
        {/* Author */}
        <div className="flex items-center gap-2 mb-2">
          {comment.author_username ? (
            <>
              <Link to={`/u/${comment.author_username}`}>
                <Avatar username={comment.author_username} size="sm" />
              </Link>
              <Link to={`/u/${comment.author_username}`} className="text-sm font-medium hover:text-primary-600 hover:underline transition">
                {comment.author_username}
              </Link>
            </>
          ) : (
            <span className="text-sm text-text-muted italic">[unknown]</span>
          )}
          <span className="text-xs text-text-muted">
            {timeAgo(comment.created_at)}
            {isEdited && (
              <span className="ml-1" title={editedAt ? new Date(editedAt).toLocaleString() : ''}>(edited)</span>
            )}
          </span>
        </div>

        {/* Body */}
        {editingComment ? (
          <div className="mt-2 space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-alt text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-300 transition resize-y"
            />
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" size="sm" type="button" onClick={() => setEditingComment(false)} disabled={savingEdit}>
                <X size={12} className="mr-1" /> Cancel
              </Button>
              <Button size="sm" onClick={handleSaveComment} disabled={savingEdit || !editContent.trim()}>
                <Check size={12} className="mr-1" /> {savingEdit ? 'Saving…' : 'Save'}
              </Button>
            </div>
          </div>
        ) : (
          <p className={`text-sm whitespace-pre-wrap ${deleted ? 'text-text-muted italic' : ''}`}>
            {deleted ? '[deleted]' : <MentionText text={currentContent} />}
          </p>
        )}

        {/* Actions */}
        {!deleted && (
          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={handleLike}
              disabled={!user}
              className={`flex items-center gap-0.5 text-xs px-2 py-1 rounded transition ${
                liked ? 'text-danger bg-red-50' : 'text-text-muted hover:text-text hover:bg-surface-hover'
              }`}
            >
              <Heart size={12} fill={liked ? 'currentColor' : 'none'} /> {formatNumber(likeCount)}
            </button>

            {user && depth < MAX_COMMENT_DEPTH && (
              <button
                onClick={() => setShowReplyForm(!showReplyForm)}
                className="flex items-center gap-0.5 text-xs text-text-muted hover:text-text px-2 py-1 rounded hover:bg-surface-hover transition"
              >
                <Reply size={12} /> Reply
              </button>
            )}

            {isAuthor && !editingComment && (
              <button
                onClick={startEditingComment}
                className="flex items-center gap-0.5 text-xs text-text-muted hover:text-text px-2 py-1 rounded hover:bg-surface-hover transition"
              >
                <Pencil size={12} />
              </button>
            )}

            {replyCount > 0 && (
              <button
                onClick={loadReplies}
                disabled={loadingReplies}
                className="flex items-center gap-0.5 text-xs text-primary-600 hover:underline px-2 py-1"
              >
                {showReplies ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {replyCount} {replyCount === 1 ? 'reply' : 'replies'}
              </button>
            )}

            {user && !isAuthor && (
              <button
                onClick={() => setShowReportModal(true)}
                className="flex items-center gap-0.5 text-xs text-text-muted hover:text-text px-2 py-1 rounded hover:bg-surface-hover transition"
              >
                <Flag size={12} />
              </button>
            )}

            {(isAuthor || isMod) && (
              <button
                onClick={handleDelete}
                className="ml-auto text-xs text-text-muted hover:text-danger px-2 py-1 rounded hover:bg-surface-hover transition"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>
        )}

        {/* Report modal */}
        {showReportModal && (
          <ReportModal
            onClose={() => setShowReportModal(false)}
            onSubmit={(data) => commentsAPI.report(comment.id, data)}
          />
        )}

        {/* Reply form */}
        {showReplyForm && (
          <form onSubmit={handleReply} className="mt-3">
            <textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply…"
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-alt text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-300 transition resize-y"
            />
            <div className="flex gap-2 justify-end mt-1">
              <Button variant="ghost" size="sm" type="button" onClick={() => setShowReplyForm(false)}>
                Cancel
              </Button>
              <Button size="sm" type="submit" disabled={posting || !replyContent.trim()}>
                {posting ? 'Posting…' : 'Reply'}
              </Button>
            </div>
          </form>
        )}
      </div>

      {/* Nested replies */}
      {showReplies && replies.length > 0 && (
        <div className="mt-2 space-y-2">
          {replies.map((reply) => (
            <CommentTree
              key={reply.id}
              comment={reply}
              threadId={threadId}
              depth={depth + 1}
              onReplyAdded={onReplyAdded}
              highlightId={highlightId}
              wsEvent={wsEvent}
            />
          ))}
          {hasMoreReplies && (
            <button
              className="text-xs text-primary-600 hover:underline ml-6"
              onClick={async () => {
                try {
                  const { data } = await commentsAPI.replies(comment.id, { cursor: replyCursor, limit: PAGINATION.REPLIES_PER_PAGE });
                  setReplies((prev) => [...prev, ...data.items]);
                  setReplyCursor(data.next_cursor);
                  setHasMoreReplies(data.has_more);
                } catch {
                  // Silently fail — user can retry
                }
              }}
            >
              Load more replies
            </button>
          )}
        </div>
      )}
    </div>
  );
}
