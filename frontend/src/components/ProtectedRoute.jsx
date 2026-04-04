import { Navigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import Spinner from './ui/Spinner';

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size={28} />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return children;
}
