import React from 'react';
import { DocumentCard } from './DocumentCard';
import { Files } from 'lucide-react';

interface DocumentListProps {
  documentIds: string[];
  classifiedTypes?: Record<string, string>;
  selectedDocId: string;
  onSelectDoc: (docId: string) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documentIds,
  classifiedTypes = {},
  selectedDocId,
  onSelectDoc,
}) => {
  if (documentIds.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-2">
          <Files className="w-5 h-5" />
        </div>
        <p className="text-xs font-medium text-slate-600">No documents found</p>
        <p className="text-[11px] text-slate-400 mt-0.5">
          Upload dossier files to begin verification
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documentIds.map((docId) => (
        <DocumentCard
          key={docId}
          documentId={docId}
          documentType={classifiedTypes[docId]}
          isSelected={selectedDocId === docId}
          onSelect={onSelectDoc}
        />
      ))}
    </div>
  );
};
