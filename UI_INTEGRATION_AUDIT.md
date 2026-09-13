# FinScan AI — Functionality & Demo-Readiness Audit

Scope: **hackathon functionality + demoability only.** Production hardening (accessibility, exhaustive security, visual polish) is intentionally out of scope. Findings below come from tracing actual source code (frontend → API → worker → LangGraph → rules/ML) on `main` @ `f268e0a`, not from trusting `docs/implementation_status.md`'s "100% complete" claims. The app was **not spun up live** (no Docker/Postgres/Redis session in this pass) — every finding is a static, verified code-path trace; treat "run it live once before the demo" as a standing action item regardless.

---

## 1. What the product actually is

Confirmed from code, not just docs: a loan-dossier intake and underwriting-assist tool.

```
Underwriter
 ↓ uploads 5 documents (application form, 3 payslips, bank stmt, ITR, KYC)
 ↓
FastAPI persists docs → outbox event → worker picks up job
 ↓
LangGraph 8-node pipeline: triage → OCR/classify → extract → rules → RAG → synth → grounding gate → interrupt()
 ↓
Pipeline halts at READY_FOR_REVIEW (real LangGraph interrupt_before, verified in core/graph/workflow.py:88)
 ↓
Underwriter reviews findings/evidence in React SPA, approves/rejects/requests info
 ↓
CAM PDF exported
```

This matches the README's "Prime Invariant" framing and is **substantively real**, not a facade — see §3.

---

## 2. Is it real or mocked? (verified, not assumed)

| Claim | Verified reality |
|---|---|
| ML confidence reaches the UI | **Real.** `core/graph/nodes.py:313-339` builds `classification_metadata[doc_id]` with `confidence`, `class_probabilities`, `requires_human_triage` from the actual classifier result (`ml_res.get("confidence")`), with distinct tiers for ML / heuristic-fallback / failure. Frontend types (`types/contracts.ts`, `types/application.ts`) and viewer components (`EvidenceBox.tsx`, `LeftDossierPane.tsx`) consume `confidence`. |
| LangGraph is actually invoked | **Real.** `worker/consumer.py:273` calls `self.graph.invoke(...)` where `self.graph` is built by `core/graph/workflow.py:build_application_graph`, which sets `interrupt_before=interrupt_nodes` (workflow.py:88) targeting `READY_FOR_REVIEW`. Not a stubbed/no-op graph. |
| `api.ts` frontend calls hit real endpoints | **Real.** Every method in `apps/ui/src/services/api.ts` is a genuine `fetch` against `apps/api/routes/*` — no simulated responses, no `setTimeout`-faked network calls in the production code path. |
| CAM PDF export | **Mostly real, correctly gated.** Real applications call `api.exportApplication(id, 'pdf')` → backend `core/reporting/exporter.py` (ReportLab). A **client-side fake PDF generator** (`utils/demoPdfGenerator.ts: generateSignedCamPdf`) exists, but `MemoNarrativeTab.tsx:105` gates it strictly behind `isReadOnlyPreset` (the offline demo dossier only) — it does **not** silently substitute for a failed real export. This is a reasonable, honest fallback design, not a mock-dressed-as-real bug. |
| `mockDossier.ts` / demo data | **Present but correctly isolated.** `App.tsx:205,339,570` gates all use behind `isDemoDossierId(selectedAppId)`. A real application ID never routes through the mock dossier. Low risk of leaking fake data into a real demo run, *provided* the demo doesn't accidentally select the preset ID when a judge expects a live one — worth a note during the live demo script (see §5).
| `getApplication` doc comment says "stub" | **Stale comment, not stale code.** `apps/api/routes/applications.py:143-173` fully hydrates state from DB (`state_json`, loan fields, reviewer, timestamps) — the "currently a stub" comment in `api.ts:133` is simply out of date. Not a functional bug, but worth fixing before a judge reads the source. |

**Verdict on the "fake UI" risk:** Low. This is not a project papering over a non-functional backend with mocked screens. The pipeline is genuinely wired end to end. The real risks are in **workflow completeness gaps**, not fakery — see §3.

---

## 3. Verified functional gaps (the ones that will actually bite in a demo)

### F-01 — Reclassifying a document does not re-run extraction or rules — P0 for the "wrong document type" demo journey

**Problem:** `PATCH /applications/{id}/documents/{doc_id}/reclassify` (`apps/api/routes/documents.py:437-495`) updates `DocumentModel.doc_type` and `state_json.classified_types` / `classification_metadata` only. It never re-queues extraction or re-evaluates deterministic rules.

**Why it matters for a demo:** The canonical judge test is "upload a payslip labeled as a bank statement, watch the system catch it, let the underwriter fix it, see the correction flow downstream." Today:
1. Classification badge updates correctly (`confidence: 1.0`, `method: "user_override"`) ✅
2. The **extracted facts** (`payslip_facts`/`bank_facts`/etc.) still reflect the original (wrong) extractor's output ❌
3. The **rule findings** (RULE-COMP-01, RULE-INC-01, etc.) still reflect the pre-correction state ❌
4. `POST /applications/{id}/process` — the only path that re-runs the LangGraph pipeline — is **hard-blocked** once the application has left `UPLOADED` status: `apps/api/routes/applications.py:230-234` raises `409 Conflict` for any status other than `UPLOADED`. Once a dossier reaches `READY_FOR_REVIEW`, there is **no API-exposed way** to force a re-extraction/re-rules pass after a reclassification.

**Frontend makes this worse, not better:** `App.tsx:427-437` (`handleReclassifyDocument`) shows a plain success toast — `"Document {id} reclassified as {type}."` — with no indication that downstream facts/findings are now stale. A judge who reclassifies a document and then looks at findings will see confident-looking (but wrong) numbers still displayed as if verified.

