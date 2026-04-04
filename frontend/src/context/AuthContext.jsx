import { createContext, useState, useEffect, useCallback } from 'react';
import { authAPI, usersAPI } from '../lib/api';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const { data } = await usersAPI.getMe();
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = async (loginValue, password) => {
    await authAPI.login({ login: loginValue, password });
    await fetchUser();
  };

  const register = async (formData) => {
    await authAPI.register(formData);
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch {
      // ignore
    }
    setUser(null);
  };

  const updateProfile = async (data) => {
    const { data: updated } = await usersAPI.updateMe(data);
    setUser(updated);
  };

  const deactivateAccount = async () => {
    await usersAPI.deactivateMe();
    setUser(null);
  };

  const deleteAccount = async () => {
    await usersAPI.deleteMe();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, register, logout, updateProfile, deactivateAccount, deleteAccount, fetchUser }}>
      {children}
    </AuthContext.Provider>
  );
}
