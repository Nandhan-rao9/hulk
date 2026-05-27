import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
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
    api.post<Activity>(`/activities/${id}/approve/`, { note }),
};

// Source Files API
export const sourceFilesApi = {
  list: (params?: Record<string, any>) =>
    api.get<PaginatedResponse<SourceFile>>('/source-files/', { params }),

  get: (id: number) =>
    api.get<SourceFile>(`/source-files/${id}/`),

  upload: (file: File, sourceType: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', sourceType);
    return api.post<SourceFile>('/source-files/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

export default api;
