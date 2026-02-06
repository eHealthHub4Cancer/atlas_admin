from unittest.mock import patch

from contextlib import nullcontext

from django.test import TestCase, SimpleTestCase
from rest_framework.test import APIClient

from .models import Role, User


class SignupSyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('accounts.api_views.sync_user_to_sec')
    @patch('accounts.api_views.grant_role_to_sec')
    def test_signup_api_syncs_user_and_selected_role_to_sec(self, mock_grant_role, mock_sync_user):
        role = Role.objects.create(name='researcher')

        payload = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'display_name': 'New User',
            'role': role.name,
            'prefix': '',
            'category': '',
            'affiliation': 'Test Org',
        }

        response = self.client.post('/api/signup/', payload, format='json')

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='newuser')
        self.assertTrue(user.roles.filter(name='researcher').exists())
        mock_sync_user.assert_called_once_with(user)
        mock_grant_role.assert_called_once_with(user, 'researcher')

    @patch('accounts.api_views.sync_user_to_sec')
    @patch('accounts.api_views.grant_role_to_sec')
    def test_signup_api_syncs_user_without_role_assignment(self, mock_grant_role, mock_sync_user):
        payload = {
            'username': 'basicuser',
            'email': 'basic@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'display_name': 'Basic User',
            'role': '',
            'prefix': '',
            'category': '',
            'affiliation': '',
        }

        response = self.client.post('/api/signup/', payload, format='json')

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='basicuser')
        mock_sync_user.assert_called_once_with(user)
        mock_grant_role.assert_not_called()


class SecSyncFallbackTests(SimpleTestCase):
    @patch('accounts.sec_sync.get_webapi_connection')
    @patch('accounts.sec_sync.transaction.atomic', return_value=nullcontext())
    @patch('accounts.sec_sync.ensure_sec_role', return_value=42)
    @patch('accounts.sec_sync.ensure_sec_user_role_link')
    @patch('accounts.sec_sync._resolve_sec_user_id', return_value=77)
    def test_grant_role_uses_resolved_sec_user_id_without_model_field(
        self,
        mock_resolve_sec_user_id,
        mock_ensure_link,
        mock_ensure_role,
        mock_atomic,
        mock_get_connection,
    ):
        from types import SimpleNamespace
        from accounts.sec_sync import grant_role_to_sec

        mock_conn = mock_get_connection.return_value
        mock_conn.cursor.return_value.__enter__.return_value = object()

        user = SimpleNamespace(username='no_sec_field')
        result = grant_role_to_sec(user, 'researcher')

        self.assertTrue(result)
        mock_resolve_sec_user_id.assert_called_once()
        mock_ensure_role.assert_called_once()
        mock_ensure_link.assert_called_once_with(mock_conn.cursor.return_value.__enter__.return_value, 77, 42)
