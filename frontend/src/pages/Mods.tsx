// Mods Page
import React, { useEffect, useState } from 'react';
import { useModsStore } from '../hooks/useMods';
import { useInstancesStore } from '../hooks/useInstances';
import { useAuthStore } from '../hooks/useAuth';
import { Button, Card, Badge, EmptyState, LoadingSpinner, Modal, Input } from '../components/UI';
import type { ModCreate } from '../types/api';

export const Mods: React.FC = () => {
  const {
    mods,
    pagination,
    isLoading,
    error,
    fetchMods,
    createMod,
    updateMod,
    deleteMod,
    uploadMod,
    clearError,
  } = useModsStore();
  const { instances, fetchInstances } = useInstancesStore();
  const { isAuthenticated } = useAuthStore();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingMod, setEditingMod] = useState<ModCreate & { id: number } | null>(null);
  const [formData, setFormData] = useState<{
    instance_id: number;
    name: string;
    version: string;
    filename: string;
    file_path: string;
    source: string;
    is_enabled: boolean;
  }>({
    instance_id: 0,
    name: '',
    version: '1.0.0',
    filename: '',
    file_path: '',
    source: 'local',
    is_enabled: true,
  });
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [selectedInstanceId, setSelectedInstanceId] = useState<number | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchInstances();
      fetchMods();
    }
  }, [isAuthenticated, fetchInstances, fetchMods]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Convert empty source to undefined
      const submitData = {
        ...formData,
        source: formData.source || undefined,
      };
      if (editingMod) {
        await updateMod(editingMod.id, submitData);
      } else if (uploadFile && selectedInstanceId) {
        await uploadMod(selectedInstanceId, uploadFile);
      } else {
        await createMod(submitData);
      }
      setIsCreateModalOpen(false);
      setEditingMod(null);
      setUploadFile(null);
      resetForm();
    } catch {
      // Error handled in store
    }
  };

  const handleEdit = (mod: ModCreate & { id: number }) => {
    setEditingMod(mod);
    setFormData({
      instance_id: mod.instance_id,
      name: mod.name,
      version: mod.version,
      filename: mod.filename,
      file_path: mod.file_path,
      source: mod.source || '',
      is_enabled: mod.is_enabled ?? true,
    });
    setIsCreateModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (deleteConfirmId === id) {
      try {
        await deleteMod(id);
      } catch {
        // Error handled in store
      }
      setDeleteConfirmId(null);
    } else {
      setDeleteConfirmId(id);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadFile(file);
      setFormData({ ...formData, filename: file.name, name: file.name.replace('.jar', '') });
    }
  };

  const resetForm = () => {
    setFormData({
      instance_id: instances[0]?.id || 0,
      name: '',
      version: '1.0.0',
      filename: '',
      file_path: '',
      source: 'local',
      is_enabled: true,
    });
    setSelectedInstanceId(instances[0]?.id || null);
  };

  const openCreateModal = () => {
    resetForm();
    setEditingMod(null);
    setUploadFile(null);
    setIsCreateModalOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Mods</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage mods for your instances</p>
        </div>
        <Button onClick={openCreateModal}>
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Mod
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 flex items-center justify-between">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={clearError}>Dismiss</Button>
        </div>
      )}

      {isLoading && mods.length === 0 ? (
        <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>
      ) : mods.length === 0 ? (
        <EmptyState
          icon={<svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>}
          title="No mods yet"
          description="Add mods to your instances by uploading .jar files or adding them manually"
          action={<Button onClick={openCreateModal}>Add Mod</Button>}
        />
      ) : (
        <div className="space-y-3">
          {mods.map((mod) => (
            <Card key={mod.id} className="p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <span className="text-3xl">🧩</span>
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">{mod.name}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    v{mod.version} • {mod.filename}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <Badge variant={mod.is_enabled ? 'success' : 'default'}>
                  {mod.is_enabled ? 'Enabled' : 'Disabled'}
                </Badge>
                <Badge variant="info">{mod.source?.toUpperCase() || 'LOCAL'}</Badge>
                <Button variant="secondary" size="sm" onClick={() => handleEdit(mod as ModCreate & { id: number })}>Edit</Button>
                <Button
                  variant={deleteConfirmId === mod.id ? 'danger' : 'ghost'}
                  size="sm"
                  onClick={() => handleDelete(mod.id)}
                >
                  {deleteConfirmId === mod.id ? 'Confirm' : 'Delete'}
                </Button>
              </div>
            </Card>
          ))}

          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button variant="secondary" size="sm" onClick={() => fetchMods({ page: pagination.page - 1 })} disabled={pagination.page <= 1}>Previous</Button>
              <span className="text-sm text-gray-600 dark:text-gray-400">Page {pagination.page} of {pagination.totalPages} ({pagination.total} total)</span>
              <Button variant="secondary" size="sm" onClick={() => fetchMods({ page: pagination.page + 1 })} disabled={pagination.page >= pagination.totalPages}>Next</Button>
            </div>
          )}
        </div>
      )}

      <Modal isOpen={isCreateModalOpen} onClose={() => { setIsCreateModalOpen(false); resetForm(); setEditingMod(null); setUploadFile(null); }} title={editingMod ? 'Edit Mod' : uploadFile ? 'Upload Mod' : 'Add Mod'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Instance</label>
            <select
              value={formData.instance_id}
              onChange={(e) => { setFormData({ ...formData, instance_id: parseInt(e.target.value) }); setSelectedInstanceId(parseInt(e.target.value)); }}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {instances.map((inst) => (
                <option key={inst.id} value={inst.id}>{inst.name} (MC {inst.minecraft_version})</option>
              ))}
            </select>
          </div>

          {!uploadFile && !editingMod && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Upload .jar file</label>
              <input
                type="file"
                accept=".jar"
                onChange={handleFileChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-900/30 dark:file:text-blue-400"
              />
            </div>
          )}

          {(!uploadFile || editingMod) && (
            <>
              <Input label="Name" value={formData.name} onChange={(v) => setFormData({ ...formData, name: v })} required placeholder="Mod Name" />
              <Input label="Version" value={formData.version} onChange={(v) => setFormData({ ...formData, version: v })} required placeholder="1.0.0" />
              <Input label="Filename" value={formData.filename} onChange={(v) => setFormData({ ...formData, filename: v })} required placeholder="mod.jar" />
              {!uploadFile && <Input label="File Path" value={formData.file_path} onChange={(v) => setFormData({ ...formData, file_path: v })} required placeholder="/path/to/mod.jar" />}
              <Input label="Source" value={formData.source} onChange={(v) => setFormData({ ...formData, source: v })} placeholder="curseforge, modrinth, local" />
            </>
          )}

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_enabled"
              checked={formData.is_enabled}
              onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="is_enabled" className="text-sm text-gray-700 dark:text-gray-300">Enabled</label>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="secondary" onClick={() => { setIsCreateModalOpen(false); resetForm(); setEditingMod(null); setUploadFile(null); }}>Cancel</Button>
            <Button type="submit" disabled={isLoading}>{isLoading ? 'Saving...' : (editingMod ? 'Update' : (uploadFile ? 'Upload' : 'Add'))}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};