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

Verified against `main` @ `89390f0`. Every file below exists; nothing reachable
is omitted.

```
apps/ui/src/
├── App.tsx                          # Root: providers, routing, keyboard shortcuts
├── main.tsx                         # Vite entry
├── index.css                        # Ledger design tokens (see Theming)
├── components/
│   ├── DashboardPage.tsx            # Dossier desk — landing view, live roster
│   ├── auth/
│   │   └── LoginPage.tsx            # Google sign-in gate
│   ├── layout/
│   │   ├── Header.tsx               # App title, dossier switcher, SLA timer
│   │   ├── LeftDossierPane.tsx      # Document index (inlines its own cards)
│   │   └── RightInspectorPane.tsx   # Findings / facts / memo / Q&A + sign-off
│   ├── viewer/
│   │   ├── PdfViewer.tsx            # pdf.js canvas container + page render
│   │   ├── usePdfDocument.ts        # pdf.js document hook
│   │   ├── BoundingBoxOverlay.tsx   # Evidence highlight layer
│   │   ├── EvidenceBox.tsx          # Individual evidence highlight + tooltip
│   │   └── ViewerToolbar.tsx        # Zoom, paging, document-level controls
│   ├── review/
│   │   ├── FindingCard.tsx          # Rule result with evidence citations
│   │   ├── FactsTab.tsx             # Extracted facts display
│   │   ├── MemoNarrativeTab.tsx     # Credit Appraisal Memo + exports
│   │   ├── PolicyQaTab.tsx          # Policy Q&A with grounding banner
│   │   └── ReviewActionModal.tsx    # Approve / Reject / Request Info + dual-sign
│   ├── navigation/
│   │   ├── DocumentUploadModal.tsx  # Upload interface
│   │   └── NewApplicationModal.tsx  # Create dossier
│   └── common/
│       ├── StatusPill.tsx           # StatusPill + VerdictPill (token-driven)
│       ├── MaskedValue.tsx          # PII-masked display
│       ├── SlaTimer.tsx             # Review SLA countdown
│       └── KeyboardShortcutsModal.tsx
├── context/
│   ├── AuthContext.tsx              # Authentication state
│   ├── EvidenceNavigationContext.tsx # Evidence click-to-jump (the live one)
│   └── ThemeContext.tsx             # Stamps data-theme="ledger"; no state
├── services/
│   ├── api.ts                       # Typed API client
│   └── auth.ts                      # Auth service
├── types/
│   ├── contracts.ts                 # Backend contract types
│   ├── api.ts                       # Request/response + PolicyCitation
│   ├── application.ts               # UI-specific types
│   ├── evidence.ts                  # EvidenceRef, Finding, BoundingBox
│   └── auth.ts                      # Auth types
├── utils/
│   ├── pii.ts                       # PII masking utilities
│   ├── coordinates.ts               # Bounding box coordinate utils
│   ├── documentHelper.ts            # Document metadata helpers
│   └── demoPdfGenerator.ts          # Synthetic PDFs for demo presets
└── data/
    └── mockDossier.ts               # Demo data for development
```

### Removed in `77baa1d`

Fifteen unreferenced modules were deleted. They are listed here so the names
in older design notes and PR descriptions resolve to something:

| Removed | Superseded by |
|---------|---------------|
| `components/DossierPane.tsx`, `ReviewPane.tsx`, `TopBar.tsx`, `ViewerPane.tsx` | the `layout/` three-pane components |
| `layout/Resizer.tsx` | fixed pane widths (`width` props on the panes) |
| `viewer/PdfPage.tsx`, `viewer/EvidenceOverlay.tsx` | inline render path in `PdfViewer` + `BoundingBoxOverlay` → `EvidenceBox` |
| `viewer/PdfToolbar.tsx` | `viewer/ViewerToolbar.tsx` |
| `qa/QaPanel.tsx` | `review/PolicyQaTab.tsx` |
| `navigation/DocumentList.tsx`, `DocumentCard.tsx` | list inlined in `LeftDossierPane` |
| `hooks/useEvidenceNavigation.ts` | `context/EvidenceNavigationContext.tsx` — the hook was a **name collision** with a different API |
| `hooks/useKeyboardShortcuts.ts` | inline `keydown` handler in `App.tsx` |
| `services/documentStorage.ts`, `utils/exportUtils.ts` | no call sites |

There is no `hooks/` directory. `useEvidenceNavigation` is exported from
`context/EvidenceNavigationContext.tsx` — import it from there.

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

## Policy Q&A

Lives in `review/PolicyQaTab.tsx`, rendered as a tab of the right inspector.
Underwriters ask policy questions and receive RAG answers that must declare
their own grounding.

**The grounding banner is not decoration — it is the abstention contract.**
Every answer renders one, and it is derived, never asserted:

