# Validation record — 18 October 2026

Base: OpenTutor `a890519f3632efa14cf24449b366b3b9d901eecf`.
Environment: Linux, Python 3.12.14, Node 24.19.0. This is not a Mac hardware test.

| Check | Result |
|---|---|
| Selected backend packet/reviewer/route/PDF/ingestion/authorization tests | 30 passed |
| Frontend suite including numerical exercises | 39 files, 219 tests passed |
| New Study Lab UI tests plus numerical exercise tests | 2 files, 5 tests passed (3 overlap with the 219 above) |
| TypeScript `tsc --noEmit` | Passed |
| Next.js production build | Passed, including `/study-lab` and `/experiments` |
| Ruff on new Python modules, tests and launcher | Passed |
| API OpenAPI HTTP request | 200 |
| Study Lab HTTP request | 200 |
| Experiments HTTP request | 200 |
| Proxied API health HTTP request | 200 |

The API tests verify course ownership is checked before retrieval/model calls,
oversized input rejection, no route-level retry after tutor timeout, reviewer
input scope, citation auditing, malformed reviewer outputs, false quote IDs,
reviewer failure/cleanup, PDF page boundaries and encrypted-file rejection.
The numerical tests check normalization, shift invariance, temperature behavior,
Bayesian base rates and impossible conditioning events. UI tests check evidence
display, course-change reset and failure without automatic resubmission.

Two old ingestion tests initially failed because they patched the obsolete
`extract_content` call instead of `extract_content_with_title`. The dedicated
fix branch updates the mocks to match the current production boundary. Existing
TypeScript failures in block mappings and test fixtures are isolated in a
second fix branch. The checks above passed after those fixes.

No live generative model was available in this environment. Tutor and reviewer
responses in tests were mocked. No claim of end-to-end answer accuracy,
reviewer effectiveness, API billing savings, delayed learning improvement,
production readiness or Mac latency follows from these checks. The full backend
suite was not run. Browser visual QA of the app is still part of the Mac test.
