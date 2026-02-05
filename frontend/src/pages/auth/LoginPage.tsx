import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { AuthLayout } from '../../components/layout';
import { Button, Input } from '../../components/ui';
import { authApi } from '../../lib/api';
import { useAuthStore } from '../../store/auth';
import { toast } from '../../store/toast';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { fetchSession } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    try {
      const result = await authApi.login({
        username: formData.username.trim(),
        password: formData.password,
      });
      if (result.success) {
        await fetchSession();
        toast.success('Welcome back!', 'You have been logged in successfully.');
        navigate(result.redirect || '/user');
      }
    } catch (error: unknown) {
      const err = error as { message?: string; errors?: Record<string, string[]> };
      if (err.errors) {
        const fieldErrors: Record<string, string> = {};
        Object.entries(err.errors).forEach(([key, messages]) => {
          fieldErrors[key] = messages[0];
        });
        setErrors(fieldErrors);
      } else {
        toast.error('Login failed', err.message || 'Invalid credentials');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your Atlas account"
      showAdminLink
      maxWidthClassName="max-w-sm"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          label="Username or email"
          name="username"
          type="text"
          value={formData.username}
          onChange={handleChange}
          error={errors.username}
          placeholder="Enter your username or email"
          autoComplete="username"
          required
        />

        <div>
          <Input
            label="Password"
            name="password"
            type={showPassword ? 'text' : 'password'}
            value={formData.password}
            onChange={handleChange}
            error={errors.password}
            placeholder="Enter your password"
            autoComplete="current-password"
            required
            rightIcon={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="focus:outline-none"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeSlashIcon className="h-5 w-5" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
              </button>
            }
          />
        </div>

        {errors.non_field_errors && (
          <p className="text-sm text-red-500">{errors.non_field_errors}</p>
        )}

        <Button
          type="submit"
          variant="primary"
          className="w-full"
          isLoading={isLoading}
        >
          Sign in
        </Button>

        <p className="text-center text-sm text-slate-600 dark:text-slate-400">
          Don't have an account?{' '}
          <Link to="/signup" className="link font-medium">
            Sign up
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
};
