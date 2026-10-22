// Instances Hook
import { create } from 'zustand';
import type { Instance, InstanceCreate, InstanceUpdate } from '../types/api';
import { api } from '../api/client';

interface InstancesState {
  instances: Instance[];
  currentInstance: Instance | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  isLoading: boolean;
  error: string | null;
  fetchInstances: (params?: { page?: number; page_size?: number; search?: string; loader?: string }) => Promise<void>;
  fetchInstance: (id: number) => Promise<void>;
  createInstance: (data: InstanceCreate) => Promise<Instance>;
  updateInstance: (id: number, data: InstanceUpdate) => Promise<Instance>;
  deleteInstance: (id: number) => Promise<void>;
  clearError: () => void;
  setCurrentInstance: (instance: Instance | null) => void;
}

export const useInstancesStore = create<InstancesState>((set, get) => ({
  instances: [],
  currentInstance: null,
  pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  setCurrentInstance: (instance) => set({ currentInstance: instance }),

  fetchInstances: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.listInstances(params);
      set({
        instances: response.items,
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
      set({ error: error.response?.data?.detail || 'Failed to fetch instances', isLoading: false });
    }
  },

  fetchInstance: async (id: number) => {
    set({ isLoading: true, error: null });
    try {
      const instance = await api.getInstance(id);
      set({ currentInstance: instance, isLoading: false });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to fetch instance', isLoading: false });
    }
  },

  createInstance: async (data: InstanceCreate) => {
    set({ isLoading: true, error: null });
    try {
      const instance = await api.createInstance(data);
      const { instances } = get();
      set({ instances: [instance, ...instances], isLoading: false });
      return instance;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to create instance', isLoading: false });
      throw err;
    }
  },

  updateInstance: async (id: number, data: InstanceUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const instance = await api.updateInstance(id, data);
      const { instances } = get();
      set({
        instances: instances.map((i) => (i.id === id ? instance : i)),
        currentInstance: instance,
        isLoading: false,
      });
      return instance;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to update instance', isLoading: false });
      throw err;
    }
  },

  deleteInstance: async (id: number) => {
    set({ isLoading: true, error: null });
    try {
      await api.deleteInstance(id);
      const { instances } = get();
      set({
        instances: instances.filter((i) => i.id !== id),
        currentInstance: get().currentInstance?.id === id ? null : get().currentInstance,
        isLoading: false,
      });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      set({ error: error.response?.data?.detail || 'Failed to delete instance', isLoading: false });
      throw err;
    }
  },
}));