import { useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MessageSquare, Search, LogOut, User, LayoutDashboard, ChevronDown } from 'lucide-react';
import useAuth from '../hooks/useAuth';
import useClickOutside from '../hooks/useClickOutside';
import Avatar from './ui/Avatar';
import NotificationBell from './NotificationBell';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  useClickOutside(menuRef, () => setMenuOpen(false));

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-50 bg-surface/80 backdrop-blur-md border-b border-border">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 text-primary-600 font-bold text-lg shrink-0">
          <MessageSquare size={22} />
          <span className="hidden sm:inline">Forum</span>
        </Link>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex-1 max-w-md">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search threads…"
              className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-border bg-surface-alt focus:outline-none focus:ring-2 focus:ring-primary-300 focus:border-primary-400 transition"
            />
          </div>
        </form>

        {/* Right side */}
        <div className="flex items-center gap-2">
          {user ? (
            <>
              <NotificationBell />

              {/* User menu */}
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-surface-hover transition"
                >
                  <Avatar username={user.username} avatarUrl={user.avatar_url} size="sm" />
                  <span className="hidden sm:inline text-sm font-medium">{user.username}</span>
                  <ChevronDown size={14} className="text-text-muted" />
                </button>

                {menuOpen && (
                  <div className="absolute right-0 mt-1 w-48 bg-surface border border-border rounded-lg shadow-lg py-1">
                    <Link
                      to="/profile"
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-surface-hover transition"
                    >
                      <User size={15} /> Profile
                    </Link>
                    <Link
                      to="/dashboard"
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-surface-hover transition"
                    >
                      <LayoutDashboard size={15} /> Dashboard
                    </Link>
                    <hr className="my-1 border-border" />
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 px-3 py-2 text-sm text-danger hover:bg-surface-hover transition w-full"
                    >
                      <LogOut size={15} /> Logout
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text transition"
              >
                Log in
              </Link>
              <Link
                to="/register"
                className="px-3 py-1.5 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
