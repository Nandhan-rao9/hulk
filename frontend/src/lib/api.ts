import axios from 'axios';

// Helper to get CSRF token from cookie
function getCsrfToken(): string | null {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split('=');
    if (key === name) {
      return decodeURIComponent(value);
    }
  }
  return null;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add CSRF token to all requests
api.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

export interface Activity {
  id: number;
  source_file_name: string;
  source_type: string;
  facility: number | null;
  facility_name: string | null;
  scope: number;
  category: string;
  period_start: string | null;
  period_end: string;
  emissions_kgco2e: number | null;
  status: string;
  is_suspicious: boolean;
  flag_reason: string | null;
  is_cross_month: boolean;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  created_at: string;
  sap_detail: any | null;
  utility_detail: any | null;
  travel_detail: any | null;
}

export interface SourceFile {
  id: number;
  org: number;
  org_name: string;
  source_type: string;
  original_filename: string;
  file_hash: string;
  uploaded_by: number;
  uploaded_by_name: string;
  uploaded_at: string;
  status: string;
  total_rows: number | null;
  failed_rows: number | null;
  flagged_rows: number | null;
  pending_rows: number | null;
  approved_rows: number | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Activities API
export const activitiesApi = {
  list: (params?: Record<string, any>) =>
    api.get<PaginatedResponse<Activity>>('/activities/', { params }),

  get: (id: number) =>
    api.get<Activity>(`/activities/${id}/`),

  approve: (id: number, note?: string) =>
    api.post<{ message: string; activity: Activity }>(`/activities/${id}/approve/`, { note }),

  flag: (id: number, reason: string, note?: string) =>
    api.post<Activity>(`/activities/${id}/flag/`, { reason, note }),

  unflag: (id: number, note?: string) =>
    api.post<Activity>(`/activities/${id}/unflag/`, { note }),
};

export interface FileActivity {
  id: number;
  scope: number;
  category: string;
  period_end: string;
  facility_name: string | null;
  emissions_kgco2e: number;
  metric_label: string;
  metric_value: number;
  metric_unit: string;
  material?: string;
  service_number?: string;
  mode?: string;
  employee_id?: string;
  cabin_class?: string;
  distance_km?: number;
  nights?: number;
}

export interface FileActivitiesResponse {
  source_file_id: number;
  filename: string;
  source_type: string;
  total_approved: number;
  activities: FileActivity[];
}

export interface FileSummaryResponse {
  source_file_id: number;
  source_type: string;
  status_counts: Record<string, number>;
  emissions_total_kgco2e: number;
  metrics: {
    total_quantity_normalized?: number;
    unit_distribution?: Record<string, number>;
    material_breakdown?: Array<{material: string; quantity: number; unit: string}>;
    total_kwh?: number;
    total_distance_km?: number;
    mode_breakdown?: Record<string, number>;
  };
}

export interface LookupUploadResponse {
  status: 'success' | 'error';
  total_rows: number;
  created: number;
  updated: number;
  skipped: number;
  errors: Array<{row: number; field: string; error: string}>;
}

// Source Files API
export const sourceFilesApi = {
  list: (params?: Record<string, any>) =>
    api.get<PaginatedResponse<SourceFile>>('/source-files/', { params }),

  get: (id: number) =>
    api.get<SourceFile>(`/source-files/${id}/`),

  getActivities: (id: number) =>
    api.get<FileActivitiesResponse>(`/source-files/${id}/activities/`),

  getSummary: (id: number) =>
    api.get<FileSummaryResponse>(`/source-files/${id}/summary/`),

  delete: (id: number) =>
    api.delete(`/source-files/${id}/`),

  upload: (file: File, sourceType: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', sourceType);
    return api.post<SourceFile>('/source-files/upload/', formData, {
      headers: {
        'Content-Type': undefined,  // Let Axios auto-detect FormData and set boundary
      },
    });
  },
};

// Lookups API (Admin only)
export const lookupsApi = {
  uploadPlantLookup: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<LookupUploadResponse>('/lookups/plant/upload/', formData, {
      headers: {
        'Content-Type': undefined,
      },
    });
  },

  uploadMaterialMapping: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<LookupUploadResponse>('/lookups/material-mapping/upload/', formData, {
      headers: {
        'Content-Type': undefined,
      },
    });
  },
};

export default api;
