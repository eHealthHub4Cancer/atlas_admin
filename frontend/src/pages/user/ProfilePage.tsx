import React, { useState, useEffect } from 'react';
import { Card, CardHeader, Button, Input, Select, Badge } from '../../components/ui';
import { useUserProfile, useUpdateProfile } from '../../hooks/useApi';
import { capitalize } from '../../lib/utils';

const prefixOptions = [
  { value: '', label: 'Select prefix' },
  { value: 'Mr.', label: 'Mr.' },
  { value: 'Mrs.', label: 'Mrs.' },
  { value: 'Ms.', label: 'Ms.' },
  { value: 'Dr.', label: 'Dr.' },
  { value: 'Prof.', label: 'Prof.' },
];

export const ProfilePage: React.FC = () => {
  const { data: profile, isLoading } = useUserProfile();
  const updateProfile = useUpdateProfile();

  const [formData, setFormData] = useState({
    display_name: '',
    email: '',
    affiliation: '',
    prefix: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (profile?.profile) {
      setFormData({
        display_name: profile.profile.display_name || '',
        email: profile.profile.email || '',
        affiliation: profile.profile.affiliation || '',
        prefix: profile.profile.prefix || '',
      });
    }
  }, [profile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setHasChanges(true);
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleSelectChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    setHasChanges(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    try {
      await updateProfile.mutateAsync(formData);
      setHasChanges(false);
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

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-48" />
        <Card>
          <div className="space-y-4">
            <div className="skeleton h-10 w-full" />
            <div className="skeleton h-10 w-full" />
            <div className="skeleton h-10 w-full" />
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Profile Settings
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Manage your personal information
        </p>
      </div>

      {/* Account overview card */}
      <Card>
        <CardHeader title="Account Overview" />
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400">Username</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">
              {profile?.username}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400">Role</dt>
            <dd className="mt-1">
              <Badge variant="primary">{capitalize(profile?.role || 'guest')}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500 dark:text-slate-400">Status</dt>
            <dd className="mt-1">
              <Badge variant={profile?.is_disabled ? 'danger' : 'success'}>
                {profile?.is_disabled ? 'Disabled' : 'Active'}
              </Badge>
            </dd>
          </div>
        </dl>
      </Card>

      {/* Edit profile form */}
      <Card>
        <CardHeader
          title="Edit Profile"
          description="Update your personal information below"
        />
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
              placeholder="Your display name"
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
            placeholder="your.email@example.com"
            required
          />

          <Input
            label="Affiliation"
            name="affiliation"
            type="text"
            value={formData.affiliation}
            onChange={handleChange}
            error={errors.affiliation}
            placeholder="Your organization or institution"
          />

          {errors.non_field_errors && (
            <p className="text-sm text-red-500">{errors.non_field_errors}</p>
          )}

          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                if (profile?.profile) {
                  setFormData({
                    display_name: profile.profile.display_name || '',
                    email: profile.profile.email || '',
                    affiliation: profile.profile.affiliation || '',
                    prefix: profile.profile.prefix || '',
                  });
                  setHasChanges(false);
                }
              }}
              disabled={!hasChanges}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={updateProfile.isPending}
              disabled={!hasChanges}
            >
              Save Changes
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
