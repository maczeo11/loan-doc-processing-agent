# FinScan AI Frontend Architecture

**Document Version:** 1.0  
**Last Updated:** September 2026  
**Owner:** Akshaya (Member 7)

---

## Overview

The FinScan AI frontend is a single-page application (SPA) built with React 18, Vite, TypeScript, and Tailwind CSS. It provides a three-pane reviewer layout for bank underwriters to review loan dossiers, inspect extracted facts with evidence citations, and make approval decisions.

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | React | 18.x |
| Build Tool | Vite | 5.x |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS | 3.x |
| PDF Rendering | pdf.js | 4.x |
| Icons | Lucide React | Latest |
| State Management | React Context | Built-in |

---

## Component Architecture

```
apps/ui/src/
├── App.tsx                          # Root component with providers
├── components/
│   ├── layout/
│   │   ├── Header.tsx               # Top bar with app title, auth, SLA timer
│   │   ├── LeftDossierPane.tsx      # Document list navigation
│   │   ├── RightInspectorPane.tsx   # Findings, facts, Q&A, memo tabs
│   │   └── Resizer.tsx              # Draggable pane dividers
│   ├── viewer/
│   │   ├── PdfViewer.tsx            # Main PDF canvas container
│   │   ├── PdfPage.tsx              # Single page renderer
│   │   ├── PdfToolbar.tsx           # Zoom, page navigation controls
│   │   ├── usePdfDocument.ts        # pdf.js document hook
│   │   ├── BoundingBoxOverlay.tsx   # Evidence highlight layer
│   │   ├── EvidenceBox.tsx          # Individual evidence highlight
│   │   └── ViewerToolbar.tsx        # Document-level toolbar
│   ├── review/
│   │   ├── FindingCard.tsx          # Rule result with evidence citations
│   │   ├── FactsTab.tsx             # Extracted facts display
│   │   ├── MemoNarrativeTab.tsx     # Credit Appraisal Memo
│   │   ├── PolicyQaTab.tsx          # Policy Q&A interface
│   │   └── ReviewActionModal.tsx    # Approve/Reject/Request Info modal
│   ├── qa/
│   │   └── QaPanel.tsx              # Interactive Q&A with citations
│   ├── navigation/
│   │   ├── DocumentList.tsx         # Document navigation list
│   │   ├── DocumentCard.tsx         # Single document card
│   │   └── DocumentUploadModal.tsx  # Upload interface
│   └── common/
│       ├── StatusPill.tsx           # Status/verdict badge
│       ├── MaskedValue.tsx          # PII-masked display
│       ├── SlaTimer.tsx             # Review SLA countdown
│       └── KeyboardShortcutsModal.tsx
├── context/
│   ├── AuthContext.tsx              # Authentication state
│   └── EvidenceNavigationContext.tsx # Evidence click-to-jump
├── hooks/
│   ├── useEvidenceNavigation.ts     # Evidence navigation hook
│   └── useKeyboardShortcuts.ts      # Keyboard shortcuts
├── services/
│   ├── api.ts                       # Typed API client
│   ├── auth.ts                      # Auth service
│   └── documentStorage.ts           # Document storage helpers
├── types/
│   ├── contracts.ts                 # Backend contract types
│   ├── application.ts               # UI-specific types
│   ├── evidence.ts                  # Evidence types
│   └── auth.ts                      # Auth types
├── utils/
│   ├── pii.ts                       # PII masking utilities
│   ├── coordinates.ts               # Bounding box coordinate utils
│   ├── documentHelper.ts            # Document metadata helpers
│   └── exportUtils.ts               # Export functionality
└── data/
    └── mockDossier.ts               # Demo data for development
```

---

