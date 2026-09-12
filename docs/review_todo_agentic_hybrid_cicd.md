# Review Todo — `test/agentic-hybrid-cicd` vs `main`

Findings from a high-effort code review plus follow-up deep-dives on the agentic
LLM/tool-calling/RAG integration, identity cross-checking, and explanation capability,
run against this branch before merging into `main`. Done as of this session: 1-13, 16,
17, 18, 19, 20. Still open: 14 (dead-code/cleanup pass), 15 (RAG stale-token bug).

## Correctness (block merge)

- [x] **1. `document_texts` cache dropped by LangGraph state schema** —
  `core/contracts/state.py`. `LoanApplicationState` (TypedDict) has no `document_texts`
  field, so the OCR page-text cache Node 2 writes never survives to Node 3 in the real
  compiled graph (only in unit tests that call nodes directly). Every document falls into
  the cache-miss branch, which this diff changed from a cheap native-only call into a full
  OCR-router pass — reintroducing the "2x OCR cost" problem the change claims to fix.
  **Fix:** add `document_texts` to the TypedDict schema. **Done** — field added; both
  Node 2 (write) and Node 3 (read) cache paths updated to match.

- [x] **2. Evidence page/bbox misalignment on cache-miss re-parse** —
  `core/graph/nodes.py:308`. `_extract_doc_texts_via_router` silently skips pages with no
  extractable text (`continue`, no placeholder), so `enumerate()` mislabels later pages'
  `page_number`. It also drops `page_width`/`page_height`, so bounding boxes fall back to a
  hardcoded 600x800. Underwriter evidence overlays can point at the wrong page/location.
  **Fix:** preserve page index (insert a placeholder instead of `continue`) and propagate
  real page dimensions from the router. **Done** — `_extract_doc_texts_via_router` now
  returns one `{page_number, text, page_width, page_height}` dict per real page (blank
  pages keep "" text instead of a dropped slot); both Node 2 and Node 3 cache read/write
  sites updated (backward-compatible with the older plain string-list cache format tests
  still seed directly).

- [x] **3. Hardcoded `[:30]` instead of `MAX_PAGES_PER_DOCUMENT`** —
  `core/graph/nodes.py:291` (cache-hit branch). Currently equals the constant by
  coincidence, but is a second, independent source of truth that will silently diverge if
  `MAX_PAGES_PER_DOCUMENT` is retuned. **Fix:** use the constant. **Done** — fixed as part
  of the item 2 rewrite.

- [x] **4. Router re-parses native-text pages 2-3x** —
  `core/extraction/router.py:107` / `core/graph/nodes.py`. Wiring the router into the main
  path by default means every native-text page now goes through
  `extract_page_content` + `extract_native_text_with_coordinates` +
  `get_page_image_coverage` instead of one cheap call — a real CPU/I-O regression for the
  common (non-OCR) case. **Fix:** only invoke router escalation for pages that actually
  need OCR; keep the cheap native path for the rest. **Done** — added an optional
  pre-opened `doc=` param threaded through `native_parser.py`'s `extract_page_content`,
  `get_page_image_coverage`, `extract_native_text_with_coordinates` and `router.py`'s
  `inspect_page_route`/`route_page_extraction`; `_extract_doc_texts_via_router` opens the
  PDF once per document and reuses it across every page instead of reopening/reparsing up
  to 3x per page. Fully backward-compatible (default `doc=None` behaves exactly as before
  for every other caller/test).

## Security

- [x] **5. Firebase auth accepts unverified emails** —
  `apps/api/auth/firebase_verify.py:47`. `email_verified` isn't checked, and the allowlist
  authorizes purely by email string/domain match. Anyone can self-register with an unowned
  `@authorized-domain.com` address and get auto-provisioned as `SENIOR_UNDERWRITER`.
  **Fix:** require `email_verified == True` (or an explicit invite/claim) before allowlist
  auto-provisioning. **Done** — unverified email/password sign-in tokens are now rejected
  outright; Google/federated sign-in (always `email_verified=True`) is unaffected.

