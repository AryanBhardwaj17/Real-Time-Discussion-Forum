import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { getErrorMessage } from '../lib/utils';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [form, setForm] = useState({ login: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const deactivated = searchParams.get('deactivated') === '1';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (deactivated) setSearchParams({}, { replace: true });
    setLoading(true);
    try {
      await login(form.login, form.password);
      navigate('/');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <div className="w-full max-w-sm bg-surface border border-border rounded-xl p-6 shadow-sm">
        <h1 className="text-xl font-bold text-center mb-6">Welcome back</h1>

        {deactivated && (
          <div className="mb-4 px-3 py-2 bg-amber-50 text-amber-800 text-sm rounded-lg border border-amber-200">
            Your account has been deactivated by an administrator. Contact support for help.
          </div>
        )}

        {error && (
          <div className="mb-4 px-3 py-2 bg-red-50 text-danger text-sm rounded-lg border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Email or Username"
            type="text"
            value={form.login}
            onChange={(e) => setForm({ ...form, login: e.target.value })}
            placeholder="you@example.com"
            required
          />
          <Input
            label="Password"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="••••••••"
            required
          />
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        <p className="mt-4 text-sm text-text-secondary text-center">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary-600 hover:underline font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
