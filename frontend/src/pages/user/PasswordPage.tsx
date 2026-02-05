import React, { useState } from 'react';
import { EyeIcon, EyeSlashIcon, KeyIcon } from '@heroicons/react/24/outline';
import { Card, CardHeader, Button, Input } from '../../components/ui';
import { useChangePassword } from '../../hooks/useApi';

export const PasswordPage: React.FC = () => {
  const changePassword = useChangePassword();
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [formData, setFormData] = useState({
    current_password: '',
    new_password1: '',
    new_password2: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const togglePassword = (field: 'current' | 'new' | 'confirm') => {
    setShowPasswords((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Client-side validation
    const newErrors: Record<string, string> = {};
    if (formData.new_password1.length < 8) {
      newErrors.new_password1 = 'Password must be at least 8 characters';
    }
    if (formData.new_password1 !== formData.new_password2) {
      newErrors.new_password2 = 'Passwords do not match';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      await changePassword.mutateAsync(formData);
      // Reset form on success
      setFormData({
        current_password: '',
        new_password1: '',
        new_password2: '',
      });
    } catch (error: unknown) {
      const err = error as { errors?: Record<string, string[]> };
      if (err.errors) {
        const fieldErrors: Record<string, string> = {};
        Object.entries(err.errors).forEach(([key, messages]) => {
          fieldErrors[key] = messages[0];
        });
        setErrors(fieldErrors);
      }
    }
  };

  const PasswordToggleButton = ({ field, show }: { field: 'current' | 'new' | 'confirm'; show: boolean }) => (
    <button
      type="button"
      onClick={() => togglePassword(field)}
      className="focus:outline-none"
      tabIndex={-1}
    >
      {show ? (
        <EyeSlashIcon className="h-5 w-5" />
      ) : (
        <EyeIcon className="h-5 w-5" />
      )}
    </button>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Change Password
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Update your account password
        </p>
      </div>

      <Card className="max-w-xl">
        <CardHeader
          title="Update Password"
          description="Choose a strong password with at least 8 characters"
        />

        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            label="Current Password"
            name="current_password"
            type={showPasswords.current ? 'text' : 'password'}
            value={formData.current_password}
            onChange={handleChange}
            error={errors.current_password}
            placeholder="Enter your current password"
            autoComplete="current-password"
            required
            rightIcon={<PasswordToggleButton field="current" show={showPasswords.current} />}
          />

          <Input
            label="New Password"
            name="new_password1"
            type={showPasswords.new ? 'text' : 'password'}
            value={formData.new_password1}
            onChange={handleChange}
            error={errors.new_password1}
            placeholder="Enter your new password"
            autoComplete="new-password"
            required
            hint="Must be at least 8 characters"
            rightIcon={<PasswordToggleButton field="new" show={showPasswords.new} />}
          />

          <Input
            label="Confirm New Password"
            name="new_password2"
            type={showPasswords.confirm ? 'text' : 'password'}
            value={formData.new_password2}
            onChange={handleChange}
            error={errors.new_password2}
            placeholder="Confirm your new password"
            autoComplete="new-password"
            required
            rightIcon={<PasswordToggleButton field="confirm" show={showPasswords.confirm} />}
          />

          {errors.non_field_errors && (
            <p className="text-sm text-red-500">{errors.non_field_errors}</p>
          )}

          <Button
            type="submit"
            variant="primary"
            isLoading={changePassword.isPending}
            leftIcon={<KeyIcon className="h-4 w-4" />}
          >
            Update Password
          </Button>
        </form>
      </Card>

      {/* Security tips */}
      <Card className="max-w-xl bg-slate-50 dark:bg-dark-elevated">
        <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 mb-3">
          Password Security Tips
        </h3>
        <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
          <li className="flex items-start gap-2">
            <span className="text-brand-500">•</span>
            Use a unique password that you don't use elsewhere
          </li>
          <li className="flex items-start gap-2">
            <span className="text-brand-500">•</span>
            Include a mix of letters, numbers, and symbols
          </li>
          <li className="flex items-start gap-2">
            <span className="text-brand-500">•</span>
            Avoid common words or easily guessable information
          </li>
          <li className="flex items-start gap-2">
            <span className="text-brand-500">•</span>
            Consider using a password manager
          </li>
        </ul>
      </Card>
    </div>
  );
};
