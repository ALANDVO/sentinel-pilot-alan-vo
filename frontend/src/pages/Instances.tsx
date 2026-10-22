import React, { useEffect, useState } from 'react';
import { useInstancesStore } from '../hooks/useInstances';
import { useAuthStore } from '../hooks/useAuth';
import { Button, Card, Badge, EmptyState, LoadingSpinner, Modal, Input } from '../components/UI';
import type { Instance } from '../types/api';

const LoaderIcons: Record<string, string> = {
  vanilla: '🎮',
  forge: '⚙️',
  fabric: '🧵',
  quilt: '🧶',
};

export const Instances: React.FC = () => {
  const {
    instances,
    pagination,
    isLoading,
    error,
    fetchInstances,
    createInstance,
    updateInstance,
    deleteInstance,
    setCurrentInstance,
    clearError,
  } = useInstancesStore();
  const { isAuthenticated } = useAuthStore();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingInstance, setEditingInstance] = useState<Instance | null>(null);
  const [formData, setFormData] = useState<{
    name: string;
    minecraft_version: string;
    loader: string;
    loader_version: string;
    memory_max: string;
  }>({
    name: '',
    minecraft_version: '1.20.1',
    loader: 'fabric',
    loader_version: '',
    memory_max: '4G',
  });
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchInstances();
    }
  }, [isAuthenticated, fetchInstances]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Convert empty strings to undefined for optional fields
      const submitData = {
        ...formData,
        loader: formData.loader || undefined,
        loader_version: formData.loader_version || undefined,
        memory_max: formData.memory_max || undefined,
      };
      if (editingInstance) {
        await updateInstance(editingInstance.id, submitData);
      } else {
        await createInstance(submitData);
      }
      setIsCreateModalOpen(false);
      setEditingInstance(null);
      resetForm();
    } catch {
      // Error handled in store
    }
  };

  const handleEdit = (instance: Instance) => {
    setEditingInstance(instance);
    setFormData({
      name: instance.name,
      minecraft_version: instance.minecraft_version,
      loader: instance.loader || '',
      loader_version: instance.loader_version || '',
      memory_max: instance.memory_max || '',
    });
    setIsCreateModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (deleteConfirmId === id) {
      try {
        await deleteInstance(id);
      } catch {
        // Error handled in store
      }
      setDeleteConfirmId(null);
    } else {
      setDeleteConfirmId(id);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      minecraft_version: '1.20.1',
      loader: 'fabric',
      loader_version: '',
      memory_max: '4G',
    });
  };

  const openCreateModal = () => {
    resetForm();
    setEditingInstance(null);
    setIsCreateModalOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Instances</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage your Minecraft instances</p>
        </div>
        <Button onClick={openCreateModal}>
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Instance
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 flex items-center justify-between">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={clearError}>
            Dismiss
          </Button>
        </div>
      )}

      {isLoading && instances.length === 0 ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : instances.length === 0 ? (
        <EmptyState
          icon={<svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>}
          title="No instances yet"
          description="Create your first Minecraft instance to get started"
          action={<Button onClick={openCreateModal}>Create Instance</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {instances.map((instance) => (
            <Card key={instance.id} className="p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{LoaderIcons[instance.loader || 'vanilla'] || '🎮'}</span>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">{instance.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      MC {instance.minecraft_version}
                      {instance.loader && ` • ${instance.loader} ${instance.loader_version || ''}`}
                    </p>
                  </div>
                </div>
                <Badge variant={instance.is_active ? 'success' : 'default'}>
                  {instance.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>

              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400 mb-4">
                {instance.memory_max && (
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>
                    <span>{instance.memory_max}</span>
                  </div>
                )}
                {instance.mods_count > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🧩</span>
                    <span>{instance.mods_count} mods</span>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" className="flex-1" onClick={() => setCurrentInstance(instance)}>
                  View Details
                </Button>
                <Button variant="secondary" size="sm" className="flex-1" onClick={() => handleEdit(instance)}>
                  Edit
                </Button>
                <Button
                  variant={deleteConfirmId === instance.id ? 'danger' : 'ghost'}
                  size="sm"
                  onClick={() => handleDelete(instance.id)}
                >
                  {deleteConfirmId === instance.id ? 'Confirm' : 'Delete'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {instances.length > 0 && pagination.totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchInstances({ page: pagination.page - 1 })}
            disabled={pagination.page <= 1}
          >
            Previous
          </Button>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Page {pagination.page} of {pagination.totalPages} ({pagination.total} total)
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchInstances({ page: pagination.page + 1 })}
            disabled={pagination.page >= pagination.totalPages}
          >
            Next
          </Button>
        </div>
      )}

      <Modal isOpen={isCreateModalOpen} onClose={() => { setIsCreateModalOpen(false); resetForm(); setEditingInstance(null); }} title={editingInstance ? 'Edit Instance' : 'Create Instance'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Name" value={formData.name} onChange={(v) => setFormData({ ...formData, name: v })} required placeholder="My Survival World" />
          <Input label="Minecraft Version" value={formData.minecraft_version} onChange={(v) => setFormData({ ...formData, minecraft_version: v })} required placeholder="1.20.1" />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Loader</label>
            <select
              value={formData.loader}
              onChange={(e) => setFormData({ ...formData, loader: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="vanilla">Vanilla</option>
              <option value="forge">Forge</option>
              <option value="fabric">Fabric</option>
              <option value="quilt">Quilt</option>
            </select>
          </div>
          <Input label="Loader Version (optional)" value={formData.loader_version} onChange={(v) => setFormData({ ...formData, loader_version: v })} placeholder="0.15.11" />
          <Input label="Max Memory" value={formData.memory_max} onChange={(v) => setFormData({ ...formData, memory_max: v })} placeholder="4G" />
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="secondary" onClick={() => { setIsCreateModalOpen(false); resetForm(); setEditingInstance(null); }}>Cancel</Button>
            <Button type="submit" disabled={isLoading}>{isLoading ? 'Saving...' : (editingInstance ? 'Update' : 'Create')}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};