// Register Page
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../hooks/useAuth';
import { Button, Input, Card } from '../components/UI';

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const { register, error, clearError, isLoading } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (password !== confirmPassword) {
      return;
    }

    try {
      await register(email, password, fullName || undefined);
      navigate('/instances');
    } catch {
      // Error handled in store
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center px-4">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <Link to="/instances" className="inline-flex items-center gap-2 mb-6">
            <span className="text-3xl">🛡️</span>
            <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">Sentinel Pilot</span>
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Create account</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Start managing your Minecraft instances</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
              {error}
            </div>
          )}

          <Input
            label="Full Name (optional)"
            type="text"
            value={fullName}
            onChange={setFullName}
            placeholder="John Doe"
            autoComplete="name"
          />

          <Input
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="you@example.com"
            required
            autoComplete="email"
          />

          <Input
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••••"
            required
            autoComplete="new-password"
          />

          <Input
            label="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={setConfirmPassword}
            placeholder="••••••••"
            required
            autoComplete="new-password"
          />

          <Button type="submit" className="w-full" disabled={isLoading} size="lg">
            {isLoading ? 'Creating account...' : 'Create account'}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:text-blue-500 font-medium">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
};