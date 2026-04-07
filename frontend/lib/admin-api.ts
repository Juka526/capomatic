/**
 * Admin API endpoints.
 * All endpoints require admin role.
 */
import { getAccessToken } from './auth0';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAdminData(url: string) {
  const token = await getAccessToken();

  const response = await fetch(`${API_URL}${url}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Request failed');
  }

  return await response.json();
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
  last_login: string | null;
}

export async function getAllUsers(): Promise<AdminUser[]> {
  const data = await fetchAdminData('/api/admin/users');
  return data.users || [];
}
