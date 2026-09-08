# FinScan AI — Reviewer SPA (Frontend)

**Owner:** Akshaya  
**Tech Stack:** React 18, Vite, TypeScript, Tailwind CSS, pdf.js

---

## 🎯 Purpose
The underwriter reviewer dashboard where loan officers review parsed dossiers, verify bounding-box evidence against original PDF documents, inspect deterministic consistency checks, and submit final sign-off.

---

## 📋 Key Features to Implement
1. **Document Viewer:** Split pane rendering original PDFs using `pdf.js` with bounding-box overlays based on `EvidenceRef` coordinates.
2. **Reconciliation Card:** Displaying `Finding` verdicts (`pass` / `flag` / `unknown`) with direct citation jump-links to document pages.
3. **HITL Sign-Off Actions:**
   - Sign Off / Approve
   - Flag Discrepancy / Reject
   - Request Missing Information
4. **Interactive Policy Q&A:** Chat panel asking questions against `POST /applications/{id}/questions`.

---

## 🔌 API Endpoints
The SPA calls the API on same-origin `/` in production or via Vite proxy (`http://localhost:8000`) in development:
- `GET  /applications/{id}` — Fetch application state, findings, and evidence.
- `POST /applications/{id}/documents` — Upload new dossier files.
- `POST /applications/{id}/process` — Trigger processing job.
- `GET  /jobs/{id}` — Poll processing job status.
- `POST /applications/{id}/review` — Submit human approval or rejection.
- `POST /applications/{id}/questions` — RAG Q&A with citations.
- `GET  /applications/{id}/export` — Download finalized audit report.

---

## 🛠️ Local Development

```bash
cd apps/ui
npm install
npm run dev
```

To build static bundle for FastAPI:
```bash
npm run build
# Outputs to apps/ui/dist, which FastAPI serves automatically at http://localhost:8000
```
