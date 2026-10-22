// Auth Hook
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types/api';
import { api } from '../api/client';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
  updateMe: (data: { full_name?: string; password?: string }) => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      clearError: () => set({ error: null }),

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          await api.login(email, password);
          await get().fetchMe();
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } } };
          set({ error: error.response?.data?.detail || 'Login failed', isLoading: false });
          throw err;
        }
      },

      register: async (email: string, password: string, fullName?: string) => {
        set({ isLoading: true, error: null });
        try {
          await api.register(email, password, fullName);
          await get().login(email, password);
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } } };
          set({ error: error.response?.data?.detail || 'Registration failed', isLoading: false });
          throw err;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          await api.logout();
        } finally {
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      updateMe: async (data: { full_name?: string; password?: string }) => {
        set({ isLoading: true, error: null });
        try {
          const user = await api.updateMe(data);
          set({ user, isLoading: false });
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } } };
          set({ error: error.response?.data?.detail || 'Failed to update profile', isLoading: false });
          throw err;
        }
      },

      fetchMe: async () => {
        try {
          const user = await api.getMe();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);