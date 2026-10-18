# Study Lab prototype

An experimental extension of OpenTutor for adult technical study. Use the
`study/all-features` branch to try the complete prototype. Upstream baseline:
`a890519f3632efa14cf24449b366b3b9d901eecf`.

## What is implemented

| Feature | Implementation | Scope and limitation |
|---|---|---|
| Bounded study chat | `/study-lab`: explain, practice, interview and recall modes; goal/level input; course selector | A prompted learning workflow, not a validated adaptive teaching algorithm |
| Explicit context | Course-authorized keyword retrieval, deduplicated evidence, complete recent messages, token audit | Keyword retrieval can miss relevant passages; no global or cross-course memory is loaded in this route |
| Independent reviewer | Optional separate OpenAI-compatible model; latest answer + question + goal + last assistant task + evidence | Model-selected claims only; no guarantee of completeness, truth or mathematical correctness |
| Evidence checking | Supplied citation IDs and exact quoted substrings validated in code | A real quote can still be irrelevant; semantic entailment remains a model judgment |
| Page-aware PDFs | Native text, page-local chunks, page numbers and sparse-text / visual-object flags | No OCR, equation recognition, figure crops or semantic table reconstruction |
| Interactive exercises | `/experiments`: softmax/temperature and Bayesian spam classification | Two curated numerical tools; no arbitrary generated-code execution |
| Model choice | Existing OpenTutor tutor providers; separately configured reviewer | Local Ollama or a cloud tutor plus local reviewer; no API keys are supplied |
| Local launcher | One command starts API and UI on loopback; optional HTTP smoke test | Intended for local single-user testing |

Existing OpenTutor upload, notes, quizzes, flashcards and FSRS interfaces remain
available through the main workspace. The Study Lab does not add a new durable
learner model or connect its chat attempts to FSRS mastery updates. Sessions live
in browser memory and clear on reload or reset. Changing course clears the chat.

Not implemented: video generation, video transcription/keyframe retrieval,
general image understanding, automatic verification-driven answer rewriting,
symbolic proof checking, personalized mastery tracking in Study Lab, a full
evaluation dashboard, or a public multi-user service. These need separate work
and evaluation. Do not present this prototype as a hallucination-free tutor.

## Set up on macOS