## Three-Pane Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Header                                          │
│  FinScan AI — Loan Document Reviewer    [SLA Timer] [User Avatar ▼]         │
├────────────────┬──────────────────────────────────┬─────────────────────────┤
│                │                                  │                         │
│   Dossier      │         PDF Viewer               │      Inspector          │
│   Documents    │                                  │                         │
│                │   ┌────────────────────────┐     │  ┌─────────────────────┐│
│  ┌───────────┐ │   │                        │     │  │ [Facts] [Findings]  ││
│  │ App Form  │ │   │   Canvas Rendering     │     │  │ [Memo]  [Q&A]       ││
│  ├───────────┤ │   │   with Bounding Box    │     │  ├─────────────────────┤│
│  │ Payslip 1 │ │   │   Overlays             │     │  │                     ││
│  ├───────────┤ │   │                        │     │  │ RULE-COMP-01: PASS  ││
│  │ Payslip 2 │ │   │   [Evidence Box        │     │  │ All documents       ││
│  ├───────────┤ │   │    ┌─────────┐]        │     │  │ verified            ││
│  │ Payslip 3 │ │   │                        │     │  ├─────────────────────┤│
│  ├───────────┤ │   └────────────────────────┘     │  │ RULE-INC-01: FLAG   ││
│  │ Bank Stmt │ │                                  │  │ Salary mismatch     ││
│  ├───────────┤ │   [Zoom: 100%] [Page: 1/3]       │  │ ₹72,500 vs ₹45,000  ││
│  │ ITR-V     │ │                                  │  ├─────────────────────┤│
│  ├───────────┤ │                                  │  │ [Approve] [Reject]  ││
│  │ PAN Card  │ │                                  │  │ [Request Info]      ││
│  └───────────┘ │                                  │  └─────────────────────┘│
│                │                                  │                         │
├────────────────┴──────────────────────────────────┴─────────────────────────┤
│                              Footer (optional)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PDF Viewer & Bounding Box System

### Architecture

The PDF viewer uses pdf.js to render documents directly to HTML5 canvas elements. Evidence citations are rendered as absolute-positioned overlay elements that transform normalized coordinates to pixel positions.

