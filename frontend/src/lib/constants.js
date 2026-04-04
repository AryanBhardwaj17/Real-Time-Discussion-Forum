export const ROLES = {
  ADMIN: 'admin',
  MODERATOR: 'moderator',
  MEMBER: 'member',
};

export const SORT_OPTIONS = {
  HOT: 'hot',
  NEW: 'new',
  TOP: 'top',
};

export const PAGINATION = {
  THREADS_PER_PAGE: 20,
  COMMENTS_PER_PAGE: 50,
  REPLIES_PER_PAGE: 20,
  NOTIFICATIONS_PER_PAGE: 30,
};

export const MAX_COMMENT_DEPTH = 4;

export const POLL_INTERVALS = {
  NOTIFICATIONS: 30_000,
  NOTIFICATIONS_WS_FALLBACK: 60_000,
};

export const WS_EVENTS = {
  NEW_COMMENT: 'new_comment',
  COMMENT_EDITED: 'comment_edited',
  COMMENT_DELETED: 'comment_deleted',
  LIKE_UPDATE: 'like_update',
  COMMENT_LIKE_UPDATE: 'comment_like_update',
  NEW_THREAD: 'new_thread',
  THREAD_UPDATED: 'thread_updated',
  THREAD_DELETED: 'thread_deleted',
  THREAD_PINNED: 'thread_pinned',
  THREAD_LOCKED: 'thread_locked',
  NOTIFICATION: 'notification',
  NOTIFICATION_RETRACTED: 'notification_retracted',
  FORCE_LOGOUT: 'force_logout',
  ROLE_CHANGED: 'role_changed',
};
