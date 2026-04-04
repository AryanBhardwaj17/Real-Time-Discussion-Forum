import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { MessageCircle, Heart, FileText } from 'lucide-react';
import { usersAPI, profilesAPI } from '../lib/api';
import { getErrorMessage, timeAgo, formatNumber } from '../lib/utils';
import Avatar from '../components/ui/Avatar';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';

export default function UserProfilePage() {
  const { username } = useParams();
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [threads, setThreads] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      setThreads([]);
      setCursor(null);
      setHasMore(false);
      setStats(null);
      try {
        const { data: user } = await usersAPI.getPublicProfile(username);
        setProfile(user);

        const [threadsRes, statsRes] = await Promise.all([
          profilesAPI.threads(user.id, { limit: 10 }),
          profilesAPI.stats(user.id),
        ]);
        setThreads(threadsRes.data.items);
        setCursor(threadsRes.data.next_cursor);
        setHasMore(threadsRes.data.has_more);
        setStats(statsRes.data);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [username]);

  const loadMore = async () => {
    if (!profile || !cursor) return;
    setLoadingMore(true);
    try {
      const { data } = await profilesAPI.threads(profile.id, { cursor, limit: 10 });
      setThreads((prev) => [...prev, ...data.items]);
      setCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch { /* ignore */ } finally {
      setLoadingMore(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size={28} />
      </div>
    );
  }

  if (error) {
    return <div className="text-center py-12 text-red-500">{error}</div>;
  }

  if (!profile) return null;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Profile card */}
      <div className="bg-surface border border-border rounded-xl p-6 mb-6">
        <div className="flex items-center gap-4">
          <Avatar username={profile.username} avatarUrl={profile.avatar_url} size="lg" />
          <div>
            <h1 className="text-xl font-bold">{profile.username}</h1>
            {profile.name && <p className="text-text-secondary">{profile.name}</p>}
            <Badge variant="primary" className="mt-1">{profile.role}</Badge>
          </div>
        </div>
        {profile.bio && (
          <p className="mt-4 text-text-secondary">{profile.bio}</p>
        )}
        <p className="mt-2 text-xs text-text-muted">
          Joined {timeAgo(profile.created_at)}
        </p>

        {/* Stats */}
        {stats && (
          <div className="flex gap-6 mt-4 pt-4 border-t border-border">
            <div className="text-center">
              <p className="text-lg font-bold">{formatNumber(stats.thread_count)}</p>
              <p className="text-xs text-text-muted flex items-center gap-1"><FileText size={12} /> Threads</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold">{formatNumber(stats.comment_count)}</p>
              <p className="text-xs text-text-muted flex items-center gap-1"><MessageCircle size={12} /> Comments</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold">{formatNumber(stats.likes_received)}</p>
              <p className="text-xs text-text-muted flex items-center gap-1"><Heart size={12} /> Likes</p>
            </div>
          </div>
        )}
      </div>

      {/* Threads */}
      <h2 className="text-lg font-semibold mb-3">Threads</h2>
      {threads.length === 0 ? (
        <p className="text-text-secondary text-sm">No threads yet.</p>
      ) : (
        <div className="space-y-2">
          {threads.map((t) => (
            <Link
              key={t.id}
              to={`/threads/${t.id}`}
              className="block bg-surface border border-border rounded-lg p-3 hover:border-primary-200 hover:shadow-sm transition-colors"
            >
              <p className="font-medium">{t.title}</p>
              <p className="text-xs text-text-muted mt-1">
                {timeAgo(t.created_at)} · {t.comment_count} comments · {t.like_count} likes
              </p>
            </Link>
          ))}
        </div>
      )}

      {hasMore && (
        <div className="text-center mt-4">
          <Button variant="secondary" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? 'Loading…' : 'Load More'}
          </Button>
        </div>
      )}
    </div>
  );
}
