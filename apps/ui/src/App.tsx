import { useState, useEffect, useCallback } from 'react';
import { TopBar } from './components/TopBar';
import { DossierPane } from './components/DossierPane';
import { PdfViewer } from './components/viewer/PdfViewer';
import { ReviewPane } from './components/ReviewPane';
import { DEMO_DOSSIER_APP_25195 } from './data/mockDossier';
import { api } from './services/api';
import { getDocumentTitle } from './utils/documentHelper';
import { downloadJsonExport } from './utils/exportUtils';
import { EvidenceNavigationProvider } from './context/EvidenceNavigationContext';
import type { LoanApplicationState, ReviewDecisionRequest } from './types/contracts';

export default function App() {
  const [selectedAppId] = useState<string>('APP-25195');
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);
  const [dossierState, setDossierState] = useState<LoanApplicationState>(DEMO_DOSSIER_APP_25195);
  const [selectedDocId, setSelectedDocId] = useState<string>('doc-app-form');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [notification, setNotification] = useState<string | null>(null);
  
  const handleExportJson = () => {
    downloadJsonExport(dossierState);
    setNotification(`JSON export downloaded for ${dossierState.application_id}`);
  };


  const fetchApplicationData = useCallback(async () => {
    setIsLoading(true);
    try {
      if (isDemoMode) {
        // Use isolated demo data for APP-25195
        setDossierState(DEMO_DOSSIER_APP_25195);
        if (DEMO_DOSSIER_APP_25195.document_ids && DEMO_DOSSIER_APP_25195.document_ids.length > 0) {
          setSelectedDocId(DEMO_DOSSIER_APP_25195.document_ids[0]);
        }
        setNotification('Loaded demo dossier for APP-25195');
      } else {
        // Call live API backend GET /applications/{id}
        const apiData = await api.getApplication(selectedAppId);
        setDossierState({
          application_id: apiData.application_id || selectedAppId,
          status: apiData.status || 'UPLOADED',
          document_ids: apiData.document_ids || [],
          classified_types: apiData.classified_types || {},
          findings: apiData.findings || [],
          applicant: apiData.applicant || null,
          payslip: apiData.payslip || null,
          bank_statement: apiData.bank_statement || null,
          tax_return: apiData.tax_return || null,
          summary_markdown: apiData.summary_markdown || null,
        });
        if (apiData.document_ids && apiData.document_ids.length > 0) {
          setSelectedDocId(apiData.document_ids[0]);
        } else {
          setSelectedDocId('no-docs');
        }
        setNotification(`Fetched live API response for ${selectedAppId}`);
      }
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Failed to fetch application');
    } finally {
      setIsLoading(false);
    }
  }, [isDemoMode, selectedAppId]);

  useEffect(() => {
    fetchApplicationData();
  }, [fetchApplicationData]);

  const handleToggleDemoMode = () => {
    setIsDemoMode((prev) => !prev);
  };

  const handleSelectDoc = (docId: string) => {
    setSelectedDocId(docId);
  };

  const handleUploadDocument = async (file: File, docTypeHint?: string) => {
    try {
      if (isDemoMode) {
        const newDocId = `doc-user-${Date.now().toString().slice(-4)}`;
        setDossierState((prev) => ({
          ...prev,
          document_ids: [...(prev.document_ids || []), newDocId],
          classified_types: {
            ...(prev.classified_types || {}),
            [newDocId]: docTypeHint || 'document',
          },
        }));
        setSelectedDocId(newDocId);
        setNotification(`Uploaded "${file.name}" to demo dossier.`);
      } else {
        const uploadRes = await api.uploadDocument(selectedAppId, file, docTypeHint);
        setDossierState((prev) => ({
          ...prev,
          document_ids: [...(prev.document_ids || []), uploadRes.document_id],
          classified_types: {
            ...(prev.classified_types || {}),
            [uploadRes.document_id]: docTypeHint || 'document',
          },
        }));
        setSelectedDocId(uploadRes.document_id);
        setNotification(`Uploaded "${file.name}" (ID: ${uploadRes.document_id})`);
      }
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Failed to upload document');
      throw err;
    }
  };

  const handleSubmitReview = async (
    decision: ReviewDecisionRequest['decision'],
    notes: string
  ) => {
    try {
      if (!isDemoMode) {
        await api.submitReview(selectedAppId, {
          decision,
          reviewer_id: 'REV-UNDERWRITER-1',
          notes,
        });
      }
      setDossierState((prev) => ({
        ...prev,
        status: decision === 'NEEDS_INFO' ? 'NEEDS_INFORMATION' : 'REVIEWED',
        reviewer_decision: decision,
        reviewer_notes: notes,
      }));
      setNotification(`Review submitted: ${decision}`);
    } catch (err) {
      setNotification(err instanceof Error ? err.message : 'Error submitting review');
    }
  };

  const currentDocTitle = getDocumentTitle(
    selectedDocId,
    dossierState.classified_types?.[selectedDocId]
  );

  return (
    <EvidenceNavigationProvider onSelectDocument={handleSelectDoc}>
      <div className="h-screen w-screen flex flex-col bg-slate-100 font-sans overflow-hidden">
        {/* Top Application Bar */}
        <TopBar
          applicationId={selectedAppId}
          applicantName={dossierState.applicant?.full_name || 'Ananya Sharma'}
          status={dossierState.status}
          isDemoMode={isDemoMode}
          isLoading={isLoading}
          onRefresh={fetchApplicationData}
          onToggleDemoMode={handleToggleDemoMode}
          onExportJson={handleExportJson}
        />

        {/* Notification Toast */}
        {notification && (
          <div className="bg-slate-800 text-white text-xs px-4 py-1.5 flex items-center justify-between shrink-0">
            <span>{notification}</span>
            <button
              onClick={() => setNotification(null)}
              className="text-slate-400 hover:text-white ml-4 font-bold"
            >
              ×
            </button>
          </div>
        )}

        {/* Three-Pane Reviewer Workspace Layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Pane: Dossier Documents (260px - 320px) */}
          <div className="w-72 shrink-0 h-full">
            <DossierPane
              documentIds={dossierState.document_ids || []}
              classifiedTypes={dossierState.classified_types}
              selectedDocId={selectedDocId}
              onSelectDoc={handleSelectDoc}
              applicationId={selectedAppId}
              onUploadDocument={handleUploadDocument}
            />
          </div>

          {/* Center Pane: Real PDF.js Viewer (flex-1) */}
          <div className="flex-1 h-full min-w-0">
            <PdfViewer
              docId={selectedDocId}
              docTitle={currentDocTitle}
              isDemoMode={isDemoMode}
            />
          </div>

          {/* Right Pane: Findings & Human Review (360px - 420px) */}
          <div className="w-96 shrink-0 h-full">
            <ReviewPane
              state={dossierState}
              onSubmitReview={handleSubmitReview}
              isDemoMode={isDemoMode}
            />
          </div>
        </div>
      </div>
    </EvidenceNavigationProvider>
  );
}
