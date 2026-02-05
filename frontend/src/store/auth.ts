import { create } from 'zustand';
import type { AuthSession } from '../types';
import { authApi } from '../lib/api';

interface AuthState {
  session: AuthSession | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  setSession: (session: AuthSession | null) => void;
  fetchSession: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  isLoading: true,
  isAuthenticated: false,
  isAdmin: false,

  setSession: (session) => {
    set({
      session,
      isAuthenticated: !!session,
      isAdmin: !!session?.is_admin || !!session?.is_super_admin,
      isLoading: false,
    });
  },

  fetchSession: async () => {
    set({ isLoading: true });
    try {
      const session = await authApi.getSession();
      get().setSession(session);
    } catch {
      get().setSession(null);
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } finally {
      set({
        session: null,
        isAuthenticated: false,
        isAdmin: false,
      });
    }
  },
}));
