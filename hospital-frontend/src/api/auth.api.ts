/**
 * Auth API module.
 * Tiêu chí 2: domain logic tách riêng theo feature.
 */
import { apiClient } from './client';
import type { TokenResponse, User } from '@/types';

export interface LoginPayload { username: string; password: string }
export interface RegisterPayload {
  username: string; password: string;
  full_name?: string; role?: string; clinic_room?: string;
}

export const authApi = {
  /** POST /auth/login — OAuth2 form-encoded */
  login: (payload: LoginPayload) =>
    apiClient.post<TokenResponse>('/auth/login', payload, {
      contentType: 'application/x-www-form-urlencoded',
    }),

  /** GET /auth/me */
  me: () => apiClient.get<User>('/auth/me'),

  /** POST /auth/register */
  register: (payload: RegisterPayload) =>
    apiClient.post<User>('/auth/register', payload),
};
