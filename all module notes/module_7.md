# 📚 FinScan AI — Module 7: Frontend Reviewer SPA & Underwriter Cockpit
## 🎓 Complete Conceptual & Theory Guide for Mentor Explanation (Zero Code)
### **Owner:** Akshaya (Member 7 — Frontend Lead & Human-in-the-Loop Interaction Architect)
### **Assigned Scope:** `apps/ui/` (React 18 SPA, Vite, Tailwind CSS, `pdf.js` Canvas, Dual-Sign Gate, Policy Q&A) & `core/reporting/exporter.py`

---

## 🧭 Table of Contents
1. [The 30-Second Elevator Pitch to Your Mentor](#1-the-30-second-elevator-pitch-to-your-mentor)
2. [The Real-World Banking Problem (Underwriter Fatigue & The Misclick Nightmare)](#2-the-real-world-banking-problem-underwriter-fatigue--the-misclick-nightmare)
3. [Key Definitions in Simple Terms (The Module 7 Vocabulary)](#3-key-definitions-in-simple-terms-the-module-7-vocabulary)
4. [Pillar 1: The Three-Pane Cockpit Layout (Left, Center, Right)](#4-pillar-1-the-three-pane-cockpit-layout-left-center-right)
5. [Pillar 2: The `pdf.js` Canvas & Dynamic Bounding-Box Overlay Engine](#5-pillar-2-the-pdfjs-canvas--dynamic-bounding-box-overlay-engine)
6. [Pillar 3: The 3-Tier Dual-Sign Confirmation Friction Gate (Accidental Approval Prevention)](#6-pillar-3-the-3-tier-dual-sign-confirmation-friction-gate-accidental-approval-prevention)
7. [Pillar 4: Interactive Policy Q&A & Inline Citation Navigation](#7-pillar-4-interactive-policy-qa--inline-citation-navigation)
8. [Pillar 5: Banking Accessibility & Power-Underwriter Keyboard Workflows](#8-pillar-5-banking-accessibility--power-underwriter-keyboard-workflows)
9. [Pillar 6: Security, PII Masking & Same-Origin Zero-Node Production Serving](#9-pillar-6-security-pii-masking--same-origin-zero-node-production-serving)
10. [Pillar 7: Exporting the Sealed Credit Appraisal Memo (PDF & JSON)](#10-pillar-7-exporting-the-sealed-credit-appraisal-memo-pdf--json)
11. [End-to-End Walkthrough: Underwriter Priya Reviewing Ravi Kumar's Dossier](#11-end-to-end-walkthrough-underwriter-priya-reviewing-ravi-kumars-dossier)
12. [Architectural Trade-Off & Decision Tables](#12-architectural-trade-off--decision-tables)
13. [Top 15 Mentor & Viva Defense Questions & Answers](#13-top-15-mentor--viva-defense-questions--answers)
14. [Deep Dive: Exactly What Akshaya Built, Component Interactions, and Why Alternative UI Tech Was Rejected](#14-deep-dive-exactly-what-akshaya-built-component-interactions-and-why-alternative-ui-tech-was-rejected)

---

## 1. The 30-Second Elevator Pitch to Your Mentor

> *"Respected Sir/Ma'am,  
> Even the smartest AI is useless if a human underwriter cannot verify its claims or accidentally approves a fraudulent loan due to fatigue. In banking, the user interface is not just a visual skin—it is a legal compliance and risk-mitigation tool.  
> As **Member 7 (Akshaya)**, I built the Human-in-the-Loop Cockpit of FinScan AI:  
>  
> 1. **The Three-Pane Verification Cockpit:** A high-density single-page application (React 18 + Vite + Tailwind) featuring document navigation on the left, interactive `pdf.js` canvas in the center, and deterministic audit findings on the right.  
> 2. **Click-to-Verify Bounding Box Navigation:** When an underwriter clicks any audit finding or salary number, the canvas instantly pans to the exact document page and draws a highlighted bounding-box overlay directly over the source text in the PDF!  
> 3. **The 3-Tier Dual-Sign Friction Gate:** To completely prevent accidental lending authorizations from mouse slips or fatigue, the UI enforces intent selection, mandatory written rationale ($\ge 5$ chars), and forces the underwriter to manually type the exact Dossier ID (`APP-XXXXX`) into a challenge box before the sign-off button unlocks!  
> 4. **Production Zero-Node Footprint:** The entire React app compiles into pure static HTML/JS/CSS served directly by FastAPI, eliminating Node.js from production entirely."*

---

## 2. The Real-World Banking Problem (Underwriter Fatigue & The Misclick Nightmare)

### The Nightmare of Underwriter Fatigue
In a major retail bank, a credit underwriter reviews between 40 and 60 loan dossiers every single day.
- Each dossier contains 15 to 30 pages of payslips, bank statements, tax returns, and identity cards.
- By 4:00 PM, after staring at thousands of numbers, **cognitive fatigue sets in**.
- **The Danger of the Simple "Approve" Button:**  
  If the UI has a simple green *"Approve"* button, a tired underwriter might double-click or slip with their mouse, accidentally authorizing a ₹15,00,000 personal loan for an applicant who forged their salary slips!
- **The Tab-Switching Nightmare:**  
  Historically, underwriters had 4 different browser windows open: one for the PDF reader, one for Excel calculations, one for core banking, and one for credit policy manuals. Toggling back and forth wasted 15 minutes per loan and caused frequent errors.

### Akshaya's Solution
Akshaya built a **unified three-pane cockpit** where:
- Every number is visibly tethered to its physical page coordinates.
- Policy rules are cited inline.
- An accidental click cannot authorize a loan thanks to a multi-step confirmation challenge.

---

## 3. Key Definitions in Simple Terms (The Module 7 Vocabulary)

| Term | In Simple Words | Real-World Analogy | Role in FinScan AI |
| :--- | :--- | :--- | :--- |
| **Human-in-the-Loop (HITL)** | Ensuring that autonomous AI never makes the final decision; a human must review and sign off. | An airplane autopilot flying between cities, but a licensed captain handling take-off and landing. | The core philosophy governing Station 8 and the React review UI. |
| **`pdf.js` Canvas** | An open-source HTML5 rendering engine from Mozilla that draws PDF pages directly onto an HTML canvas. | A digital projector displaying a scanned slide onto a white screen in your browser. | Renders PDFs in the center pane with crisp zooming and no external plugins. |
| **Bounding-Box Overlay** | A colored visual rectangle drawn on top of a rendered PDF page to highlight exact source text. | A student using a yellow highlighter pen over a crucial sentence in a textbook. | Visually grounds every financial fact and finding to its page coordinates. |
| **Coordinate Scaling** | Mathematically translating PDF coordinate points ($[0, 595] \times [0, 842]$) onto physical screen pixels. | Scaling a blueprint to fit a laptop screen without warping the room proportions. | Handled dynamically in `BoundingBoxOverlay.tsx` during zoom and window resizing. |
| **Dual-Sign Friction Gate** | A safety mechanism that forces the user to complete deliberate manual steps before confirming a critical action. | A nuclear submarine requiring two officers to turn separate keys simultaneously to launch. | Prevents accidental approvals via intent selection, rationale, and typing the application ID. |
| **Dossier Identifier Challenge** | Requiring the reviewer to manually type `APP-XXXXX` before the approve/reject button enables. | An online bank asking you to re-type an account number before sending a wire transfer. | Unlocks the final sign-off button in `ReviewActionModal.tsx`. |
| **Inline Citation Jumping** | Clicking a tag like `[DOC-PAYSLIP:P1]` in the text to instantly navigate the PDF viewer to that exact page. | Clicking a blue footnote in Wikipedia that jumps straight to the source book. | Powers instant document and page navigation in the Reviewer UI. |
| **PII Masking** | Obscuring sensitive personal data (PAN card, bank account) so only the last 4 characters are visible. | Showing a credit card as `XXXX-XXXX-XXXX-1234` on a receipt. | Implemented in `utils/pii.ts` to protect borrower privacy. |
| **Zero-Node Production** | Compiling the frontend into pure static HTML/CSS/JS and serving it via FastAPI without running Node.js on the server. | Baking bread in an industrial bakery (Vite build) and selling the finished loaves in a grocery store without needing an oven in the store. | Reduces server RAM usage and simplifies cloud deployment on AWS `t4g.medium`. |

---

## 4. Pillar 1: The Three-Pane Cockpit Layout (Left, Center, Right)

Akshaya designed an ergonomic, high-density **three-pane layout** inspired by professional financial terminals (like Bloomberg and FactSet):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TOP NAV: FinScan AI | Dossier APP-25195 | Status: READY_FOR_REVIEW | Underwriter: Priya │
├───────────────────┬───────────────────────────────────┬────────────────────────────────┤
│   LEFT PANE       │            CENTER PANE            │          RIGHT PANE            │
│  (Document Index) │        (Interactive PDF Viewer)   │      (Audit & Fact Inspector)  │
│                   │                                   │                                │
│ • Application Form│  ┌─────────────────────────────┐  │  [Tabs: Findings | Facts | CAM]│
│   (Page 1 of 1)   │  │ HDFC Bank Statement         │  │                                │
│                   │  │ Account: XXXXXX4402         │  │ 🟢 RULE-COMP-01: PASS          │
│ • Payslips (3 mos)│  │ Date       Narration Amount │  │    All mandatory docs present. │
│   (Pages 2 to 4)  │  │ ─────────────────────────── │  │                                │
│                   │  │ 01/08/24  SALARY   ₹44,200 │  │ 🔴 RULE-INC-01: FLAG           │
│ • Bank Statement  │  │ ┌─────────────────────────┐ │  │    Salary mismatch: Stated     │
│   (Pages 5 to 10) │  │ │ [HIGHLIGHT BOX]         │ │  │    ₹55,000 vs Bank ₹44,200    │
│   [Active Tab]    │  │ └─────────────────────────┘ │  │    (Click to jump to citation) │
│                   │  │ Closing Balance: ₹1,28,400  │  │                                │
│ • Tax Return (ITR)│  └─────────────────────────────┘  │ ────────────────────────────── │
│   (Page 11)       │                                   │ ACTION BUTTONS:                │
│                   │  [Zoom: 100% | Prev | Next | Fit] │ [A] Approve  [R] Reject  [N]   │
└───────────────────┴───────────────────────────────────┴────────────────────────────────┘
```

### 1. Left Pane: Dossier Document Navigation (`LeftDossierPane.tsx`)
* Lists all uploaded customer documents with page counts and classification badges.
* Highlights the active document being viewed.
* Provides file upload, document reclassification, and delete controls for branch underwriters.

### 2. Center Pane: Interactive `pdf.js` Canvas Viewer (`PdfViewer.tsx`)
* Renders the authentic PDF document directly inside the browser using HTML5 Canvas.
* Features smooth zoom controls (50% to 200%, Fit to Width, Fit to Page).
* Houses the **BoundingBoxOverlay** that projects visual highlight boxes over verified spans.

### 3. Right Pane: The Audit Inspector (`RightInspectorPane.tsx`)
* **Tab 1: Findings:** Displays deterministic rule verdicts (`PASS`, `FLAG`, `UNKNOWN`) with severity badges and policy citations.
* **Tab 2: Extracted Facts:** Displays parsed applicant entities (net salary, bank credits, tax paid) with masked PII.
* **Tab 3: CAM Narrative:** Displays the synthesized Credit Appraisal Memo narrative generated in Station 6.
* **Tab 4: Ask FinScan AI (Policy Q&A):** An interactive assistant grounded in bank underwriting policy.
* **Tab 5: Audit Trail:** An immutable historical ledger tracking all state transitions and reviewer actions.

---

## 5. Pillar 2: The `pdf.js` Canvas & Dynamic Bounding-Box Overlay Engine

### The Problem with Fixed Coordinate Overlays
PDFs are measured in **points** (usually $595 \times 842$ points for standard A4 paper).  
However, when an underwriter views a document on a 1080p desktop monitor, the canvas might render at $800 \times 1132$ physical screen pixels. If the underwriter zooms in to 150%, the canvas expands to $1200 \times 1698$ pixels.  
If you use raw PDF points, your highlight boxes will appear in the completely wrong location!

### Akshaya's Solution: The Dynamic Pixel Bounds Formula (`computePixelBounds`)
In `BoundingBoxOverlay.tsx`, Akshaya implemented a dynamic mathematical scaling algorithm:

```
                          [Incoming EvidenceRef BoundingBox]
                                          │
                                          ▼
                      Are coordinates normalized? (x0, y0 <= 1.05)
                                          │
                         ┌────────────────┴────────────────┐
                       YES                                 NO
                         ▼                                 ▼
             [Normalized Coordinates]              [Raw PDF Points]
             left   = x0 * CanvasWidth             pageWidth  = box.page_width || 595
             top    = y0 * CanvasHeight            pageHeight = box.page_height || 842
             width  = (x1 - x0) * CanvasWidth      left   = (x0 / pageWidth) * CanvasWidth
             height = (y1 - y0) * CanvasHeight     top    = (y0 / pageHeight) * CanvasHeight
                         │                                 │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                         [Apply Boundary Clamping & Padding]
                         width  = max(14px, width)
                         height = max(10px, height)
                         left   = clamp(0, left, CanvasWidth - width)
                         top    = clamp(0, top, CanvasHeight - height)
                                          │
                                          ▼
                         [Render SVG/HTML Highlight Rectangle]
```

### Superpowers of This Architecture:
1. **Resolution-Independent:** Whether on a 13-inch laptop, an iPad, or a 4K monitor, highlight boxes land precisely over the target text.
2. **Zoom-Resistant:** As the user zooms in and out using the toolbar, the overlay automatically recalculates pixel coordinates in real time.
3. **Safety Fallback:** If an extractor cited evidence but bounding box coordinates are missing or unreadable, the UI safely renders an informational banner at the top: *"Evidence cited on Page X — Precise coordinates unavailable"*, ensuring the underwriter is never misled by a ghost box.

---

## 6. Pillar 3: The 3-Tier Dual-Sign Confirmation Friction Gate (Accidental Approval Prevention)

Under section 5.3 of `AGENTS.md`, **the UI must prevent accidental lending authorizations from underwriter fatigue or misclicks.**

Akshaya engineered the **3-Tier Dual-Sign Friction Gate** inside `ReviewActionModal.tsx`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   3-TIER DUAL-SIGN FRICTION GATE                       │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  TIER 1: INTENT SELECTION                                              │
│  Reviewer chooses:  [🟢 Approve]   [🔴 Reject]   [🟡 Need Info]        │
│                                                                        │
│  TIER 2: MANDATORY SUBSTANTIVE RATIONALE                               │
│  If "Reject" or "Need Info" is chosen:                                 │
│  • Reviewer MUST provide written justification.                        │
│  • Enforces minimum length: >= 5 characters.                           │
│  • Sign-off button remains disabled if rationale is blank!             │
│                                                                        │
│  TIER 3: DOSSIER IDENTIFIER CHALLENGE                                  │
│  "Type APP-25195 to confirm this decision:"                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ APP-25195                                                        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  • Strict Equality Check: typedText.trim() === applicationId           │
│  • Non-empty validation prevents empty string auto-unlock.             │
│                                                                        │
│  ════════════════════════════════════════════════════════════════════  │
│  [ CANCEL ]                       [ CONFIRM SIGN-OFF (UNLOCKED) 🟢 ]  │
└────────────────────────────────────────────────────────────────────────┘
```

### Why This is Essential for Banking Compliance:
* **The "Slip of the Mouse" Protection:** A tired underwriter cannot approve a loan with a single misclick.
* **The Challenge Field:** Typing the exact ID (`APP-25195`) forces the human brain to switch from passive scrolling to active cognitive engagement.
* **Audit Trail Accountability:** The rationale entered during Tier 2 is permanently written into PostgreSQL as an immutable audit record (`actor`, `timestamp`, `rationale`, `from_status`, `to_status`).

---

## 7. Pillar 4: Interactive Policy Q&A & Inline Citation Navigation

In complex loan underwriting, reviewers often encounter ambiguous edge cases:
- *"Can we accept rental income if the rental agreement is unregistered?"*
- *"Why was this applicant's salary flagged for a 12% mismatch?"*

Akshaya built the **Policy Q&A Panel (`PolicyQaTab.tsx`)** connected directly to `POST /applications/{id}/questions`:

### Key Features of the Q&A Panel:
1. **Pre-Engineered Quick Prompts:** Leads with contextual quick-action buttons:
   - *"Explain this salary mismatch flag"*
   - *"What are the bank's minimum DTI rules?"*
   - *"Verify KYC identity match guidelines"*
2. **Grounding Verification Badges:**
   - If the backend verified that the answer is grounded in official policy, it renders a green **`ShieldCheck` (Grounding Verified)** badge.
   - If the claim lacked policy grounding, it displays a yellow **`ShieldAlert` (Ungrounded / Abstention)** banner.
3. **Interactive Inline Footnotes (`renderInlineCitations`):**
   - Answers contain clickable citations like `[POL-SAL-01]` or `[DOC-PAYSLIP:P1]`.
   - **The Magic Click:** When an underwriter clicks `[DOC-PAYSLIP:P1]`, the center pane automatically switches to the Payslip document, jumps to Page 1, and draws the bounding box!

---

## 8. Pillar 5: Banking Accessibility & Power-Underwriter Keyboard Workflows

Senior bank underwriters process dozens of applications daily and prefer using keyboards rather than constantly reaching for a mouse.

Akshaya implemented a comprehensive suite of **Single-Key Keyboard Shortcuts** (`App.tsx`):

| Key | Action | What It Does |
| :---: | :--- | :--- |
| `j` or `↓` | **Next Finding** | Moves focus down to the next audit finding card in the right pane. |
| `k` or `↑` | **Previous Finding** | Moves focus up to the previous audit finding card. |
| `Enter` | **Jump to Citation** | Automatically switches center viewer to the cited document & page and highlights the box! |
| `]` | **Next Document** | Flips to the next document in the customer's uploaded dossier. |
| `[` | **Previous Document**| Flips to the previous document in the dossier. |
| `a` or `A` | **Initiate Approval** | Opens the Dual-Sign confirmation modal with "Approve" pre-selected. |
| `r` or `R` | **Initiate Rejection**| Opens the Dual-Sign confirmation modal with "Reject" pre-selected. |
| `n` or `N` | **Initiate Need Info** | Opens the Dual-Sign confirmation modal with "Need Info" pre-selected. |
| `Escape`| **Dismiss / Close** | Closes modals, shortcuts overlay, or clears active highlight selections. |
| `?` | **Show Shortcuts** | Toggles the keyboard shortcut reference cheatsheet on screen. |

> **Safety Invariant:** All keyboard shortcuts are automatically suspended whenever the reviewer's cursor is inside an input field or textarea, preventing accidental keystrokes while typing audit notes!

---

## 9. Pillar 6: Security, PII Masking & Same-Origin Zero-Node Production Serving

In financial technology, frontend engineering must enforce strict security boundaries:

### 1. Client-Side PII Masking (`utils/pii.ts`)
To protect borrower privacy and prevent shoulder-surfing in bank branches:
- **PAN Numbers:** Fully masked except for the last 4 characters (`XXXXXX1234`).
- **Bank Account Numbers:** Account numbers longer than 4 digits are masked (`XXXXXXXX4402`).
- **Aadhaar Numbers:** Masked to show only the last 4 digits (`XXXX-XXXX-9012`).

### 2. Zero-Node Production Deployment Architecture
In production, running a Node.js server to serve frontend pages introduces security vulnerabilities, memory overhead, and process management headaches.
- **Akshaya's Architecture:**
  - During the build step, Vite compiles the React app into optimized, minified static files in `apps/ui/dist/`.
  - **FastAPI serves these files directly** from the same origin (`/` and `/assets/`).
  - **Result:** **Zero Node.js processes run on the production server!** This saves ~150 MB of server RAM on our AWS `t4g.medium` instance.

### 3. Short-Lived Presigned Download URLs
- The React frontend **never connects directly to AWS S3** or stores static file paths.
- To render a PDF, `PdfViewer.tsx` requests a short-lived, cryptographically signed URL from FastAPI (valid for only 15 to 60 minutes).

### 4. Polling Rate-Limiting Protection
- The frontend polls `GET /applications/{id}` to detect pipeline progress.
- Enforces an interval floor of **$\ge 2$ seconds** (capped at 30 polls/minute) to prevent underwriter tabs from overwhelming the backend.

---

## 10. Pillar 7: Exporting the Sealed Credit Appraisal Memo (PDF & JSON)

Once an underwriter signs off on a loan dossier, the system generates an official **Credit Appraisal Memo (CAM)** receipt (`core/reporting/exporter.py`):

### What the Exporter Delivers:
1. **Structured JSON Export (`export_reviewed_dossier_json`):**  
   Exports the complete state graph dictionary containing all findings, bounding boxes, status transitions, and underwriter signatures for archival into the bank's data warehouse.
2. **Publication-Quality PDF Receipt (`export_reviewed_dossier_pdf`):**  
   Built using ReportLab Platypus, it renders a multi-page, formatted audit memo featuring:
   - Official bank header and application metadata.
   - Reconciled salary and financial arithmetic tables.
   - Deterministic rule findings with explicit pass/flag badges.
   - Synthesized Credit Appraisal Memo narrative.
   - **The Official Disposition Seal:** Displays the final sign-off decision (`APPROVED`, `REJECTED`, `NEEDS_INFO`), the underwriter's name, timestamp, and mandatory written rationale.

---

## 11. End-to-End Walkthrough: Underwriter Priya Reviewing Ravi Kumar's Dossier

Here is how Underwriter Priya uses Akshaya's cockpit to review applicant **Ravi Kumar**:

```
1. PRIYA LOGS INTO FINSCAN AI:
   • The dashboard lists 12 dossiers waiting in READY_FOR_REVIEW.
   • Priya clicks on Ravi Kumar (APP-25195).
   • The cockpit loads in under 200 ms with all 10 documents indexed.

2. IMMEDIATE VISUAL ALERT (RIGHT PANE):
   • Top status badge displays: READY_FOR_REVIEW (Paused at Station 7).
   • Finding Card 1: 🟢 RULE-COMP-01 (PASS) — All 5 mandatory document types present.
   • Finding Card 2: 🔴 RULE-INC-01 (FLAG) — Salary Discrepancy Detected!
     "Stated monthly salary: ₹55,000. Verified bank salary credits: ₹44,200.
      Discrepancy: -19.6% (Exceeds policy tolerance of 5.0%)."

3. CLICK-TO-VERIFY NAVIGATION:
   • Priya presses "Enter" on Finding Card 2.
   • The center viewer instantly switches from the Application Form to "HDFC Bank Statement",
     jumps to Page 2, and renders a glowing highlight box over the transaction row:
     "01/08/2024 - SALARY CREDIT - ₹44,200".
   • Priya confirms with her own eyes that the bank credit was indeed only ₹44,200!

4. ASKING POLICY Q&A:
   • In Tab 4 (Ask FinScan AI), Priya clicks: "Explain this salary mismatch flag".
   • FinScan AI responds citing bank guideline [POL-SAL-01]:
     "Credit policy requires stated income to match average 3-month net bank payroll
      deposits within 5%. Discrepancies exceeding 10% warrant rejection or debt-to-income recalculation."

5. THE DUAL-SIGN REJECTION SIGN-OFF:
   • Priya presses "r" on her keyboard.
   • The 3-Tier Dual-Sign modal opens:
     1. Intent: Pre-selected to "Flag Discrepancy & Reject Application".
     2. Rationale: Priya types: "Income inflated by 19.6%. Stated ₹55k vs actual ₹44.2k in HDFC account."
     3. Challenge: Priya types "APP-25195" into the confirmation box.
   • The red "Confirm Rejection" button unlocks!
   • Priya clicks Confirm.

6. AUDIT SEALING & EXPORT:
   • The state advances to REVIEWED.
   • An immutable audit event is committed to PostgreSQL.
   • Priya clicks "Download Audit Report (PDF)" to generate the sealed CAM for bank archives.
```

---

## 12. Architectural Trade-Off & Decision Tables

When your mentor asks *"Why did you design the frontend this way?"*, use these comparisons:

### 1. `pdf.js` Canvas vs. Browser Native `<embed>` / `<iframe>` PDF Viewer
| Criteria | `pdf.js` Canvas (Chosen) | Browser Native `<embed>` / `<iframe>` |
| :--- | :--- | :--- |
| **Bounding-Box Overlays** | ✅ Full control; draws HTML5/SVG highlight boxes directly over canvas coordinates | ❌ Impossible; browser PDF plugins are isolated sandboxes with zero DOM access |
| **Cross-Browser Consistency**| ✅ 100% identical rendering across Chrome, Firefox, Safari, and Edge | ❌ Inconsistent UI controls and toolbars across different browsers |
| **Security & Scripting** | ✅ Sandboxed inside React; disables malicious embedded PDF JavaScript | ❌ Can execute embedded PDF scripts or prompt external reader downloads |
| **Verdict** | **Selected:** Essential for visual provenance and bounding-box highlighting. | **Rejected:** Cannot draw coordinate bounding boxes. |

---

### 2. 3-Tier Dual-Sign Friction Gate vs. Simple "One-Click" Approval Button
| Criteria | 3-Tier Dual-Sign Gate (Chosen) | Single-Click Button |
| :--- | :--- | :--- |
| **Accidental Authorizations**| ✅ Zero possibility; requires typing the exact Dossier ID | ❌ High risk; mouse slips and underwriter fatigue cause wrongful approvals |
| **Regulatory Audit Defense** | ✅ Captures mandatory written rationale for every adverse decision | ❌ Fails audit; cannot prove underwriter consciously reviewed discrepancies |
| **User Friction** | Balanced (under 10 seconds for a conscious decision) | Ultra-fast (0.1 seconds) |
| **Verdict** | **Selected:** In banking, safety and audit compliance trump speed. | **Rejected:** Dangerous liability in retail credit underwriting. |

---

### 3. Vite + React 18 SPA (FastAPI Served) vs. Next.js / Server-Side Rendering (SSR)
| Criteria | React 18 + Vite (Chosen) | Next.js / SSR |
| :--- | :--- | :--- |
| **Production Server Footprint**| **Zero Node.js:** Static files served by FastAPI in 15 MB RAM | Requires running Node.js server (consuming 150–300 MB RAM) |
| **Deployment Simplicity** | Single Docker container with FastAPI | Requires multi-container setup (FastAPI + Node.js) |
| **Build Speed** | Ultra-fast (Vite Hot Module Replacement in < 100ms) | Slower build times and complex server hydration |
| **Verdict** | **Selected:** Strict adherence to AGENTS.md banned technology list (No Next.js). | **Banned:** Adds unnecessary cloud cost and operational overhead. |

---

## 13. Top 15 Mentor & Viva Defense Questions & Answers

### Q1: "What was your specific personal contribution as Akshaya (Member 7)?"
> **Answer:**  
> *"I was the Frontend Lead & Human-in-the-Loop Interaction Architect. I built the React 18 + Vite Reviewer Cockpit in `apps/ui/`, the `pdf.js` canvas viewer with dynamic bounding-box coordinate translation, the 3-Tier Dual-Sign confirmation friction gate, the Policy Q&A panel with inline citation jumping, and the audited dossier export engine in `core/reporting/exporter.py`."*

### Q2: "Why did you use `pdf.js` instead of standard browser PDF embeds?"
> **Answer:**  
> *"Browser native embeds (`<embed>` or `<iframe>`) render PDFs inside an isolated OS sandbox that web applications cannot touch. `pdf.js` decodes PDF vectors directly onto an HTML5 Canvas element. This gives us full DOM control to calculate coordinates and draw highlighted bounding-box overlays exactly over verified text spans!"*

### Q3: "How do you calculate bounding-box coordinates when a user zooms in or resizes the window?"
> **Answer:**  
> *"In `BoundingBoxOverlay.tsx`, our `computePixelBounds` function dynamically scales coordinates. If coordinates are normalized ($0$ to $1$), we multiply by the rendered canvas width and height. If they are in PDF points, we scale them by the unscaled page dimensions (e.g. $595 \times 842$). This guarantees that whether the user is at 50% zoom or 200% zoom, the highlight box lands exactly over the cited text."*

### Q4: "What is the 3-Tier Dual-Sign Friction Gate and why is it necessary?"
> **Answer:**  
> *"Underwriters review dozens of files daily and suffer from cognitive fatigue. A simple 'Approve' button leads to accidental authorizations. Our friction gate enforces 3 checks: 1) Intent selection, 2) Mandatory written rationale ($\ge 5$ characters) for adverse decisions, and 3) An identifier challenge requiring the underwriter to manually type the exact Dossier ID (`APP-XXXXX`). The button only unlocks when all 3 tiers pass."*

### Q5: "Can an underwriter approve a loan using keyboard shortcuts?"
> **Answer:**  
> *"Pressing 'A' on the keyboard initiates the approval workflow by opening the Dual-Sign modal, but it does NOT authorize the loan. The underwriter must still type the Dossier ID challenge to confirm. The system never allows a single blind keystroke to authorize lending capital."*

### Q6: "Why doesn't your React application use Node.js on the production server?"
> **Answer:**  
> *"We follow the 'Zero-Node in Production' architectural invariant from `AGENTS.md`. During CI/CD, Vite compiles our TypeScript and React components into minified static assets (`index.html`, JavaScript bundles, CSS). These static files are placed in `apps/ui/dist/` and served directly by FastAPI from the same origin. This saves 200 MB of server RAM and eliminates Node.js runtime vulnerabilities."*

### Q7: "How does the UI protect borrower privacy and customer PII?"
> **Answer:**  
> *"In `utils/pii.ts`, we implement client-side PII sanitization. Government PAN cards, bank account numbers, and Aadhaar numbers are automatically masked to display only their last 4 characters (`XXXXXX1234`), preventing visual data leaks or shoulder-surfing in busy bank branches."*

### Q8: "How does inline citation navigation work in the Policy Q&A panel?"
> **Answer:**  
> *"When the AI answers a policy question, it includes bracketed footnotes like `[DOC-PAYSLIP:P1]`. Our `renderInlineCitations` parser recognizes these tags and renders them as clickable links. Clicking a citation triggers `handleSelectEvidence()`, which automatically switches the center viewer to that document, navigates to the cited page, and scrolls the bounding box into view."*

### Q9: "What happens if an extractor cites evidence on a page, but the bounding box coordinates are missing?"
> **Answer:**  
> *"Our UI defensively guards against coordinate failure. Instead of crashing or rendering a confusing box in the corner of the page, it displays an informational badge: 'Evidence cited on Page X — Precise coordinates unavailable', ensuring full transparency without misleading the reviewer."*

### Q10: "How does the frontend communicate with Balaji's FastAPI backend?"
> **Answer:**  
> *"The frontend communicates through a strongly-typed API client (`services/api.ts`) generated from the frozen OpenAPI schema built by Manjunath. We use standard REST endpoints for dossier status, document uploads, and policy queries, and poll `GET /applications/{id}` at rate-limited intervals ($\ge 2$ seconds) to track asynchronous worker progress."*

### Q11: "Why did you build keyboard shortcuts (`j`, `k`, `Enter`, `[`, `]`)?"
> **Answer:**  
> *"Power-user ergonomics. Professional underwriters work much faster when they don't have to repeatedly switch between mouse and keyboard. They can scroll findings with `j`/`k`, press `Enter` to visually verify on-page evidence, and flip documents with brackets, cutting dossier review time from 15 minutes to under 2 minutes."*

### Q12: "What prevents keyboard shortcuts from firing while an underwriter is typing audit notes?"
> **Answer:**  
> *"In `App.tsx`, the global keydown listener inspects `e.target`. If the target is an `INPUT`, `TEXTAREA`, or `SELECT` element, the event listener returns immediately. Shortcuts only trigger when the user is navigating the workspace."*

### Q13: "What does the Credit Appraisal Memo (CAM) export contain?"
> **Answer:**  
> *"The export generated by `core/reporting/exporter.py` creates both a structured JSON file for core banking integration and a formal PDF report. It includes applicant demographics, reconciled salary figures, deterministic rule findings, policy citations, the underwriter's final decision, timestamp, and their mandatory audit rationale."*

### Q14: "How does your module enforce the project's Prime Invariant?"
> **Answer:**  
> *"The Prime Invariant states: 'Deterministic code calculates, AI explains, a human approves.' My UI guarantees that the system cannot issue an autonomous lending approval. The pipeline halts at Station 7, and only unlocks after a licensed human underwriter clears our 3-Tier Dual-Sign friction gate."*

### Q15: "If the evaluator asks you to summarize Module 7 in one sentence, what will you say?"
> **Answer:**  
> *"Module 7 provides the Human-in-the-Loop Cockpit of FinScan AI — uniting document navigation, interactive `pdf.js` canvas bounding-box overlays, and a 3-Tier Dual-Sign friction gate to ensure that credit decisions are fast, provable, and immune to underwriter misclicks."*

---

## 14. Deep Dive: Exactly What Akshaya Built, Component Interactions, and Why Alternative UI Tech Was Rejected

### 14.1 Component Hierarchy & Data Flow in `apps/ui/src/`

```
┌────────────────────────────────────────────────────────────────────────┐
│ App.tsx (Master Layout Controller & Keyboard Event Hub)                │
├──────────────────────────────────┬─────────────────────────────────────┤
│ LeftDossierPane.tsx              │ Center: PdfViewer.tsx               │
│ • Document manifest list         │ • usePdfDocument.ts (PDF.js loader) │
│ • Upload / Reclassify / Delete   │ • HTML5 Canvas Render Layer         │
│ • Page counts & status badges    │ • BoundingBoxOverlay.tsx            │
│                                  │   └── EvidenceBox.tsx (SVG Box)     │
│                                  │ • ViewerToolbar.tsx (Zoom/Pages)    │
├──────────────────────────────────┴─────────────────────────────────────┤
│ RightInspectorPane.tsx (Multi-Tab Audit & Decision Hub)                │
│ ├── Tab 1: FindingsTab.tsx (FindingCard.tsx with Pass/Flag badges)     │
│ ├── Tab 2: FactsTab.tsx (Reconciled salary, credits, masked PII)       │
│ ├── Tab 3: MemoNarrativeTab.tsx (CAM Markdown Narrative)               │
│ ├── Tab 4: PolicyQaTab.tsx (Interactive Chat, ShieldCheck Badges)      │
│ └── Tab 5: AuditTrailTab.tsx (Status transitions, actor, timestamp)    │
├────────────────────────────────────────────────────────────────────────┤
│ ReviewActionModal.tsx (The 3-Tier Dual-Sign Friction Gate)             │
│ ├── Intent Selection ([A] Approve, [R] Reject, [N] Need Info)          │
│ ├── Mandatory Written Rationale (min 5 characters)                     │
│ └── Dossier Identifier Challenge (Input equality: APP-XXXXX)           │
└────────────────────────────────────────────────────────────────────────┘
```

### 14.2 Why Alternative Frontend Technologies Were Explicitly Rejected

1. **Why NOT Next.js / Nuxt / SvelteKit (SSR)?**  
   - Explicitly banned in `AGENTS.md`. Server-Side Rendering requires a running Node.js server in production, increasing RAM usage by 200 MB and introducing server hydration complexity. Vite creates static files served same-origin by FastAPI with zero Node in production.
2. **Why NOT Redux or MobX for State Management?**  
   - Banned in `AGENTS.md`. FinScan AI uses pure React state hooks (`useState`, `useMemo`, `useCallback`) and lightweight React Context (`AuthContext.tsx`). The backend PostgreSQL database and LangGraph state graph are the single sources of truth; client-side state is strictly ephemeral.
3. **Why NOT Third-Party Component Libraries (MUI, Ant Design, Chakra)?**  
   - Banned in `AGENTS.md`. Heavy component libraries add 500 KB to 1 MB of JavaScript bloat, slow down rendering, and make custom coordinate overlays difficult. Akshaya built lightweight, accessible, tailored Tailwind CSS components with zero third-party UI framework bloat.
4. **Why NOT Client-Side Financial Calculations?**  
   - Inviolable rule: The UI **never calculates financial arithmetic** (e.g. computing DTI or salary averages). All numbers originate from Sravanthi's deterministic Python rules engine in `core/rules/`. The UI strictly displays what the backend verified.
