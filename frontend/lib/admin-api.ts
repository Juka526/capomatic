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

export interface AdminStats {
  total_users: number;
  total_jobs: number;
  total_cached: number;
  cache_hit_rate: number;
  avg_processing_time: number;
}

export interface PopularSong {
  song_name: string;
  original_key: string | null;
  target_key: string | null;
  semitones: number;
  request_count: number;
  unique_users: number;
  last_requested: string;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
  last_login: string | null;
}

export async function getAdminStats(): Promise<AdminStats> {
  return fetchAdminData('/api/admin/stats');
}

export async function getPopularSongs(limit = 20): Promise<PopularSong[]> {
  const data = await fetchAdminData(`/api/admin/popular?limit=${limit}`);
  return data.songs || [];
}

export async function getAllUsers(): Promise<AdminUser[]> {
  const data = await fetchAdminData('/api/admin/users');
  return data.users || [];
}
