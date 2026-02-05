import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { EyeIcon, EyeSlashIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';
import { AuthLayout } from '../../components/layout';
import { Button, Input, Badge } from '../../components/ui';
import { authApi } from '../../lib/api';
import { useAuthStore } from '../../store/auth';
import { toast } from '../../store/toast';

export const AdminLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { fetchSession } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
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
      const result = await authApi.adminLogin(formData);
      if (result.success) {
        await fetchSession();
        toast.success('Welcome, Admin!', 'You have been logged in successfully.');
        navigate(result.redirect || '/admin');
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
      title="Admin Console"
      subtitle="Sign in to the administration dashboard"
    >
      <div className="mb-6 flex justify-center">
        <Badge variant="warning" className="gap-2 px-3 py-2">
          <ShieldCheckIcon className="h-4 w-4" />
          Authorized Personnel Only
        </Badge>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          label="Email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          error={errors.email}
          placeholder="admin@example.com"
          autoComplete="email"
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
          Sign in as Admin
        </Button>

        <p className="text-center text-sm text-slate-600 dark:text-slate-400">
          Not an admin?{' '}
          <Link to="/login" className="link font-medium">
            User Login
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
};