- [x] **6. Session cookie `Secure` flag gated on undocumented `TLS_ENABLED`** —
  `apps/api/routes/auth.py:70`, `apps/api/config.py:58` (default `False`). Not set in
  `.env.example`, `.env.production.example`, `docker-compose.yml`, or any infra script, so
  a production-behind-HTTPS deploy can silently lose the `Secure` cookie attribute.
  **Fix:** default `Secure` based on `ENVIRONMENT` again, or add `TLS_ENABLED=true` to all
  production env templates/infra scripts and document it. **Done** — the `False` default
  was actually a deliberate, correct fix for this project's real HTTP-only EC2 deployment
  (switching back to `ENVIRONMENT`-based inference previously broke login); documented the
  flag with usage guidance in `.env.production.example` instead of reverting it.

- [x] **7. `sanitize_summary_text` doesn't catch fully uncited answers** —
  `core/rag/grounding.py:132`. Only lines that already contain a `[chunk_id]` tag are
  checked; a hallucinated line with zero citation tags passes through untouched, so a
  confident, uncited LLM answer reaches the underwriter with no abstention warning.
  **Fix:** require at least one valid citation to appear somewhere in a non-empty answer,
  else treat it as ungrounded/abstain (mirror `validate_llm_narrative`'s fail-closed
  pattern). Add a test for "confident prose, no bracket tags at all." **Done** — tracks
  `has_any_citation_tag` across the whole answer (not per-line); zero tags anywhere ⇒ the
  entire answer is withheld with an abstention notice. Kept distinct from the existing
  "citation present but unauthorized ⇒ drop that line" behavior, which is unchanged (2 new
  tests: fully-uncited-is-withheld, mixed-cited-and-uncited-survives).

- [x] **8. Rate-limit identity falls back to spoofable `X-User-Id` header** —
  `apps/api/middleware/rate_limit.py:136` via `apps/api/auth/deps.py:66-77`
  (`current_user_email(..., fallback="")`). Currently masked by router-level auth
  requiring a valid session first, but a latent spoofing vector for any future caller that
  reuses `resolve_user_identity`/`current_user_email` without that guard.
  **Fix:** make the header fallback explicit/opt-in only for `AUTH_MODE == "mock"`, never
  silently available otherwise. **Done** — `current_user_email` only reads `X-User-Id`
  when `AUTH_MODE == "mock"`; any other mode falls back to the generic key on a
  missing/invalid/expired JWT instead of an attacker-controlled header.

## Agentic LLM / RAG follow-ups

- [x] **9. `get_agentic_chat_model()` misses the `OPENAI_API_KEY` fallback** —
  `apps/api/agent.py:50` checks only `GROQ_API_KEY`/`OPENCODE_API_KEY`, but
  `adapters/llm/opencode.py:34`'s `OpenCodeZenLLM` also resolves `OPENAI_API_KEY` as a
  third fallback. A deployment configured with only `OPENAI_API_KEY` silently never gets
  the agentic path even though the adapter itself would work.
  **Fix:** check the same three env vars the adapter actually uses. **Done.**

- [x] **10. `langgraph` version unpinned (`>=0.0.30`, no ceiling)** —
  `requirements.txt`, `requirements-ci.txt`. `create_react_agent(chat_model, tools,
  prompt=system_prompt)` uses the modern `prompt=` kwarg, which didn't exist in the pinned
  floor version and has drifted across langgraph releases. Every test in
  `test_agentic_qa.py` mocks `create_react_agent` entirely, so a real API break would never
  be caught by CI (fails safe to the non-agentic fallback, but silently and permanently).
  **Fix:** pin a tested range (e.g. `>=0.2,<0.4`) and add one smoke test that imports the
  real `create_react_agent` and checks its signature. **Done** — pinned to `>=1.0,<2.0`
  (verified against the installed 1.2.11, whose `create_react_agent` still exposes
  `prompt=`); added `test_create_react_agent_signature_has_prompt_kwarg`, which imports the
  REAL function (not a mock) so a future signature break shows up in CI.

