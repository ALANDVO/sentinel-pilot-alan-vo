// Mods Hook
import { create } from 'zustand';
import type { Mod, ModCreate, ModUpdate } from '../types/api';
import { api } from '../api/client';

interface ModsState {
  mods: Mod[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  isLoading: boolean;
  error: string | null;
  fetchMods: (params?: { instance_id?: number; page?: number; page_size?: number; enabled_only?: boolean }) => Promise<void>;
  createMod: (data: ModCreate) => Promise<Mod>;
  updateMod: (id: number, data: ModUpdate) => Promise<Mod>;
  deleteMod: (id: number) => Promise<void>;
  uploadMod: (instanceId: number, file: File) => Promise<Mod>;
  clearError: () => void;
}

export const useModsStore = create<ModsState>((set, get) => ({
  mods: [],
  pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchMods: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.listMods(params);
      set({
        mods: response.items,
        pagination: {
          page: response.page,
          pageSize: response.page_size,
          total: response.total,
          totalPages: response.total_pages,
        },
        isLoading: false,
      });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to fetch mods', isLoading: false });
    }
  },

  createMod: async (data: ModCreate) => {
    set({ isLoading: true, error: null });
    try {
      const mod = await api.createMod(data);
      const { mods } = get();
      set({ mods: [mod, ...mods], isLoading: false });
      return mod;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to create mod', isLoading: false });
      throw err;
    }
  },

  updateMod: async (id: number, data: ModUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const mod = await api.updateMod(id, data);
      const { mods } = get();
      set({ mods: mods.map((m) => (m.id === id ? mod : m)), isLoading: false });
      return mod;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to update mod', isLoading: false });
      throw err;
    }
  },

  deleteMod: async (id: number) => {
    set({ isLoading: true, error: null });
    try {
      await api.deleteMod(id);
      const { mods } = get();
      set({ mods: mods.filter((m) => m.id !== id), isLoading: false });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to delete mod', isLoading: false });
      throw err;
    }
  },

  uploadMod: async (instanceId: number, file: File) => {
    set({ isLoading: true, error: null });
    try {
      const mod = await api.uploadMod(instanceId, file);
      const { mods } = get();
      set({ mods: [mod, ...mods], isLoading: false });
      return mod;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to upload mod', isLoading: false });
      throw err;
    }
  },
}));