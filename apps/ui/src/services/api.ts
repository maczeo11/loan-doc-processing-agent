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

const BASE_URL = '';

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
    const res = await fetch(`${BASE_URL}/health`);
    return handleResponse(res);
  },

  /**
   * Retrieve application state (currently a stub on backend returning { application_id, status })
   */
  async getApplication(id: string): Promise<Partial<LoanApplicationState>> {
    const res = await fetch(`${BASE_URL}/applications/${encodeURIComponent(id)}`);
    return handleResponse<Partial<LoanApplicationState>>(res);
  },

  /**
   * Create a new loan application container
   */
  async createApplication(payload: CreateApplicationRequest): Promise<CreateApplicationResponse> {
    const res = await fetch(`${BASE_URL}/applications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<CreateApplicationResponse>(res);
  },

  /**
   * Queue application for processing (202 Accepted with job_id)
   */
  async processApplication(id: string): Promise<ProcessApplicationResponse> {
    const res = await fetch(`${BASE_URL}/applications/${encodeURIComponent(id)}/process`, {
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
    const res = await fetch(`${BASE_URL}/applications/${encodeURIComponent(applicationId)}/documents`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DocumentUploadResponse>(res);
  },

  /**
   * Poll processing job status
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await fetch(`${BASE_URL}/jobs/${encodeURIComponent(jobId)}`);
    return handleResponse<JobStatusResponse>(res);
  },

  /**
   * Cancel a queued or running job
   */
  async cancelJob(jobId: string): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${BASE_URL}/jobs/${encodeURIComponent(jobId)}/cancel`, {
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
    const res = await fetch(`${BASE_URL}/applications/${encodeURIComponent(applicationId)}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
    const res = await fetch(`${BASE_URL}/applications/${encodeURIComponent(applicationId)}/questions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
    const res = await fetch(
      `${BASE_URL}/applications/${encodeURIComponent(applicationId)}/export?format=${encodeURIComponent(format)}`
    );
    if (!res.ok) {
      return handleResponse<ExportResponse>(res);
    }
    const contentType = res.headers.get('content-type') || '';
    if (format === 'pdf' || contentType.includes('application/pdf')) {
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      return { blobUrl, filename: `CAM_${applicationId}.pdf` };
    }
    return res.json() as Promise<ExportResponse>;
  },
};
