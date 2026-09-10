import React, { useState } from 'react';
import { FileText, UploadCloud } from 'lucide-react';
import { DocumentList } from './navigation/DocumentList';
import { DocumentUploadModal } from './navigation/DocumentUploadModal';

interface DossierPaneProps {
  documentIds: string[];
  classifiedTypes?: Record<string, string>;
  selectedDocId: string;
  onSelectDoc: (docId: string) => void;
  applicationId: string;
  onUploadDocument: (file: File, docTypeHint?: string) => Promise<void>;
}

export const DossierPane: React.FC<DossierPaneProps> = ({
  documentIds,
  classifiedTypes = {},
  selectedDocId,
  onSelectDoc,
  applicationId,
  onUploadDocument,
}) => {
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);

  return (
    <aside className="w-full h-full flex flex-col bg-white border-r border-slate-200">
      {/* Pane Header */}
      <div className="px-4 py-3.5 border-b border-slate-200 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-indigo-600" />
          <h2 className="text-sm font-bold text-slate-800">Dossier Documents</h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-600 border border-slate-200">
          {documentIds.length} {documentIds.length === 1 ? 'file' : 'files'}
        </span>
      </div>

      {/* Document List Container */}
      <div className="flex-1 overflow-y-auto p-3">
        <DocumentList
          documentIds={documentIds}
          classifiedTypes={classifiedTypes}
          selectedDocId={selectedDocId}
          onSelectDoc={onSelectDoc}
        />
      </div>

      {/* Upload Action Footer */}
      <div className="p-3 border-t border-slate-200 bg-slate-50 shrink-0">
        <button
          type="button"
          onClick={() => setIsUploadOpen(true)}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-dashed border-indigo-300 text-xs font-semibold text-indigo-700 bg-white hover:bg-indigo-50 hover:border-indigo-400 transition-colors shadow-2xs"
        >
          <UploadCloud className="w-4 h-4 text-indigo-600" />
          <span>Upload Additional File</span>
        </button>
      </div>

      {/* Upload Modal Dialog */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUpload={onUploadDocument}
        applicationId={applicationId}
      />
    </aside>
  );
};
