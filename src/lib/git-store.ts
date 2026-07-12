/**
 * Zustand store for git branch management in the multiverse view.
 * Handles fetching branches, creating new branches, and managing branch operations.
 */
import { create } from "zustand";

export interface GitBranch {
  id: string;
  name: string;
  description?: string;
  isActive: boolean;
  lastCommit?: string;
}

interface GitState {
  /** List of all git branches */
  branches: GitBranch[];
  /** Currently active branch */
  activeBranch: string | null;
  /** Loading state */
  loading: boolean;
  /** Error message if any */
  error: string | null;
  /** Fetch all branches from the repository */
  fetchBranches: () => Promise<void>;
  /** Create a new branch with a custom name or random if not provided */
  createBranch: (branchName?: string) => Promise<void>;
  /** Delete a branch by name */
  deleteBranch: (branchName: string) => Promise<void>;
  /** Switch to a different branch */
  checkoutBranch: (branchName: string) => Promise<void>;
  /** Merge a branch into another branch (from -> to) */
  mergeBranch: (fromBranch: string, toBranch: string) => Promise<void>;
}

/**
 * Generate a random branch name using adjectives and nouns.
 */
function generateBranchName(): string {
  const adjectives = [
    "quantum",
    "stellar",
    "cosmic",
    "prismatic",
    "ethereal",
    "luminous",
    "crystalline",
    "nebular",
    "radiant",
    "spectral",
  ];
  const nouns = [
    "nexus",
    "realm",
    "dimension",
    "matrix",
    "vortex",
    "cascade",
    "horizon",
    "anomaly",
    "singularity",
    "continuum",
  ];

  const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
  const noun = nouns[Math.floor(Math.random() * nouns.length)];
  const num = Math.floor(Math.random() * 1000);

  return `${adj}-${noun}-${num}`;
}

/**
 * Call the backend API to execute git commands.
 * In a real implementation, this would hit a proper backend endpoint.
 * For now, we'll use fetch with a mock/future endpoint.
 */
async function executeGitCommand(command: string): Promise<string> {
  try {
    const response = await fetch("/api/git", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });

    if (!response.ok) {
      throw new Error(`Git command failed: ${response.statusText}`);
    }

    const data = (await response.json()) as { output: string; error?: string };
    if (data.error) throw new Error(data.error);
    return data.output;
  } catch (error) {
    console.error("Git command error:", error);
    throw error;
  }
}

export const useGitStore = create<GitState>((set, get) => ({
  branches: [],
  activeBranch: null,
  loading: false,
  error: null,

  fetchBranches: async () => {
    set({ loading: true, error: null });
    try {
      // Get list of all branches
      const output = await executeGitCommand("git branch -a");
      const lines = output
        .split("\n")
        .filter((line) => line.trim())
        .map((line) => line.trim());

      const branches: GitBranch[] = [];
      let activeBranch: string | null = null;

      for (const line of lines) {
        const isActive = line.startsWith("*");
        const name = line.replace("*", "").trim().replace("remotes/origin/", "");

        // Skip HEAD entries
        if (name.includes("HEAD")) continue;

        const branch: GitBranch = {
          id: name,
          name,
          isActive,
        };

        branches.push(branch);
        if (isActive) activeBranch = name;
      }

      set({ branches, activeBranch, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch branches",
        loading: false,
      });
    }
  },

  createBranch: async (branchName?: string) => {
    set({ loading: true, error: null });
    try {
      const name = branchName || generateBranchName();
      await executeGitCommand(`git branch ${name}`);

      // Refetch branches to update the list
      await get().fetchBranches();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create branch",
        loading: false,
      });
    }
  },

  deleteBranch: async (branchName: string) => {
    set({ loading: true, error: null });
    try {
      // Check if trying to delete active branch
      if (branchName === get().activeBranch) {
        throw new Error("Cannot delete the currently active branch");
      }

      await executeGitCommand(`git branch -d ${branchName}`);

      // Refetch branches to update the list
      await get().fetchBranches();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete branch",
        loading: false,
      });
    }
  },

  checkoutBranch: async (branchName: string) => {
    set({ loading: true, error: null });
    try {
      await executeGitCommand(`git checkout ${branchName}`);

      // Refetch branches to update active state
      await get().fetchBranches();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to checkout branch",
        loading: false,
      });
    }
  },

  mergeBranch: async (fromBranch: string, toBranch: string) => {
    set({ loading: true, error: null });
    try {
      const originalBranch = get().activeBranch;

      // Checkout the target branch first
      await executeGitCommand(`git checkout ${toBranch}`);

      // Merge the source branch into it
      await executeGitCommand(`git merge ${fromBranch}`);

      // Optionally return to the original branch
      if (originalBranch && originalBranch !== toBranch) {
        await executeGitCommand(`git checkout ${originalBranch}`);
      }

      // Refetch branches
      await get().fetchBranches();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to merge branch",
        loading: false,
      });
    }
  },
}));