- [x] **11. Single-shot `answer_question` path has no grounding firewall** (pre-existing,
  not new in this branch) — `apps/api/routes/review.py` /
  `adapters/llm/opencode.py::answer_question`. Unlike the new agentic path (which runs
  `sanitize_summary_text` + disposition redaction), the default path's raw LLM output is
  returned to the underwriter with zero citation validation.
  **Fix (optional, larger scope):** route it through `sanitize_summary_text` too now that
  the firewall exists. **Done** — `ask_question` now firewalls the single-shot answer
  through `sanitize_summary_text` (authorized set = retrieved policy chunk IDs + this
  application's finding rule_ids) before returning it - the DEFAULT Q&A path (agentic is
  off by default) is grounded the same way the experimental path always was.

- [x] **12. Pre-agentic hit check can starve the agent of a chance to reformulate** —
  `apps/api/routes/review.py:267` aborts with "no relevant passages" using a plain
  retrieval on the raw question *before* the agentic branch runs, so the agent's own
  tool-driven search (which could rephrase the query) never gets a chance if that first
  pass returns nothing.
  **Fix (optional):** only apply the early abstain when `AGENTIC_QA_ENABLED` is false, or
  let the agent attempt its own search first. **Done** — the early abstain now only fires
  when there are no policy hits AND no application findings AND `AGENTIC_QA_ENABLED` is
  false; otherwise the agent (or the findings-aware single-shot path) gets a chance to
  answer.

## Explanation capability (this session's main feature)