The following starts with local models and requires no paid API calls. Install
[Ollama for macOS](https://ollama.com/download/mac), open the app, and keep it
running. Install Git, Node.js (20.9+; tested here on Node 24), and uv. If you use
Homebrew, `brew install node uv` installs the latter two. Git may prompt for the
Apple command-line tools on first use.

```bash
mkdir -p ~/Documents/Projects
cd ~/Documents/Projects
git clone --branch study/all-features https://github.com/Pranjulcr7/OpenTutor.git
cd OpenTutor
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r apps/api/requirements-core.txt
npm ci --prefix apps/web
```

Download and name the two local models:

```bash
ollama pull qwen2.5:7b
ollama pull llama3.2:3b
ollama create study-tutor -f docs/study-lab/Modelfile.tutor
ollama create study-reviewer -f docs/study-lab/Modelfile.reviewer
```

These are baseline model choices for testing, not benchmark winners. The model
files specify a 16K context window to leave room beyond the application's input
budget, and cap generated output. Model tokenizers differ from our estimator.
The two downloaded quantizations are approximately 4.7 GB and 2.0 GB; runtime
memory is larger because of caches and other processes. Your 24 GB Mac is a
reasonable starting point, but Mac latency and memory usage have not been
measured. A smaller reviewer may return invalid JSON or miss technical errors;
the UI will show a failed check, not silently promote it to a successful one.

Create a new `.env` in this freshly cloned repository with:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=study-tutor
OLLAMA_BASE_URL=http://localhost:11434
STUDY_REVIEWER_MODEL=study-reviewer
STUDY_REVIEWER_BASE_URL=http://localhost:11434/v1
STUDY_REVIEWER_API_KEY=
EMBEDDING_MODE=skip
AUTH_ENABLED=false
```

If `.env` already exists, edit these keys without discarding existing settings.
This configuration and launcher are for local use. The launcher binds both
services to `127.0.0.1`, reads the root `.env`, and starts the web-to-API proxy.

```bash
.venv/bin/python scripts/run_study_lab.py
```

Open **http://127.0.0.1:3001/study-lab**. Numerical exercises are at
**http://127.0.0.1:3001/experiments**. Stop both services with Ctrl+C.

For a cloud tutor, use the provider keys from the root `.env.example` while
keeping the reviewer settings local. Selected questions and excerpts will then
be transmitted to that tutor provider. The tutor follows OpenTutor's existing
provider-selection/fallback behavior; the reviewer never falls back to the
tutor. Do not use personal study documents until you are comfortable with the
chosen provider settings.

## First test session

1. Open the main workspace, create a course, and upload a short text-based PDF.
   Wait for ingestion to finish. Upload processing may also trigger existing
   OpenTutor classification/auto-generation calls outside the Study Lab audit.
2. Open Study Lab and select that course. Set a goal such as “ML interview;
   explain attention masking and then test me.” Start with a 2,000-token evidence
   budget and review turned off.
3. Ask a direct question whose answer you can locate in the PDF. Open the source
   disclosures; compare the quoted text and physical PDF page numbers.
4. Turn review on and repeat a comparable question. Inspect claim verdicts,
   quotes, reviewer input/output usage, and added latency. “Supported” means the
   reviewer judged support from the shown evidence, not that correctness is proven.
5. Ask something absent from the document, then try a scanned or diagram-heavy
   page. Expect missing-evidence / extraction limitations. A reviewer cannot
   recover information that was never extracted.
6. Try practice and interview modes. Answer before requesting a hint. Use the
   softmax and Bayes sliders, predicting the change before moving them.

Record false approvals, missed claims, invalid JSON, useful source coverage,
latency and total tutor-plus-reviewer usage. Compare review-on against the same
tutor and evidence policy with review-off. Do not compare only against an
inefficient baseline that resends whole PDFs every turn.

## Branches

| Branch | Purpose |
|---|---|
| `feat/bounded-study-lab` | Chat route/UI, retrieval packet and token audit |
| `feat/latest-answer-review` | Reviewer configuration, validation and UI; stacked on bounded study lab |
| `feat/page-aware-pdf` | Native page-aware extraction and ingestion integration |
| `feat/interactive-study-experiments` | Numerical exercises |
| `fix/upstream-typecheck` | Missing summary-block mappings and typed test fixture defaults |
| `fix/ingestion-test-mocks` | Update old tests to mock the current extraction function |
| `study/all-features` | All features, fixes, integration tests, launcher and documentation |

The combined branch contains final integration polish and tests in addition to
the feature merges. Before upstream PRs, port the relevant integration changes
back into each focused branch and discuss the larger additions as requested by
upstream CONTRIBUTING.md. No upstream PR has been opened.

## Validation and troubleshooting

Validation in the development environment: 30 selected backend tests passed;
the existing frontend suite with the new numerical tests passed (219 tests),
and the two newly added Study Lab UI tests passed separately. TypeScript passed.
The launcher returned HTTP 200 for API OpenAPI, Study Lab, experiments and proxied
health endpoints. See `validation.md` for the final build result.

Model calls in these automated tests are mocked. No live generative tutor or
reviewer ran in this environment. Consequently, correctness improvement,
consumer-scale performance, Mac performance and actual API savings remain
unvalidated.

```bash
uv pip install --python .venv/bin/python pytest pytest-asyncio ruff
.venv/bin/python -m pytest tests/test_study_packet.py tests/test_study_reviewer.py tests/test_study_routes.py tests/test_pdf_evidence.py tests/test_ingestion_regressions.py tests/test_security_regressions_authz.py -q -o addopts=''
npm run test:run --prefix apps/web
npm run build --prefix apps/web
.venv/bin/python scripts/run_study_lab.py --smoke-test
```

Run build and smoke-test sequentially. If a port is occupied, stop the previous
server; alternatively pass `--api-port 8001 --web-port 3002` and update CORS
origins for the new web port. If the tutor is unavailable, check `ollama list`
and confirm the Ollama app is running. If review times out, warm the model once
with `ollama run study-reviewer`, reduce the evidence budget, or select another
reviewer. Invalid reviewer output is visible as “not checked.” Restart the
launcher after changing `.env`.

Source references for local model setup:
[Ollama quickstart](https://docs.ollama.com/quickstart),
[Qwen2.5 7B](https://ollama.com/library/qwen2.5:7b),
[Llama 3.2 3B](https://ollama.com/library/llama3.2:3b).