**Fix (small, demo-safe):**
- Cheapest: after a successful reclassify while status is `READY_FOR_REVIEW`/pre-review, re-run only `extract_facts_node` + `evaluate_rules_node` synchronously in the reclassify handler (or queue a lightweight re-eval job) and persist updated facts/findings.
- Minimum viable for the demo script: at least surface a UI banner ("Reclassified — facts/findings not yet re-verified, re-run recommended") so the gap is honest on screen instead of silently wrong.

---

### F-02 — Stale docstring claims `GET /applications/{id}` is a stub — cosmetic but judge-visible

**Problem:** `apps/ui/src/services/api.ts:133` comment: *"Retrieve application state (currently a stub on backend returning `{ application_id, status }`)"*. The actual backend (`apps/api/routes/applications.py:143-173`) returns full state. If a judge or teammate reads source during Q&A, this reads as an admission of incompleteness that isn't true.

**Fix:** One-line comment fix. Trivial, but do it — it actively undersells a feature that already works.

---

### F-03 — Demo-preset vs. live-application ID collision risk

**Problem:** The offline/demo dossier (`APP-25195`, referenced throughout `mockDossier.ts`, `demoPdfGenerator.ts`, and the README's demo script) is selected purely by ID match (`isDemoDossierId`). If the live demo backend is later seeded with an application that reuses `APP-25195` (e.g., from a stale synthetic-dossier import), the frontend will render the **hardcoded client-side preset**, not the live backend data — silently, with no error.

**Why it matters:** This is exactly the kind of thing that causes an "it worked in rehearsal, showed fake numbers in front of judges" failure. Low probability, high embarrassment.

**Fix:** Either rename the offline preset ID to something that can't collide with generated IDs (e.g., `DEMO-PRESET-OFFLINE`), or add a visible "OFFLINE PRESET" badge (the code has `isReadOnlyPreset` plumbed already — check it's actually rendered somewhere visible, not just used for gating logic).

---

## 4. What's genuinely solid (don't waste demo-prep time here)

- **ML confidence → UI chain** is real and complete, including graceful three-tier fallback (ML confident / heuristic fallback / total failure), and `requires_human_triage` flag is derived from actual confidence, not hardcoded.
- **LangGraph interrupt/HITL checkpoint** is a real `interrupt_before` on `READY_FOR_REVIEW`, not a fake "pending" status set by the frontend.
- **Worker → graph → DB** wiring (`worker/consumer.py:273`) is a genuine `.invoke()` call, checkpointed via `core/graph/checkpoint.py`.
- **API client layer** has no simulated/faked calls in the real-application code path; error handling (`handleResponse`) surfaces real backend error details rather than swallowing them.
- **CAM export** correctly distinguishes real (backend/ReportLab) vs. offline-preset (client-generated) PDF paths and doesn't blur the two for live applications.
- **Document delete** (`apps/api/routes/documents.py:498+`) purges storage + DB + state_json references — not just a UI-side removal.

---

## 5. Demo-readiness checklist

| # | Item | Status |
|---|---|---|
| 1 | Upload → process → classify → extract → rules → review, on a fresh application | Should work — full chain verified in code; **not live-tested this pass, run it once before presenting.** |
| 2 | "Wrong document type" journey (upload mismatch, detect, reclassify, see correction propagate) | **Will look broken** at the "see correction propagate" step — see F-01. Either fix it, or drop this specific journey from the live demo script and only show the reclassify badge update. |
| 3 | Low-confidence document → human triage flag | Should work — `requires_human_triage` is real and threshold-driven (`conf < 0.40`). |
| 4 | CAM PDF export on a real (non-preset) application | Should work if backend `reportlab` is installed; confirm `docs/implementation_status.md`'s "501 without reportlab" comment in `api.ts:279` isn't live — check `requirements.txt`. |
| 5 | Offline/preset dossier demo (`APP-25195`) as a fallback if backend is unreachable during the live demo | Works by design — good safety net, but see F-03 for ID-collision risk. |

---

## 6. Prioritized fix list (hackathon-appropriate, not production-appropriate)

**Must fix / must work around before demo:**
1. **F-01** — either wire reclassify → re-extract/re-evaluate, or quietly drop "watch the correction propagate through findings" from the live demo script and only claim "the underwriter can correct the classification" (true) without claiming facts auto-update (not true yet).
2. Actually **run the full stack once** (`make demo-all` or equivalent) end-to-end before presenting — this audit traced code paths but did not execute them in a live environment this session.

**Should fix if time remains:**
3. F-02 — fix the stale "stub" comment in `api.ts`.
4. F-03 — rename/flag the offline preset ID to avoid any live-ID collision.
5. Add the "not yet re-verified" banner on reclassify as a stopgap for F-01 if the full re-eval isn't feasible before the deadline.

**Nice to have (skip unless everything else is done):**
6. Surface `classification_metadata.method` (`ml_baseline` / `heuristic_fallback` / `user_override`) somewhere in the UI — the data already exists, showing it would strengthen the "AI transparency" story for judges with near-zero engineering cost.

---

## Bottom line

This is **not** a hackathon project faking its backend behind a polished UI — the classification, extraction, rules, LangGraph orchestration, and review flow are genuinely wired end-to-end, which is the hard part and it's done. The one real functional hole that will hurt in a live demo is that **human correction of a misclassified document doesn't propagate to facts/findings**, because the only re-processing path (`/process`) is locked to `UPLOADED`-status applications. Fix that, or demo around it — everything else here is either already solid or a one-line polish item.
