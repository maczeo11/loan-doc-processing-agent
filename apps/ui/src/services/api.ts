import type {
  LoanApplicationState,
  CreateApplicationRequest,
  CreateApplicationResponse,
  ProcessApplicationResponse,
  DocumentUploadResponse,
  JobStatusResponse,
  ReviewDecisionRequest,
  ReviewDecisionResponse,
  QuestionRequest,
  QuestionResponse,
  ExportResponse,
} from '../types/contracts';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || '';

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  try {
    const tok = sessionStorage.getItem('finscan_session_jwt');
    if (tok) return { Authorization: `Bearer ${tok}`, ...extra };
  } catch {
    /* ignore */
  }
  return extra;
}

async function authedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  try {
    const tok = sessionStorage.getItem('finscan_session_jwt');
    if (tok && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${tok}`);
  } catch {
    /* ignore */
  }
  const res = await fetch(input, { credentials: 'include', ...init, headers });
  if (res.status === 401) {
    // Session expired/invalid -> clear local session so LoginPage gating appears.
    try {
      sessionStorage.removeItem('finscan_underwriter_session');
      sessionStorage.removeItem('finscan_session_jwt');
    } catch {
      /* ignore */
    }
    if (typeof window !== 'undefined' && (import.meta.env.VITE_AUTH_MODE === 'google')) {
      window.location.hash = '#/login';
    }
  }
  return res;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Ignore JSON parse failure on non-JSON error
    }
    throw new Error(`API Error (${response.status}): ${errorDetail}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  /**
   * Health check endpoint
   */
  async checkHealth(): Promise<{ status: string; service: string; version: string }> {
    const res = await authedFetch(`${BASE_URL}/health`);
    return handleResponse(res);
  },

  /**
   * List recent applications
   */
  async listApplications(): Promise<Array<{ application_id: string; applicant_name: string; loan_amount: number; status: string; created_at?: string }>> {
    const res = await authedFetch(`${BASE_URL}/applications`);
    return handleResponse(res);
  },

  /**
   * Retrieve application state (currently a stub on backend returning { application_id, status })
   */
  async getApplication(id: string): Promise<Partial<LoanApplicationState>> {
    const res = await authedFetch(`${BASE_URL}/applications/${encodeURIComponent(id)}`);
    return handleResponse<Partial<LoanApplicationState>>(res);
  },

  /**
   * Create a new loan application container
   */
  async createApplication(payload: CreateApplicationRequest): Promise<CreateApplicationResponse> {
    const res = await authedFetch(`${BASE_URL}/applications`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    return handleResponse<CreateApplicationResponse>(res);
  },

  /**
   * Queue application for processing (202 Accepted with job_id)
   */
  async processApplication(id: string): Promise<ProcessApplicationResponse> {
    const res = await authedFetch(`${BASE_URL}/applications/${encodeURIComponent(id)}/process`, {
      method: 'POST',
    });
    return handleResponse<ProcessApplicationResponse>(res);
  },

  /**
   * Upload a document for a specific application
   */
  async uploadDocument(
    applicationId: string,
    file: File,
    docTypeHint?: string
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (docTypeHint) {
      formData.append('doc_type_hint', docTypeHint);
    }
    const res = await authedFetch(`${BASE_URL}/applications/${encodeURIComponent(applicationId)}/documents`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DocumentUploadResponse>(res);
  },

  /**
   * Poll processing job status
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await authedFetch(`${BASE_URL}/jobs/${encodeURIComponent(jobId)}`);
    return handleResponse<JobStatusResponse>(res);
  },

  /**
   * Cancel a queued or running job
   */
  async cancelJob(jobId: string): Promise<{ job_id: string; status: string }> {
    const res = await authedFetch(`${BASE_URL}/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: 'POST',
    });
    return handleResponse<{ job_id: string; status: string }>(res);
  },

  /**
   * Submit human underwriter review decision
   */
  async submitReview(
    applicationId: string,
    payload: ReviewDecisionRequest
  ): Promise<ReviewDecisionResponse> {
    const res = await authedFetch(`${BASE_URL}/applications/${encodeURIComponent(applicationId)}/review`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    return handleResponse<ReviewDecisionResponse>(res);
  },

  /**
   * RAG-grounded question answering over application and policy
   */
  async askQuestion(
    applicationId: string,
    payload: QuestionRequest
  ): Promise<QuestionResponse> {
    const res = await authedFetch(`${BASE_URL}/applications/${encodeURIComponent(applicationId)}/questions`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    return handleResponse<QuestionResponse>(res);
  },

  /**
   * Export finalized dossier analysis (JSON metadata or PDF bytes).
   * PDF responses are binary: callers receive an object URL to download,
   * never parsed as JSON.
   */
  async exportApplication(
    applicationId: string,
    format: 'json' | 'pdf' = 'json'
  ): Promise<ExportResponse | { blobUrl: string; filename: string }> {
    const res = await authedFetch(
      `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/export?format=${encodeURIComponent(format)}`
    );
    if (!res.ok) {
      return handleResponse<ExportResponse>(res);
    }
    const contentType = res.headers.get('content-type') || '';
    if (format === 'pdf' || contentType.includes('application/pdf')) {
      const blob = await res.blob();
      return { blobUrl: URL.createObjectURL(blob), filename: `CAM_${applicationId}.pdf` };
    }
    return res.json() as Promise<ExportResponse>;
  },
};
