import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { AuthLayout } from '../../components/layout';
import { Button, Input, Select } from '../../components/ui';
import { authApi } from '../../lib/api';
import { toast } from '../../store/toast';

const prefixOptions = [
  { value: '', label: 'Select prefix' },
  { value: 'Mr.', label: 'Mr.' },
  { value: 'Mrs.', label: 'Mrs.' },
  { value: 'Ms.', label: 'Ms.' },
  { value: 'Dr.', label: 'Dr.' },
  { value: 'Prof.', label: 'Prof.' },
];

const roleOptions = [
  { value: 'guest', label: 'Guest' },
  { value: 'researcher', label: 'Researcher' },
  { value: 'student', label: 'Student' },
];

export const SignupPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    display_name: '',
    email: '',
    affiliation: '',
    prefix: '',
    role: 'guest',
    password1: '',
    password2: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleSelectChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrors({});

    // Client-side validation
    const newErrors: Record<string, string> = {};
    if (formData.password1.length < 8) {
      newErrors.password1 = 'Password must be at least 8 characters';
    }
    if (formData.password1 !== formData.password2) {
      newErrors.password2 = 'Passwords do not match';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setIsLoading(false);
      return;
    }

    try {
      const result = await authApi.signup(formData);
      if (result.success) {
        toast.success('Account created!', 'Please sign in with your credentials.');
        navigate('/login');
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
        toast.error('Signup failed', err.message || 'Please check your information');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Join Atlas Research Platform"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Prefix"
            options={prefixOptions}
            value={formData.prefix}
            onChange={(value) => handleSelectChange('prefix', value)}
            error={errors.prefix}
          />
          <Input
            label="Display Name"
            name="display_name"
            type="text"
            value={formData.display_name}
            onChange={handleChange}
            error={errors.display_name}
            placeholder="Your name"
            required
          />
        </div>

        <Input
          label="Email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          error={errors.email}
          placeholder="you@example.com"
          autoComplete="email"
          required
        />

        <Input
          label="Username"
          name="username"
          type="text"
          value={formData.username}
          onChange={handleChange}
          error={errors.username}
          placeholder="Choose a username"
          autoComplete="username"
          required
        />

        <Input
          label="Affiliation"
          name="affiliation"
          type="text"
          value={formData.affiliation}
          onChange={handleChange}
          error={errors.affiliation}
          placeholder="Organization (optional)"
        />

        <Select
          label="Role"
          options={roleOptions}
          value={formData.role}
          onChange={(value) => handleSelectChange('role', value)}
          error={errors.role}
        />

        <Input
          label="Password"
          name="password1"
          type={showPassword ? 'text' : 'password'}
          value={formData.password1}
          onChange={handleChange}
          error={errors.password1}
          placeholder="At least 8 characters"
          autoComplete="new-password"
          required
          hint="Must be at least 8 characters"
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

        <Input
          label="Confirm Password"
          name="password2"
          type={showPassword ? 'text' : 'password'}
          value={formData.password2}
          onChange={handleChange}
          error={errors.password2}
          placeholder="Confirm your password"
          autoComplete="new-password"
          required
        />

        {errors.non_field_errors && (
          <p className="text-sm text-red-500">{errors.non_field_errors}</p>
        )}

        <Button
          type="submit"
          variant="primary"
          className="w-full"
          isLoading={isLoading}
        >
          Create account
        </Button>

        <p className="text-center text-sm text-slate-600 dark:text-slate-400">
          Already have an account?{' '}
          <Link to="/login" className="link font-medium">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
};