```
┌─────────────────────────────────────────────────────────────┐
│  PdfViewer                                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  usePdfDocument (hook)                                │  │
│  │  • Loads PDF via pdf.js                               │  │
│  │  • Manages page rendering                             │  │
│  │  • Handles zoom, navigation                           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Canvas Container (relative)                          │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  <canvas> (PDF page rendered by pdf.js)         │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  BoundingBoxOverlay (absolute, pointer-events-none)│ │
│  │  │  ┌─────────────────────────────────────────────┐│  │  │
│  │  │  │  EvidenceBox (positioned by coordinates)    ││  │  │
│  │  │  │  • Amber highlight border                   ││  │  │
│  │  │  │  • Hover tooltip with quoted span           ││  │  │
│  │  │  │  • Confidence percentage                    ││  │  │
│  │  │  └─────────────────────────────────────────────┘│  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Coordinate System

Evidence references use normalized coordinates (0-1) relative to page dimensions:

```typescript
interface BoundingBox {
  x0: number;  // Left edge (0 = left, 1 = right)
  y0: number;  // Top edge (0 = top, 1 = bottom)
  x1: number;  // Right edge
  y1: number;  // Bottom edge
  page_width?: number;   // PDF points (optional, for non-normalized)
  page_height?: number;
}
```

### Coordinate Transformation

```typescript
// apps/ui/src/components/viewer/BoundingBoxOverlay.tsx
function computePixelBounds(
  box: BoundingBox,
  renderedWidth: number,
  renderedHeight: number
): PixelBounds | null {
  // Detect if coordinates are normalized (0-1) or PDF points
  const isNormalized = 
    box.x0 <= 1.05 && box.y0 <= 1.05 && box.x1 <= 1.05 && box.y1 <= 1.05;

  if (isNormalized) {
    // Transform normalized to pixels
    left = Math.round(box.x0 * renderedWidth);
    top = Math.round(box.y0 * renderedHeight);
    width = Math.round((box.x1 - box.x0) * renderedWidth);
    height = Math.round((box.y1 - box.y0) * renderedHeight);
  } else {
    // Transform PDF points to pixels
    const pageWidth = box.page_width || 595;  // A4 default
    const pageHeight = box.page_height || 842;
    left = Math.round((box.x0 / pageWidth) * renderedWidth);
    top = Math.round((box.y0 / pageHeight) * renderedHeight);
    // ...
  }

  return { left, top, width, height };
}
```

### Evidence Box Rendering

```typescript
// apps/ui/src/components/viewer/EvidenceBox.tsx
export const EvidenceBox: React.FC<EvidenceBoxProps> = ({
  evidence,
  bounds,
  isSelected = true,
}) => {
  const [isHovered, setIsHovered] = useState<boolean>(false);
  const confidencePct = Math.round((evidence.confidence ?? 1) * 100);

  return (
    <div
      style={{
        left: `${bounds.left}px`,
        top: `${bounds.top}px`,
        width: `${bounds.width}px`,
        height: `${bounds.height}px`,
      }}
      className={`absolute z-20 transition-all pointer-events-auto cursor-pointer rounded-xs ${
        isSelected
          ? 'bg-amber-400/20 border-2 border-amber-600 ring-2 ring-amber-500/40'
          : 'bg-indigo-400/15 border border-indigo-500 hover:bg-indigo-400/25'
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Floating tooltip on hover */}
      {(isHovered || isSelected) && (
        <div className="absolute top-full left-0 mt-1 z-30 bg-slate-900/95 text-white text-[11px] p-2.5 rounded-lg shadow-xl">
          <p className="font-medium italic">"{evidence.quoted_span}"</p>
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>{evidence.extraction_method}</span>
            <span>{confidencePct}% confidence</span>
          </div>
        </div>
      )}
    </div>
  );
};
```

---

## Evidence Navigation Flow

### Click-to-Jump Interaction

When a user clicks an evidence citation in the findings panel, the system:

1. **Sets active evidence** in `EvidenceNavigationContext`
2. **Identifies target document** from `document_id`
3. **Calculates target page** from `page_number`
4. **Navigates PDF viewer** to correct page
5. **Highlights bounding box** on canvas

```typescript
// apps/ui/src/context/EvidenceNavigationContext.tsx
interface EvidenceNavigationContextType {
  activeEvidence: EvidenceRef | null;
  targetPageToNavigate: number | null;
  navigateToEvidence: (evidence: EvidenceRef) => void;
  clearActiveEvidence: () => void;
  clearTargetPage: () => void;
}

export const EvidenceNavigationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeEvidence, setActiveEvidence] = useState<EvidenceRef | null>(null);
  const [targetPageToNavigate, setTargetPageToNavigate] = useState<number | null>(null);

  const navigateToEvidence = (evidence: EvidenceRef) => {
    setActiveEvidence(evidence);
    if (evidence.page_number) {
      setTargetPageToNavigate(evidence.page_number);
    }
  };

  return (
    <EvidenceNavigationContext.Provider value={{
      activeEvidence,
      targetPageToNavigate,
      navigateToEvidence,
      // ...
    }}>
      {children}
    </EvidenceNavigationContext.Provider>
  );
};
```

### PDF Viewer Integration

```typescript
// apps/ui/src/components/viewer/PdfViewer.tsx
const PdfViewer: React.FC<PdfViewerProps> = ({ docId, pdfSource, isDemoMode }) => {
  const { activeEvidence, targetPageToNavigate, clearTargetPage } = useEvidenceNavigation();
  const { currentPage, goToPage } = usePdfDocument({ docId, pdfSource });

  // Navigate to target page when evidence is clicked
  useEffect(() => {
    if (
      targetPageToNavigate !== null &&
      activeEvidence &&
      activeEvidence.document_id === docId
    ) {
      if (currentPage !== targetPageToNavigate) {
        goToPage(targetPageToNavigate);
      }
      clearTargetPage();
    }
  }, [targetPageToNavigate, activeEvidence, docId, currentPage]);

  return (
    <main className="w-full h-full flex flex-col">
      {/* PDF canvas */}
      <canvas ref={canvasRef} />
      
      {/* Evidence overlay */}
      <BoundingBoxOverlay
        activeEvidence={activeEvidence}
        canvasWidth={canvasDimensions.width}
        canvasHeight={canvasDimensions.height}
        currentDocId={docId}
        currentPage={currentPage}
      />
    </main>
  );
};
```

---

## Finding Card with Evidence Citations

```typescript
// apps/ui/src/components/review/FindingCard.tsx
export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  isFocused,
  onSelectFinding,
  onSelectEvidence,
  activeEvidenceKey,
}) => {
  return (
    <div className={`p-3.5 rounded border ${isFocused ? 'bg-[#FDFBF7] border-stone-800' : 'bg-white'}`}>
      {/* Header: Rule ID & Verdict */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="font-mono text-xs font-semibold">{finding.rule_id}</span>
        <VerdictPill verdict={finding.verdict} />
      </div>

      {/* Rule Name */}
      <h4 className="text-xs font-serif font-bold">{finding.rule_name}</h4>

      {/* Reason */}
      <p className="text-xs text-stone-700">{sanitizePiiInText(finding.reason)}</p>

      {/* Evidence Citations */}
      {finding.supporting_evidence.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t">
          <div className="text-[10px] uppercase tracking-wider font-semibold">
            Verified Provenance ({finding.supporting_evidence.length})
          </div>
          {finding.supporting_evidence.map((ev, idx) => (
            <button
              key={idx}
              onClick={() => onSelectEvidence(ev)}
              className="text-left p-2 rounded border text-[11px]"
            >
              <span className="font-mono font-semibold text-amber-700">
                [{ev.document_type} • P.{ev.page_number}]
              </span>
              <span className="truncate block mt-0.5">
                "{sanitizePiiInText(ev.quoted_span)}"
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
```

---

## Q&A Panel

The Q&A panel allows underwriters to ask questions about the application and receive RAG-grounded answers with citations:

```typescript
// apps/ui/src/components/qa/QaPanel.tsx
export const QaPanel: React.FC<QaPanelProps> = ({ applicationId, isDemoMode }) => {
  const [messages, setMessages] = useState<QaMessage[]>([]);
  const [input, setInput] = useState('');

  const handleSubmit = async (question: string) => {
    // Add user message
    setMessages(prev => [...prev, { id: nanoid(), question, isLoading: true }]);
    
    try {
      // Call RAG endpoint
      const response = await api.askQuestion(applicationId, { question });
      
      // Add AI response with citations
      setMessages(prev => prev.map(m => 
        m.question === question 
          ? { ...m, answer: response.answer, citations: response.citations, isLoading: false }
          : m
      ));
    } catch (error) {
      // Handle error
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message history */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(msg => (
          <div key={msg.id}>
            <div className="text-sm font-medium">{msg.question}</div>
            {msg.isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <div className="mt-2">
                <p className="text-sm text-stone-700">{msg.answer}</p>
                {/* Citations */}
                {msg.citations?.map((cit, i) => (
                  <button
                    key={i}
                    onClick={() => navigateToEvidence(cit)}
                    className="text-xs text-amber-700 hover:underline"
                  >
                    [{cit.document_type} P.{cit.page_number}]
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit(input)}
          placeholder="Ask about this application..."
        />
      </div>
    </div>
  );
};
```

---

## Review Actions

### ReviewActionModal

```typescript
// apps/ui/src/components/review/ReviewActionModal.tsx
export const ReviewActionModal: React.FC<ReviewActionModalProps> = ({
  isOpen,
  onClose,
  applicationId,
  decision,
}) => {
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await api.submitReview(applicationId, {
        decision,
        reviewer_id: user.id,
        notes: notes || null,
      });
      // Success handling
    } catch (error) {
      // Error handling
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <h2>{decision === 'APPROVED' ? 'Sign Off (Approve)' : 
           decision === 'REJECTED' ? 'Flag Discrepancy' : 
           'Request Information'}</h2>
      
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Add notes for audit trail..."
      />
      
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button variant="primary" onClick={handleSubmit} loading={isSubmitting}>
          Submit
        </Button>
      </div>
    </Modal>
  );
};
```

---

## API Client

All API calls are typed against backend contracts:

```typescript
// apps/ui/src/services/api.ts
export const api = {
  async getApplication(id: string): Promise<Partial<LoanApplicationState>> {
    const res = await fetch(`/applications/${encodeURIComponent(id)}`);
    return handleResponse(res);
  },

  async submitReview(
    applicationId: string,
    payload: ReviewDecisionRequest
  ): Promise<ReviewDecisionResponse> {
    const res = await fetch(`/applications/${encodeURIComponent(applicationId)}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async askQuestion(
    applicationId: string,
    payload: QuestionRequest
  ): Promise<QuestionResponse> {
    const res = await fetch(`/applications/${encodeURIComponent(applicationId)}/questions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },
};
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `?` | Open keyboard shortcuts modal |
| `←` / `→` | Previous/next page |
| `+` / `-` | Zoom in/out |
| `f` | Toggle full-screen viewer |
| `a` | Approve (when in review mode) |
| `r` | Reject (when in review mode) |

---

## Build & Deployment

### Development

```bash
cd apps/ui
npm install
npm run dev
```

### Production Build

```bash
npm run build
# Output: apps/ui/dist/
# Served same-origin by FastAPI
```

### Docker

The SPA is built during the Docker image build and served by FastAPI:

```dockerfile
# infra/Dockerfile.api
FROM node:20-alpine AS ui-build
WORKDIR /app/apps/ui
COPY apps/ui/package*.json ./
RUN npm ci
COPY apps/ui .
RUN npm run build

FROM python:3.11-slim
# ... Python setup ...
COPY --from=ui-build /app/apps/ui/dist /app/apps/ui/dist
```

---

## Performance Considerations

1. **Lazy Loading:** PDF pages are rendered on-demand as user navigates
2. **Canvas Recycling:** Single canvas element is reused for page rendering
3. **Evidence Overlay:** Uses CSS transforms for smooth positioning
4. **Memoization:** React.useMemo for expensive coordinate calculations
5. **Debounced Resize:** Pane resizes are debounced to prevent layout thrashing
