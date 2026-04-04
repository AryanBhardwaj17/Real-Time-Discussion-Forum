import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { threadsAPI } from '../lib/api';
import { getErrorMessage } from '../lib/utils';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

export default function CreateThreadPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: '', description: '', tags: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const tags = form.tags
        ? form.tags.split(',').map((t) => t.trim()).filter(Boolean)
        : null;
      const { data } = await threadsAPI.create({ title: form.title, description: form.description, tags });
      navigate(`/threads/${data.id}`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-6">Create a new thread</h1>

      {error && (
        <div className="mb-4 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 bg-surface border border-border rounded-xl p-6">
        <Input
          label="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="What's on your mind?"
          required
          minLength={3}
        />
        <div className="space-y-1">
          <label className="block text-sm font-medium text-text-secondary">Content</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Share your thoughts…"
            required
            rows={8}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-300 focus:border-primary-400 transition resize-y"
          />
        </div>
        <Input
          label="Tags (comma-separated)"
          value={form.tags}
          onChange={(e) => setForm({ ...form, tags: e.target.value })}
          placeholder="javascript, react, help"
        />
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" type="button" onClick={() => navigate(-1)}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? 'Posting…' : 'Post Thread'}
          </Button>
        </div>
      </form>
    </div>
  );
}
