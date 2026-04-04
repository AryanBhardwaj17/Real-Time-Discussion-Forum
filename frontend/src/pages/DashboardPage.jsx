import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { MessageSquare, MessageCircle, Heart, TrendingUp, Eye, Shield, Users, UserX, UserCheck, Flag, CheckCircle, XCircle, ExternalLink } from 'lucide-react';
import { dashboardAPI, adminAPI, reportsAPI } from '../lib/api';
import { ROLES } from '../lib/constants';
import useAuth from '../hooks/useAuth';
import { timeAgo, truncate, formatNumber, getErrorMessage } from '../lib/utils';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [threads, setThreads] = useState([]);
  const [comments, setComments] = useState([]);
  const [platformStats, setPlatformStats] = useState(null);
  const [modActivity, setModActivity] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, threadsRes, commentsRes] = await Promise.all([
          dashboardAPI.myStats(),
          dashboardAPI.myThreads({ limit: 5 }),
          dashboardAPI.myComments({ limit: 5 }),
        ]);
        setStats(statsRes.data);
        setThreads(threadsRes.data.items);
        setComments(commentsRes.data.items);

        if (user.role === ROLES.ADMIN) {
          const { data } = await dashboardAPI.adminStats();
          setPlatformStats(data);
        }

        if (user.role === ROLES.MODERATOR || user.role === ROLES.ADMIN) {
          const { data } = await dashboardAPI.modActivity({ hours: 24 });
          setModActivity(data);
        }
      } catch { /* ignore */ } finally {
        setLoading(false);
      }
    };
    load();
  }, [user.role]);

  if (loading) {
    return <div className="flex justify-center py-20"><Spinner size={28} /></div>;
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-xl font-bold mb-6">Dashboard</h1>

      {/* Personal stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <StatCard icon={MessageSquare} label="Threads" value={stats.thread_count} />
          <StatCard icon={MessageCircle} label="Comments" value={stats.comment_count} />
          <StatCard icon={Heart} label="Likes Received" value={stats.likes_received} />
        </div>
      )}

      {/* Admin platform stats */}
      {platformStats && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">Platform Overview</h2>
          <div className="grid grid-cols-3 gap-3">
            <StatCard icon={TrendingUp} label="Total Users" value={platformStats.total_users} />
            <StatCard icon={MessageSquare} label="Total Threads" value={platformStats.total_threads} />
            <StatCard icon={MessageCircle} label="Total Comments" value={platformStats.total_comments} />
          </div>
        </div>
      )}

      {/* Admin: User Management */}
      {user.role === ROLES.ADMIN && <UserManagement currentUserId={user.id} />}

      {/* Report Management (admin + moderator) */}
      {(user.role === ROLES.ADMIN || user.role === ROLES.MODERATOR) && <ReportManagement />}

      {/* Moderator activity */}
      {modActivity && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Eye size={18} className="text-primary-500" /> Recent Activity (Last 24h)
          </h2>
          {modActivity.recent_threads?.length > 0 && (
            <div className="mb-3">
              <h3 className="text-sm font-medium text-text-secondary mb-2">New Threads</h3>
              <div className="space-y-2">
                {modActivity.recent_threads.map((t) => (
                  <Link
                    key={t.id}
                    to={`/threads/${t.id}`}
                    className="block bg-surface border border-border rounded-lg p-3 hover:border-primary-200 transition"
                  >
                    <h3 className="font-medium text-sm">{t.title}</h3>
                    <div className="flex gap-3 mt-1 text-xs text-text-muted">
                      <span>{t.author_username}</span>
                      <span>{timeAgo(t.created_at)}</span>
                      <span><Heart size={11} className="inline" /> {t.like_count}</span>
                      <span><MessageCircle size={11} className="inline" /> {t.comment_count}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
          {modActivity.recent_comments?.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-text-secondary mb-2">New Comments</h3>
              <div className="space-y-2">
                {modActivity.recent_comments.map((c) => (
                  <Link
                    key={c.id}
                    to={`/threads/${c.thread_id}`}
                    className="block bg-surface border border-border rounded-lg p-3 hover:border-primary-200 transition"
                  >
                    <p className="text-sm">{truncate(c.content, 120)}</p>
                    <div className="flex gap-3 mt-1 text-xs text-text-muted">
                      <span>{c.author_username}</span>
                      <span>{timeAgo(c.created_at)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
          {(!modActivity.recent_threads?.length && !modActivity.recent_comments?.length) && (
            <p className="text-sm text-text-muted">No recent activity in the last 24 hours.</p>
          )}
        </div>
      )}

      {/* My threads */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">My Threads</h2>
        {threads.length === 0 ? (
          <p className="text-sm text-text-muted">No threads yet</p>
        ) : (
          <div className="space-y-2">
            {threads.map((t) => (
              <Link
                key={t.id}
                to={`/threads/${t.id}`}
                className="block bg-surface border border-border rounded-lg p-3 hover:border-primary-200 transition"
              >
                <h3 className="font-medium text-sm">{t.title}</h3>
                <div className="flex gap-3 mt-1 text-xs text-text-muted">
                  <span>{timeAgo(t.created_at)}</span>
                  <span><Heart size={11} className="inline" /> {t.like_count}</span>
                  <span><MessageCircle size={11} className="inline" /> {t.comment_count}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* My comments */}
      <div>
        <h2 className="text-lg font-semibold mb-3">My Recent Comments</h2>
        {comments.length === 0 ? (
          <p className="text-sm text-text-muted">No comments yet</p>
        ) : (
          <div className="space-y-2">
            {comments.map((c) => (
              <Link
                key={c.id}
                to={`/threads/${c.thread_id}`}
                className="block bg-surface border border-border rounded-lg p-3 hover:border-primary-200 transition"
              >
                <p className="text-sm">{truncate(c.content, 120)}</p>
                <div className="flex gap-3 mt-1 text-xs text-text-muted">
                  <span>{timeAgo(c.created_at)}</span>
                  <span><Heart size={11} className="inline" /> {c.like_count}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }) {
  const IconComponent = icon;
  return (
    <div className="bg-surface border border-border rounded-xl p-4 text-center">
      <IconComponent size={20} className="mx-auto text-primary-500 mb-1" />
      <p className="text-2xl font-bold">{formatNumber(value)}</p>
      <p className="text-xs text-text-muted">{label}</p>
    </div>
  );
}

// ── Admin User Management ───────────────────────────────────────────
const ROLE_OPTIONS = [ROLES.MEMBER, ROLES.MODERATOR, ROLES.ADMIN];
const ROLE_BADGE_VARIANT = { admin: 'danger', moderator: 'warning', member: 'default' };

function UserManagement({ currentUserId }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nextCursor, setNextCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  const fetchUsers = useCallback(async (cursor = null) => {
    try {
      setError('');
      const params = { limit: 20 };
      if (cursor) params.cursor = cursor;
      const { data } = await adminAPI.listUsers(params);
      if (cursor) {
        setUsers((prev) => [...prev, ...data.items]);
      } else {
        setUsers(data.items);
      }
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleRoleChange = async (userId, newRole) => {
    setActionLoading(userId);
    try {
      const { data } = await adminAPI.updateRole(userId, newRole);
      setUsers((prev) => prev.map((u) => (u.id === userId ? data : u)));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleActive = async (userId, isActive) => {
    setActionLoading(userId);
    try {
      const { data } = isActive
        ? await adminAPI.deactivate(userId)
        : await adminAPI.reactivate(userId);
      setUsers((prev) => prev.map((u) => (u.id === userId ? data : u)));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Users size={18} className="text-primary-500" /> User Management
        </h2>
        <div className="flex justify-center py-6"><Spinner size={24} /></div>
      </div>
    );
  }

  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <Users size={18} className="text-primary-500" /> User Management
      </h2>

      {error && (
        <div className="mb-3 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">
          {error}
        </div>
      )}

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-alt">
                <th className="text-left px-4 py-2.5 font-medium text-text-secondary">User</th>
                <th className="text-left px-4 py-2.5 font-medium text-text-secondary">Role</th>
                <th className="text-left px-4 py-2.5 font-medium text-text-secondary">Status</th>
                <th className="text-right px-4 py-2.5 font-medium text-text-secondary">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = u.id === currentUserId;
                const isProcessing = actionLoading === u.id;
                return (
                  <tr key={u.id} className="border-b border-border last:border-0 hover:bg-surface-alt/50 transition">
                    <td className="px-4 py-3">
                      <div>
                        <span className="font-medium">{u.username}</span>
                        <p className="text-xs text-text-muted">{u.email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {isSelf ? (
                        <Badge variant={ROLE_BADGE_VARIANT[u.role]}>{u.role}</Badge>
                      ) : (
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          disabled={isProcessing}
                          className="text-xs border border-border rounded-md px-2 py-1 bg-surface focus:outline-none focus:ring-2 focus:ring-primary-300 disabled:opacity-50"
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>{r}</option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={u.is_active ? 'success' : 'danger'}>
                        {u.is_active ? 'Active' : 'Deactivated'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!isSelf && (
                        <button
                          onClick={() => handleToggleActive(u.id, u.is_active)}
                          disabled={isProcessing}
                          className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-md transition disabled:opacity-50 ${
                            u.is_active
                              ? 'text-danger hover:bg-red-50'
                              : 'text-green-700 hover:bg-green-50'
                          }`}
                        >
                          {isProcessing ? (
                            <Spinner size={12} />
                          ) : u.is_active ? (
                            <><UserX size={13} /> Deactivate</>
                          ) : (
                            <><UserCheck size={13} /> Reactivate</>
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {hasMore && (
          <div className="px-4 py-3 border-t border-border text-center">
            <button
              onClick={() => fetchUsers(nextCursor)}
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              Load more users
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Report Management ───────────────────────────────────────────────
const STATUS_BADGE_VARIANT = { pending: 'warning', resolved: 'success', dismissed: 'default' };

function ReportManagement() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [nextCursor, setNextCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState('');

  const fetchReports = useCallback(async (cursor = null) => {
    if (!cursor) setLoading(true);
    setError('');
    try {
      const params = { limit: 20 };
      if (filter) params.status = filter;
      if (cursor) params.cursor = cursor;
      const { data } = await reportsAPI.list(params);
      if (cursor) {
        setReports((prev) => [...prev, ...data.items]);
      } else {
        setReports(data.items);
      }
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const handleResolve = async (reportId, action) => {
    setActionLoading(reportId);
    try {
      const { data } = await reportsAPI.resolve(reportId, action);
      setReports((prev) => prev.map((r) => (r.id === reportId ? data : r)));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <Flag size={18} className="text-primary-500" /> Reports
      </h2>

      <div className="flex gap-2 mb-3">
        {['pending', 'resolved', 'dismissed'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`text-xs px-3 py-1 rounded-full border transition ${
              filter === s ? 'bg-primary-500 text-white border-primary-500' : 'border-border text-text-secondary hover:bg-surface-alt'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-3 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-6"><Spinner size={24} /></div>
      ) : reports.length === 0 ? (
        <p className="text-sm text-text-muted">No {filter} reports.</p>
      ) : (
        <div className="space-y-2">
          {reports.map((r) => (
            <div key={r.id} className="bg-surface border border-border rounded-lg p-3">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center text-xs font-medium px-1.5 py-0.5 rounded bg-surface-alt border border-border">
                      {r.target_type}
                    </span>
                    {r.target_author_username && (
                      <span className="text-xs text-text-secondary">
                        by <Link to={`/u/${r.target_author_username}`} className="font-medium hover:text-primary-600 hover:underline">{r.target_author_username}</Link>
                      </span>
                    )}
                    {r.thread_id && (
                      <Link
                        to={r.target_type === 'comment' ? `/threads/${r.thread_id}?highlight=${r.target_id}` : `/threads/${r.thread_id}`}
                        className="inline-flex items-center gap-0.5 text-xs text-primary-600 hover:underline"
                      >
                        <ExternalLink size={11} /> View
                      </Link>
                    )}
                  </div>
                  {r.target_content && (
                    <p className="text-sm mt-1.5 px-2 py-1.5 bg-surface-alt border-l-2 border-primary-300 rounded-r text-text-secondary line-clamp-2">
                      {r.target_content}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs font-medium text-warning">{r.reason}</span>
                    {r.description && <span className="text-xs text-text-muted">— {r.description}</span>}
                  </div>
                  <p className="text-xs text-text-muted mt-1">{timeAgo(r.created_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={STATUS_BADGE_VARIANT[r.status]}>{r.status}</Badge>
                  {r.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleResolve(r.id, 'resolved')}
                        disabled={actionLoading === r.id}
                        className="text-green-600 hover:bg-green-50 p-1 rounded transition disabled:opacity-50"
                        title="Resolve"
                      >
                        <CheckCircle size={16} />
                      </button>
                      <button
                        onClick={() => handleResolve(r.id, 'dismissed')}
                        disabled={actionLoading === r.id}
                        className="text-text-muted hover:bg-surface-alt p-1 rounded transition disabled:opacity-50"
                        title="Dismiss"
                      >
                        <XCircle size={16} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {hasMore && (
        <div className="text-center mt-3">
          <button
            onClick={() => fetchReports(nextCursor)}
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            Load more reports
          </button>
        </div>
      )}
    </div>
  );
}
