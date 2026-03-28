/**
 * API client for TransChord backend.
 * Handles all HTTP requests with authentication.
 */
import { getAccessToken } from './auth0';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors.
 */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Fetch with authentication helper.
 * Automatically adds Bearer token to requests.
 */
async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = await getAccessToken();

  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response;
}

/**
 * Job data interface.
 */
export interface Job {
  id: string;
  song_name: string | null;
  original_key: string | null;
  target_key: string | null;
  semitones: number;
  mode: string;
  status: string;
  detected_chords_count: number;
  processing_time_ms: number;
  from_cache: boolean;
  created_at: string;
  completed_at: string | null;
}

/**
 * Get current user's jobs.
 */
export async function getMyJobs(limit = 50, offset = 0): Promise<Job[]> {
  const response = await fetchWithAuth(
    `/api/jobs/my?limit=${limit}&offset=${offset}`
  );
  const data = await response.json();
  return data.jobs;
}

/**
 * Download job result as blob.
 */
export async function downloadJobResult(jobId: string): Promise<Blob> {
  const response = await fetchWithAuth(`/api/results/${jobId}`);
  return await response.blob();
}

/**
 * Delete a job (soft delete).
 */
export async function deleteJob(jobId: string): Promise<void> {
  await fetchWithAuth(`/api/jobs/${jobId}`, {
    method: 'DELETE',
  });
}

/**
 * Upload and process image (authenticated).
 */
export async function processImage(
  image: File,
  semitones: number,
  mode: string,
  songName?: string
): Promise<Response> {
  const formData = new FormData();
  formData.append('image', image);
  formData.append('semitones', semitones.toString());
  formData.append('mode', mode);
  if (songName) {
    formData.append('song_name', songName);
  }

  return await fetchWithAuth('/api/overlay', {
    method: 'POST',
    body: formData,
  });
}
