import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { authAPI } from '../lib/api';
import { getErrorMessage } from '../lib/utils';
import Avatar from '../components/ui/Avatar';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Badge from '../components/ui/Badge';

export default function ProfilePage() {
  const { user, updateProfile, deactivateAccount, deleteAccount } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: user?.name || '',
    bio: user?.bio || '',
    avatar_url: user?.avatar_url || '',
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      await updateProfile(form);
      setMessage('Profile updated!');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (!user) return null;

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-xl font-bold mb-6">Profile</h1>

      <div className="bg-surface border border-border rounded-xl p-6">
        <div className="flex items-center gap-4 mb-6">
          <Avatar username={user.username} avatarUrl={user.avatar_url} size="lg" />
          <div>
            <p className="font-semibold">{user.username}</p>
            <p className="text-sm text-text-secondary">{user.email}</p>
            <Badge variant="primary" className="mt-1">{user.role}</Badge>
          </div>
        </div>

        {message && (
          <div className="mb-4 px-3 py-2 bg-green-50 text-success text-sm rounded-lg border border-green-200">
            {message}
          </div>
        )}
        {error && (
          <div className="mb-4 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Display Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Your name"
          />
          <div className="space-y-1">
            <label className="block text-sm font-medium text-text-secondary">Bio</label>
            <textarea
              value={form.bio}
              onChange={(e) => setForm({ ...form, bio: e.target.value })}
              placeholder="Tell us about yourself…"
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-300 transition resize-y"
            />
          </div>
          <Input
            label="Avatar URL"
            type="url"
            value={form.avatar_url}
            onChange={(e) => setForm({ ...form, avatar_url: e.target.value })}
            placeholder="https://example.com/avatar.jpg"
          />
          <Button type="submit" disabled={saving} className="w-full">
            {saving ? 'Saving…' : 'Save Changes'}
          </Button>
        </form>
      </div>

      {/* ── Change Password ─────────────────────────────────────── */}
      <ChangePasswordSection />

      {/* ── Account Actions ─────────────────────────────────────── */}
      <AccountActions
        onDeactivate={async () => {
          await deactivateAccount();
          navigate('/login');
        }}
        onDelete={async () => {
          await deleteAccount();
          navigate('/login');
        }}
      />
    </div>
  );
}


/* ── Change password section ─────────────────────────────────────── */
function ChangePasswordSection() {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (form.new_password !== form.confirm) {
      setError('New passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await authAPI.changePassword({
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setMessage('Password changed successfully!');
      setForm({ current_password: '', new_password: '', confirm: '' });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-8 bg-surface border border-border rounded-xl p-6">
      <h2 className="text-lg font-semibold mb-4">Change Password</h2>

      {message && (
        <div className="mb-4 px-3 py-2 bg-green-50 text-success text-sm rounded-lg border border-green-200">
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Current Password"
          type="password"
          value={form.current_password}
          onChange={(e) => setForm({ ...form, current_password: e.target.value })}
          placeholder="Enter current password"
          required
        />
        <div className="space-y-1">
          <Input
            label="New Password"
            type="password"
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
            placeholder="Create a strong password"
            required
          />
          <ul className="text-xs text-text-secondary space-y-0.5 pl-4 list-disc">
            <li>At least 8 characters</li>
            <li>One uppercase letter (A-Z)</li>
            <li>One lowercase letter (a-z)</li>
            <li>One digit (0-9)</li>
            <li>One special character (!@#$%^&* etc.)</li>
          </ul>
        </div>
        <Input
          label="Confirm New Password"
          type="password"
          value={form.confirm}
          onChange={(e) => setForm({ ...form, confirm: e.target.value })}
          placeholder="Re-enter new password"
          required
        />
        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Changing…' : 'Change Password'}
        </Button>
      </form>
    </div>
  );
}


/* ── Confirmation-gated account actions ─────────────────────────── */
function AccountActions({ onDeactivate, onDelete }) {
  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDeactivate = async () => {
    setLoading(true);
    setError('');
    try {
      await onDeactivate();
    } catch (err) {
      setError(getErrorMessage(err));
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (deleteConfirm !== 'DELETE') return;
    setLoading(true);
    setError('');
    try {
      await onDelete();
    } catch (err) {
      setError(getErrorMessage(err));
      setLoading(false);
    }
  };

  return (
    <div className="mt-8 bg-surface border border-border rounded-xl p-6">
      <h2 className="text-lg font-semibold text-danger mb-4">Danger Zone</h2>

      {error && (
        <div className="mb-4 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* Deactivate */}
      <div className="flex items-center justify-between py-3 border-b border-border">
        <div>
          <p className="font-medium">Deactivate Account</p>
          <p className="text-sm text-text-secondary">Temporarily disable your account. Your data will be preserved.</p>
        </div>
        <Button
          variant="outline"
          className="text-danger border-danger hover:bg-red-50"
          onClick={() => setShowDeactivate(true)}
        >
          Deactivate
        </Button>
      </div>

      {showDeactivate && (
        <div className="mt-3 mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm mb-3">
            Are you sure you want to deactivate your account? You will be logged out and won't be able to sign in until an admin reactivates your account.
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="text-danger border-danger hover:bg-red-100"
              disabled={loading}
              onClick={handleDeactivate}
            >
              {loading ? 'Deactivating…' : 'Yes, deactivate'}
            </Button>
            <Button variant="ghost" onClick={() => setShowDeactivate(false)}>Cancel</Button>
          </div>
        </div>
      )}

      {/* Delete */}
      <div className="flex items-center justify-between py-3 mt-2">
        <div>
          <p className="font-medium">Delete Account</p>
          <p className="text-sm text-text-secondary">Permanently delete your account and all associated data. This cannot be undone.</p>
        </div>
        <Button
          className="bg-danger text-white hover:bg-red-700"
          onClick={() => setShowDelete(true)}
        >
          Delete
        </Button>
      </div>

      {showDelete && (
        <div className="mt-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm font-semibold text-danger mb-2">This action is permanent and irreversible.</p>
          <p className="text-sm mb-1">All your data — threads, comments, likes, and tokens — will be permanently removed.</p>
          <p className="text-sm mb-3">Type <span className="font-mono font-bold">DELETE</span> below to confirm:</p>
          <input
            type="text"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder="Type DELETE to confirm"
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-red-300 transition mb-3"
          />
          <div className="flex gap-2">
            <Button
              className="bg-danger text-white hover:bg-red-700"
              disabled={loading || deleteConfirm !== 'DELETE'}
              onClick={handleDelete}
            >
              {loading ? 'Deleting…' : 'Permanently delete my account'}
            </Button>
            <Button variant="ghost" onClick={() => { setShowDelete(false); setDeleteConfirm(''); }}>Cancel</Button>
          </div>
        </div>
      )}
    </div>
  );
}
