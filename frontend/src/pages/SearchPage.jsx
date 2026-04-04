import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Search as SearchIcon, MessageCircle, Heart } from 'lucide-react';
import { searchAPI } from '../lib/api';
import { PAGINATION } from '../lib/constants';
import { timeAgo, truncate, formatNumber } from '../lib/utils';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get('q') || '';
  const [query, setQuery] = useState(q);
  const [results, setResults] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (q) {
      setQuery(q);
      doSearch(q);
    }
  }, [q]);

  const doSearch = async (searchQuery, nextCursor = null) => {
    setLoading(true);
    try {
      const { data } = await searchAPI.threads({ q: searchQuery, cursor: nextCursor, limit: PAGINATION.THREADS_PER_PAGE });
      setResults((prev) => (nextCursor ? [...prev, ...data.items] : data.items));
      setCursor(data.next_cursor);
      setHasMore(data.has_more);
      setSearched(true);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      setSearchParams({ q: query.trim() });
      setResults([]);
      setCursor(null);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="relative max-w-lg">
          <SearchIcon size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search threads…"
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-surface text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-300 transition"
            autoFocus
          />
        </div>
      </form>

      {loading && results.length === 0 && (
        <div className="flex justify-center py-12"><Spinner size={28} /></div>
      )}

      {searched && results.length === 0 && !loading && (
        <p className="text-center py-12 text-text-muted">No results found for "{q}"</p>
      )}

      <div className="space-y-2">
        {results.map((thread) => (
          <Link
            key={thread.id}
            to={`/threads/${thread.id}`}
            className="block bg-surface border border-border rounded-xl p-4 hover:border-primary-200 hover:shadow-sm transition"
          >
            <h3 className="font-semibold">{thread.title}</h3>
            <p className="text-sm text-text-secondary mt-1 line-clamp-2">{truncate(thread.description, 180)}</p>
            {thread.tags?.length > 0 && (
              <div className="flex gap-1 mt-2">
                {thread.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)}
              </div>
            )}
            <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
              <span>{thread.author_username}</span>
              <span>{timeAgo(thread.created_at)}</span>
              <span className="flex items-center gap-0.5"><Heart size={12} /> {formatNumber(thread.like_count)}</span>
              <span className="flex items-center gap-0.5"><MessageCircle size={12} /> {formatNumber(thread.comment_count)}</span>
            </div>
          </Link>
        ))}
      </div>

      {hasMore && (
        <div className="text-center mt-4">
          <Button variant="secondary" onClick={() => doSearch(q, cursor)} disabled={loading}>
            {loading ? 'Loading…' : 'Load More'}
          </Button>
        </div>
      )}
    </div>
  );
}
