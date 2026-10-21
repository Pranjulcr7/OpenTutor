# Study Lab validation record

## Current reconstruction — 21 October 2026

Baseline: `74f492aa29909e0ddadf450ac7c3c1b2fb3aad02` on the fork's combined
branch. Changes are split into runtime, provider security, retrieval and docs.
Environment: Linux, Python 3.12.14 and Node 24.19.0.

| Check | Result |
|---|---|
| Selected backend regression tests | 79 passed |
| Frontend suite | 40 files, 222 tests passed |
| Next.js production build, including TypeScript | Passed |
| Ruff on new regression tests, verification script and study packet/reviewer | Passed |
| Launcher HTTP smoke test | API OpenAPI, Study Lab, experiments and proxied health all returned 200 |
| Production Next proxy → course list | Both `/api/courses` and `/api/courses/` returned 200 without redirects |
| Production Next proxy → FastAPI Study Lab → SDK → delayed HTTP model fixture | Nonempty answer, HTTP 200 after 35.3 seconds |

The delayed response is a **deterministic fixture**, not a generative model. It
checks that the proxy no longer terminates a request at 30 seconds. The full
backend suite was not run. Selected tests cover authorization before retrieval,
source-free routes, empty/reasoning-only completions through the actual SDK,
timeouts, malformed/empty reviews, credential redaction, dotenv injection,
file permissions, multi-user configuration denial, page-aware PDFs, assignment
indexing and ranking beyond the former candidate cutoff using real SQLite.

Reproduce the automated checks:

```bash
uv pip install --python .venv/bin/python pytest pytest-asyncio ruff
.venv/bin/python -m pytest tests/test_study*.py tests/test_pdf_evidence.py tests/test_ingestion_regressions.py tests/test_security_regressions_authz.py tests/test_provider_config_security.py tests/test_api_unit_basics.py -q -o addopts=''
npm run test:run --prefix apps/web
npm run build --prefix apps/web
```

## Browser observations before this update

A running macOS installation of the previous combined branch returned visible
answers for both an attention question and a pasted binary-search problem, with
no uploaded sources and review off. The tutor also invented `[S1]` citations;
the citation audit correctly flagged them. The source-free prompt has now been
changed to avoid encouraging source IDs when evidence is absent. This does not
ensure the model always follows the instruction.

The browser also showed a course-loading failure. Both forms of the course-list
URL now pass the production-proxy fixture check. The exact cause of an earlier
intermittent blank response on that installation remains unconfirmed.

The local server became unreachable before screenshots could be captured. The
updated build still needs a browser test on the target installation after pulling
and restarting. No private desktop screenshots are included in the repository.

## Earlier live model experiments — 19 October 2026

These measurements came from an earlier patch build whose unpublished checkout
was lost during workspace cleanup. They are historical evidence, **not a live
model validation of the reconstructed build above**.

Ollama 0.40.6, Linux CPU, Qwen3 0.6B tutor, reasoning disabled, output cap 4096:

| Prompt | Latency | Input tokens | Output tokens | Visible answer |
|---|---:|---:|---:|---|
| Attention | 6.6 s | 166 | 188 | Yes |
| Binary search | 9.2 s | 181 | 450 | Yes |
| Follow-up | 7.8 s | 685 | 280 | Yes |

Calls traversed Next proxy → FastAPI → Ollama. They demonstrate response delivery
with that setup; they do not measure factual accuracy or learning gains.

A separate Qwen2.5 0.5B reviewer was tried on three controlled cases: a supported
claim, a contradicted claim and an unsupported date. **0/3 reviews were usable**:
one failed output validation; two attributed claims absent from the answer.
The application correctly retained `not_checked`. This is evidence against
assuming that an arbitrarily small reviewer improves reliability.

## Product evaluation gate

Before proposing the feature upstream, test the updated build with a real target
model and a documented set of topic, code and source-backed questions. Compare
review-on and review-off using the same tutor, retrieval and context budget.
Measure false approvals, missed claims, invalid-review rate, source coverage,
latency and total provider-reported usage. Include a competent retrieval-based
baseline; resending whole PDFs is not a fair sole comparator.

The project has not established API savings, better learning outcomes, reviewer
accuracy, consumer-scale performance or public-hosting security. Learning modes
remain prompt-based and Study Lab lacks persistent mastery tracking. General
runtime/security/retrieval fixes can be considered separately from those larger
product claims. No upstream PR is opened by this work.
