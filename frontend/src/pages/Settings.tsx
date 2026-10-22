// Settings Page
import React, { useState } from 'react';
import { useAuthStore } from '../hooks/useAuth';
import { useThemeStore } from '../hooks/useTheme';
import { Button, Input, Card } from '../components/UI';

export const Settings: React.FC = () => {
  const { user, updateMe, isLoading } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [password, setPassword] = useState('');
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess('');
    setError('');
    try {
      await updateMe({
        full_name: fullName || undefined,
        password: password || undefined,
      });
      setSuccess('Profile updated successfully');
      setPassword('');
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      setError(errorObj.response?.data?.detail || 'Failed to update profile');
    }
  };

  const handleThemeChange = (newTheme: 'light' | 'dark') => {
    setTheme(newTheme);
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400">Manage your account and preferences</p>
      </div>

      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Profile</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {success && (
            <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 text-sm">
              {success}
            </div>
          )}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
              {error}
            </div>
          )}

          <Input label="Full Name" value={fullName} onChange={setFullName} placeholder="John Doe" />
          <Input label="Email" value={email} onChange={setEmail} type="email" disabled />
          <Input label="New Password (leave blank to keep current)" value={password} onChange={setPassword} type="password" placeholder="••••••••" />
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Password must be at least 8 characters
          </div>
          <Button type="submit" disabled={isLoading} className="w-full sm:w-auto">
            {isLoading ? 'Saving...' : 'Save Changes'}
          </Button>
        </form>
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Appearance</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Theme</label>
            <div className="flex gap-4">
              {(['light', 'dark'] as const).map((t) => (
                <label
                  key={t}
                  className={`flex-1 p-4 border-2 rounded-xl cursor-pointer transition-all ${
                    theme === t
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <input
                    type="radio"
                    name="theme"
                    value={t}
                    checked={theme === t}
                    onChange={() => handleThemeChange(t)}
                    className="sr-only"
                  />
                  <div className="flex items-center justify-center gap-3">
                    <span className="text-3xl">{t === 'dark' ? '🌙' : '☀️'}</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">{t}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">About</h2>
        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p><strong>Sentinel Pilot</strong> v1.0.0</p>
          <p>A Minecraft launcher management tool</p>
          <p className="mt-2">
            Built with React, TypeScript, FastAPI, and SQLite
          </p>
        </div>
      </Card>
    </div>
  );
};