```tsx
// apps/ui/src/components/review/PolicyQaTab.tsx
const citations: PolicyCitation[] = (resp.citations || []).map(/* … */);

setHistory((prev) => [{
  question: q,
  answer: resp.answer,
  // Grounded only when the backend returned at least one citation.
  is_grounded: citations.length > 0,
  citations,
}, ...prev]);
```

An ungrounded answer renders `ShieldAlert` + *"Unverified — illustrative
example, not retrieved evidence"*; a grounded one renders `ShieldCheck` +
the citation's policy name. The seeded example answer shipped for demos is
hardcoded `is_grounded: false` for exactly this reason.

Three rules for anyone touching this component:

1. **Never hardcode `is_grounded: true`.** A regression once did, which made the
   fabricated demo seed render under "Authoritative Citation" — the precise
   failure [`AGENTS.md`](../AGENTS.md) §1–2 exists to prevent.
2. **Never swallow the API error.** A bare `catch {}` makes a failed request
   indistinguishable from a considered answer. Failures are pushed into the
   stream as an ungrounded entry carrying the error text.
3. **Citations that carry provenance are navigable.** A citation with
   `document_id` + `page_number` becomes a jump target into the PDF canvas via
   `onSelectEvidence`; policy-corpus chunks without them render read-only:

```tsx
function toEvidenceRef(c: PolicyCitation): EvidenceRef | null {
  if (!c.document_id || !c.page_number) return null;
  return { document_id: c.document_id, document_type: c.document_type || 'document',
           page_number: c.page_number, quoted_span: c.text || '',
           bounding_box: c.bounding_box ?? null };
}
```

Answer text and citation bodies both pass through `sanitizePiiInText`.

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

---

## Human-in-the-Loop Consensus & Two-Step Dual-Sign Confirmation

To enforce **The Prime Invariant** (*A human approves. No autonomous underwriting.*), the UI implements a strict **Two-Step Dual-Sign Confirmation Protocol** in [`ReviewActionModal.tsx`](../apps/ui/src/components/review/ReviewActionModal.tsx):

### Friction Protocol Against Accidental Loan Dispositions
Underwriters reviewing dozens of applications per day face motor fatigue and accidental click risks. A simple misclick must never approve or deny a loan application.

0. **Step 0 — Sign-off gate (before any modal can open):**
   - Decisions unlock **only** when the dossier is `READY_FOR_REVIEW` *and* has
     at least one finding. A dossier still in `UPLOADED` / `QUEUED` /
     `PROCESSING`, or one with zero findings, cannot be signed at all.
   - The backend enforces the same rule (409 unless `READY_FOR_REVIEW`); the UI
     mirrors it so the underwriter is never offered an action the server will
     reject, and can never authorise a loan before verification has run.
   - Enforced in **two places that must stay in sync** — the buttons in
     `RightInspectorPane.tsx` and the `[A]`/`[R]`/`[N]` hotkeys in `App.tsx`:
     ```tsx
     const canSignOff =
       application.status === 'READY_FOR_REVIEW' && application.findings.length > 0;
     ```
     A hotkey path that skips this check silently re-opens the hole, since it
     bypasses the disabled button entirely.

1. **Step 1 — Intent Selection:**
   - Underwriter presses tactile buttons (`[A] Approve`, `[R] Reject`, `[N] Need Info`) or hotkeys.
   - The modal mounts, displaying:
     - Clear consequence banner (e.g. *Records APPROVED by Senior Underwriter in the immutable audit trail. State transitions to REVIEWED and the thread is sealed.*)
     - Impact analysis on application lifecycle state.
2. **Step 2 — Mandatory Audit Rationale:**
   - For `REJECTED` and `NEEDS_INFO` dispositions, an underwriter audit rationale ($\ge 5$ characters) is mandatory. Without substantive legal/risk justification, the action cannot proceed.
3. **Step 3 — Dual-Sign Identifier Challenge:**
   - The underwriter must explicitly type the exact dossier identifier (e.g. `APP-25195`) into the confirmation challenge field.
   - The `Confirm & Authorize` action button is strictly disabled until the typed string matches the application ID.
   - The match **must also be non-empty**:
     ```tsx
     const confirmMatches =
       confirmText.trim() !== '' && confirmText.trim() === applicationId;
     ```
     Without the first clause the protocol defeats itself: `''.trim() === ''` is
     `true`, so whenever `applicationId` is empty the seal button unlocks on a
     *freshly opened, untouched* modal — one stray Enter away from an
     authorisation. This has regressed once; it is the single most important
     line in the file.
   - Once confirmed, the review decision and rationale are atomically posted to the backend API (`POST /review/{id}/decision`) and sealed.

### Regression watchlist

