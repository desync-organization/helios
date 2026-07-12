import { create } from "zustand";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface VercelUser {
  id: string;
  email: string;
  name: string | null;
  username: string;
}

interface AuthState {
  /* Vercel */
  vercelUser: VercelUser | null;
  vercelToken: string | null;
  isVercelConnected: boolean;

  /* GitHub PAT */
  githubToken: string | null;
  isGithubConnected: boolean;

  /* Loading / error */
  isLoading: boolean;
  error: string | null;

  /* Actions */
  setVercelAuth: (user: VercelUser, token: string) => void;
  clearVercelAuth: () => void;
  setGithubToken: (token: string) => void;
  clearGithubToken: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  hydrateFromServer: () => Promise<void>;
}

/* ------------------------------------------------------------------ */
/*  Store                                                              */
/* ------------------------------------------------------------------ */

export const useAuthStore = create<AuthState>((set) => ({
  vercelUser: null,
  vercelToken: null,
  isVercelConnected: false,

  githubToken: null,
  isGithubConnected: false,

  isLoading: false,
  error: null,

  setVercelAuth: (user, token) =>
    set({
      vercelUser: user,
      vercelToken: token,
      isVercelConnected: true,
      error: null,
    }),

  clearVercelAuth: () =>
    set({
      vercelUser: null,
      vercelToken: null,
      isVercelConnected: false,
    }),

  setGithubToken: (token) =>
    set({
      githubToken: token,
      isGithubConnected: true,
      error: null,
    }),

  clearGithubToken: () =>
    set({
      githubToken: null,
      isGithubConnected: false,
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  /**
   * On mount, ask the server whether tokens are already stored
   * so the UI can reflect persisted state across refreshes.
   */
  hydrateFromServer: async () => {
    try {
      const res = await fetch("/api/auth/status");
      if (!res.ok) return;
      const data = await res.json();
      set({
        isVercelConnected: data.vercelConnected ?? false,
        vercelUser: data.vercelUser ?? null,
        isGithubConnected: data.githubConnected ?? false,
      });
    } catch {
      /* silent – dev server may not be running */
    }
  },
}));
