// API Client
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { Token, User, Instance, InstanceCreate, InstanceUpdate, InstanceListResponse, Mod, ModCreate, ModUpdate, ModListResponse, HealthResponse } from '../types/api';

declare global {
  interface ImportMetaEnv {
    readonly VITE_API_URL: string;
  }
  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshPromise: Promise<string> | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Important for cookies
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (this.accessToken && config.headers) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          try {
            const newToken = await this.refreshToken();
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
            }
            return this.client(originalRequest);
          } catch {
            this.clearToken();
            window.location.href = '/login';
            return Promise.reject(error);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  setToken(token: string | null) {
    this.accessToken = token;
  }

  clearToken() {
    this.accessToken = null;
  }

  getToken(): string | null {
    return this.accessToken;
  }

  async refreshToken(): Promise<string> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        const response = await axios.post<Token>(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        this.accessToken = response.data.access_token;
        return this.accessToken;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  // Health
  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  // Auth
  async register(email: string, password: string, full_name?: string): Promise<User> {
    const response = await this.client.post<User>('/auth/register', { email, password, full_name });
    return response.data;
  }

  async login(email: string, password: string): Promise<Token> {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    const response = await this.client.post<Token>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    this.accessToken = response.data.access_token;
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    this.clearToken();
  }

  async getMe(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  async updateMe(data: { full_name?: string; password?: string }): Promise<User> {
    const response = await this.client.patch<User>('/auth/me', data);
    return response.data;
  }

  // Instances
  async listInstances(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    loader?: string;
  }): Promise<InstanceListResponse> {
    const response = await this.client.get<InstanceListResponse>('/instances', { params });
    return response.data;
  }

  async getInstance(id: number): Promise<Instance> {
    const response = await this.client.get<Instance>(`/instances/${id}`);
    return response.data;
  }

  async createInstance(data: InstanceCreate): Promise<Instance> {
    const response = await this.client.post<Instance>('/instances', data);
    return response.data;
  }

  async updateInstance(id: number, data: InstanceUpdate): Promise<Instance> {
    const response = await this.client.patch<Instance>(`/instances/${id}`, data);
    return response.data;
  }

  async deleteInstance(id: number): Promise<void> {
    await this.client.delete(`/instances/${id}`);
  }

  // Mods
  async listMods(params?: {
    instance_id?: number;
    page?: number;
    page_size?: number;
    enabled_only?: boolean;
  }): Promise<ModListResponse> {
    const response = await this.client.get<ModListResponse>('/mods', { params });
    return response.data;
  }

  async getMod(id: number): Promise<Mod> {
    const response = await this.client.get<Mod>(`/mods/${id}`);
    return response.data;
  }

  async createMod(data: ModCreate): Promise<Mod> {
    const response = await this.client.post<Mod>('/mods', data);
    return response.data;
  }

  async updateMod(id: number, data: ModUpdate): Promise<Mod> {
    const response = await this.client.patch<Mod>(`/mods/${id}`, data);
    return response.data;
  }

  async deleteMod(id: number): Promise<void> {
    await this.client.delete(`/mods/${id}`);
  }

  async uploadMod(instanceId: number, file: File): Promise<Mod> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post<Mod>(`/mods/upload?instance_id=${instanceId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }
}

export const api = new ApiClient();