These five behaviours have each been silently reverted at least once by a merge
from a stale base. They produce no build error and no visible symptom in a happy-path
demo — check them explicitly before any release:

| Guard | Location | Symptom when lost |
|-------|----------|-------------------|
| Sign-off gate | `RightInspectorPane.tsx`, `App.tsx` | Loans signable before verification runs |
| Non-empty dual-sign | `ReviewActionModal.tsx` | Seal button unlocked on a fresh modal |
| `sanitizePiiInText` on evidence spans | `EvidenceBox.tsx`, `PdfViewer.tsx` | Raw PAN / Aadhaar / account numbers on screen and in `aria-label` |
| Derived `is_grounded` | `PolicyQaTab.tsx` | Fabricated answers labelled "Authoritative Citation" |
| Unevidenced-finding warning | `FindingCard.tsx` | Findings with no `EvidenceRef` render as confirmed |

---

## Financial Design System — Archival Swiss Ledger

The product ships **one** theme. An earlier 3-in-1 switcher (Slate / Obsidian)
with `localStorage` persistence was removed once the product committed to a
single look; its palettes were unreachable dead CSS and its provider had no
consumers. [`ThemeContext.tsx`](../apps/ui/src/context/ThemeContext.tsx) now
only stamps `data-theme="ledger"`, and `index.html` stamps it too so the palette
lands on first paint instead of after React mounts.

- **Palette:** warm parchment desk (`#F8F6F1`, `#F5F2EB`), British racing green
  (`#14532D`), Bordeaux claret (`#991B1B`), tobacco amber (`#92400E`).
- **Typography:** editorial serif headers (`Newsreader` / Georgia) against
  `JetBrains Mono` for every figure and identifier.
- **Intent:** the trust and rigour of a Swiss private-banking credit audit desk.

`font-feature-settings: 'tnum' 1` (`tabular-nums`) is set on `body` so digits
align vertically in every financial comparison.

### The token contract

Colour lives in exactly one place: CSS custom properties on `:root` in
[`index.css`](../apps/ui/src/index.css), surfaced as Tailwind `theme-*` colours
in `tailwind.config.js`.

**No component may hardcode a Tailwind palette colour** (`bg-emerald-500`,
`text-slate-900`, …). There are currently zero such usages; keep it that way.
Beyond consistency this has bitten us concretely — several hardcoded values were
*dark-theme* colours left stranded on the light parchment ground, so the SLA
timer, the masked-PII pill and the pipeline panel were rendering pale text on a
light background.

| Semantic | Token | Use for |
|----------|-------|---------|
| Verified / approved | `theme-pass`, `theme-pass-bg`, `theme-pass-border` | PASS verdicts, sign-off confirmation |
| Discrepancy / rejected | `theme-flag`, `theme-flag-bg`, `theme-flag-border` | FLAG verdicts, failures, destructive actions |
| Unverified / attention | `theme-unknown`, `theme-unknown-bg`, `theme-unknown-border` | UNKNOWN verdicts, evidence highlights, pending pipeline |
| Surfaces | `theme-app`, `theme-card`, `theme-panel`, `theme-panel-hover` | backgrounds, in that nesting order |
| Text | `theme-primary`, `theme-secondary`, `theme-muted` | body copy by emphasis |
| Structure | `theme-border`, `theme-border-card` | hairlines and card edges |
| Brand | `theme-brand` | navigation accents, focus states |

Note that `theme-brand` and `theme-pass` are both `#14532D`. Do not use
`theme-brand` to signal approval — an "in progress" state tinted brand green is
indistinguishable from a signed-off one. Transient states use the neutral panel
plus a spinner; see `StatusPill`'s `PROCESSING` entry.

### Tokens are RGB channels, not hex

Each token is a **space-separated RGB triplet**, and `tailwind.config.js` wraps
it with `<alpha-value>`:

```css
/* index.css */
--accent-pass: 20 83 45;          /* NOT #14532D */
```
```js
/* tailwind.config.js */
pass: 'rgb(var(--accent-pass) / <alpha-value>)',
```

This is load-bearing. Tailwind **cannot apply an alpha modifier to a plain
`var()` colour** — it silently generates no class at all, with no build error
and no console warning. While the tokens were hex, every one of the 27
`/alpha` utilities in the app was dead: `bg-theme-panel/50` throughout
`FactsTab`, the focus rings in `FindingCard` and `LeftDossierPane`, both modal
tints. They looked correct in source and did nothing in the browser.

If you add a token, add the channel triplet **and** the `<alpha-value>` wrapper.
To verify a suspect utility actually compiled:

```bash
cd apps/ui && npm run build
grep -o 'bg-theme-panel\\/50{[^}]*}' dist/assets/*.css   # empty output = not generated
```