- [x] **20. "Why was this flagged/rejected?" explanation, grounded via RAG + findings** —
  previously Q&A only ever searched the policy corpus; it had no access to the
  application's own deterministic findings, so it couldn't explain a specific rejection
  reason at all - only give generic policy background. **Done:**
  - `apps/api/routes/review.py::_build_findings_context` formats this application's
    findings (rule_id/rule_name/verdict/reason - deterministic, non-LLM-originated,
    citable as `[RULE_ID]`) and feeds it to BOTH the single-shot and agentic Q&A paths
    alongside the usual RAG policy retrieval - every LLM call in the Q&A flow now uses
    RAG (policy) + findings (application), never freeform.
  - `adapters/llm/opencode.py::answer_question` and `apps/api/agent.py`'s system prompt
    rewritten to explicitly instruct: name the rule that fired, quote its reason, explain
    the policy basis in plain language, cite every claim (`[chunk_id]` or `[RULE_ID]`),
    never issue a new disposition.
  - `_finding_evidence_citations` turns an actually-cited finding's `supporting_evidence`
    into the same jump-to-PDF citation shape the policy hits already use, so "why flagged"
    answers are clickable straight to the evidence, not just prose.
  - **UI:** `PolicyQaTab.tsx` (renamed tab "Policy" → "Q&A") now leads with a dedicated
    "Explain: {finding}" button per flagged finding (passed down from
    `RightInspectorPane.tsx`'s `application.findings`), pre-filling a pointed question
    instead of requiring the reviewer to discover this is possible.
  - New tests: `test_opencode_answer_question_includes_findings_context`
    (`tests/unit/test_adapters_llm.py`). TypeScript typechecks clean
    (`npx tsc --noEmit`).

## Cleanup

- [ ] **14. Dead code / redundant logic pass over the branch diff** — sweep the ~54
  changed files (`apps/api`, `core/`, `ml/`, `adapters/`) for unused imports, unreachable
  branches, and duplicated logic introduced across the 4 commits, and simplify/compact code
  where it doesn't change behavior. Concrete leads already spotted in this review:
  - `core/graph/nodes.py:291` duplicates `MAX_PAGES_PER_DOCUMENT`'s value as a literal
    `[:30]` instead of reusing the constant (see item 3 — same fix serves both).
  - `core/extraction/router.py`'s native-fast-path now calls three separate parse
    functions per page instead of one (see item 4) — consolidating them is itself the
    efficiency fix, not just a correctness one.
  - Re-check `core/rag/grounding.py::sanitize_summary_text` vs `validate_llm_narrative`
    for logic that could be shared (citation-authorization checking is duplicated between
    the two) once item 7 is fixed, rather than growing two divergent implementations.
  **Constraint:** no behavior/functionality change — this is style/perf/duplication only,
  verified by the existing test suite passing unchanged (`pytest tests/unit`) after each
  edit. Good candidate for the `/simplify` skill run scoped to this branch's diff.

## Minor

- [ ] **13. `S3Storage._clean_key` silently reinterprets a cross-bucket URI as
  bucket-relative** — `adapters/storage/s3.py:64`. A `s3://<other-bucket>/<key>` URI has
  its scheme stripped and is treated as relative to `self.bucket_name` instead of raising,
  so an API/worker bucket-name mismatch produces a generic `NoSuchKey` instead of a clear
  configuration error.
  **Fix:** raise on bucket mismatch instead of silently stripping.

## RAG correctness (found in follow-up review)

- [ ] **15. Stale BM25 tokens on chunk update** — `core/rag/indexer.py:72-82`,
  `IsolatedIndex.add_chunks`. When a chunk is re-added with the same `chunk_id` but
  updated `text`, `self.chunks[chunk_id]` is updated but `self._corpus_tokens[i]` (the
  parallel list BM25 is built from) is never recomputed — lexical search keeps matching
  the chunk against its old text forever. Not reachable in production today (nothing
  currently re-adds an existing chunk_id — the per-application dossier-indexing pipeline
  that would do this isn't wired in yet), but a live trap for whoever builds it next.
  **Fix:** rebuild `_corpus_tokens[i]` for updated chunks too, or recompute the whole BM25
  corpus from `self.chunks` in id order instead of tracking a parallel list. **Still open.**

## Rate limiting

- [x] **16. Upload rate limit too tight for normal multi-doc dossier upload** —
  `MAX_SUBMISSIONS_PER_MIN` defaulted to 5/min, too low for a 5-document dossier upload
  flow (application form + payslips + bank statement + ITR + KYC) inside one minute.
  **Done** — raised to 30/min in `apps/api/config.py`; `AGENTS.md` and
  `docs/security_report.md` updated to match; integration test (which loops
  `settings.MAX_SUBMISSIONS_PER_MIN` times) verified green at the new value.

## Cross-document identity gap (found in follow-up review)

- [x] **17. No cross-check between two separately uploaded identity documents** —
  `core/graph/nodes.py`, `extract_facts_node`. `"id_card"`, `"kyc"`, `"pan"`, and
  `"aadhaar"` doc types all fed one `applicant` slot gated by `applicant is None` — the
  first identity document processed won, and every subsequent one (e.g. a separately
  uploaded PAN card alongside an Aadhaar/ID card — a common real dossier shape, not an
  edge case) had its facts silently discarded, so a swapped/mismatched identity-document
  pair went completely undetected. RULE-ID-01 only ever compared the single surviving KYC
  doc against payslip/bank/tax records, never against a second identity document.
  **Fix:** `extract_facts_node` now extracts every identity-type document into a new
  `identity_documents` state list (`applicant` stays the first one, for backward
  compatibility with existing consumers); a new rule, **RULE-ID-02**
  (`core/rules/identity.py::audit_identity_documents_consistency`), cross-checks name and
  PAN across every uploaded identity document and cites each document's own page. Only
  emitted when 2+ identity documents were uploaded — a single ID document has nothing to
  cross-check, so the common case gets no new finding. New tests in `tests/unit/test_rules.py`
  (5 cases: single-doc no-op, matching pair, PAN mismatch, name mismatch, name variation).

- [x] **18. Docs/config sync for this session's changes** — `AGENTS.md` (RULE-ID-02 added
  to the rules list; rate-limit line updated to 30/min) and `docs/security_report.md`
  (rate-limit table updated to 30/min) brought in line with the code changes above.

## Allowlist admin tooling

- [x] **19. No way to retroactively authorize a denied user** — `UserModel`'s own
  docstring calls this the "admin flip" case (`AUTHORIZED_EMAILS`/`AUTHORIZED_DOMAINS` env
  vars only seed `authorized` on a user's *first* login; editing them does nothing for
  someone who already tried and got a `users` row with `authorized=false`), but no such
  tool existed. **Done** — added `scripts/authorize_user.py` (`add`/`remove`/`list`
  subcommands) to create-and-authorize or flip any user's row directly against
  `DATABASE_URL`, no manual SQL needed.
