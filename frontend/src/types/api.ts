// API Types
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  role: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Instance {
  id: number;
  name: string;
  minecraft_version: string;
  loader: string | null;
  loader_version: string | null;
  java_path: string | null;
  jvm_args: string | null;
  memory_min: string | null;
  memory_max: string | null;
  game_dir: string | null;
  icon_path: string | null;
  description: string | null;
  is_active: boolean;
  owner_id: number;
  created_at: string;
  updated_at: string | null;
  mods_count: number;
}

export interface InstanceCreate {
  name: string;
  minecraft_version: string;
  loader?: string;
  loader_version?: string;
  java_path?: string;
  jvm_args?: string;
  memory_min?: string;
  memory_max?: string;
  game_dir?: string;
  icon_path?: string;
  description?: string;
}

export interface InstanceUpdate {
  name?: string;
  minecraft_version?: string;
  loader?: string;
  loader_version?: string;
  java_path?: string;
  jvm_args?: string;
  memory_min?: string;
  memory_max?: string;
  game_dir?: string;
  icon_path?: string;
  description?: string;
  is_active?: boolean;
}

export interface InstanceListResponse {
  items: Instance[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Mod {
  id: number;
  name: string;
  version: string;
  filename: string;
  file_path: string;
  file_hash: string | null;
  source: string | null;
  source_url: string | null;
  description: string | null;
  is_enabled: boolean;
  instance_id: number;
  created_at: string;
  updated_at: string | null;
}

export interface ModCreate {
  instance_id: number;
  name: string;
  version: string;
  filename: string;
  file_path: string;
  file_hash?: string;
  source?: string;
  source_url?: string;
  description?: string;
  is_enabled?: boolean;
}

export interface ModUpdate {
  name?: string;
  version?: string;
  description?: string;
  is_enabled?: boolean;
}

export interface ModListResponse {
  items: Mod[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
}