<div align="center">

# OpenTutor · Study Lab

### Bring a question. Explore an idea. Test your understanding.

**Topics without uploads · Coding practice · Source-backed explanations · Interactive experiments**

[Quick start](#quick-start) · [Try a session](#try-a-session) · [Privacy](#privacy-and-api-keys) · [Validation](validation.md)

</div>

Study Lab is an experimental extension of OpenTutor for technical study. Ask
about attention, paste a coding problem, or optionally attach course material.
A PDF is **not required**. The combined test branch is `study/all-features`.

| Start with… | Try… |
|---|---|
| A topic | “Teach me attention with one small example, then ask a question.” |
| A coding problem | “Find the first and last target indices in a sorted array. Give one hint.” |
| An interview goal | Select Interview; enter the role, seniority and topic in Goal. |
| Your own material | Upload to a course in the workspace, then select it in Study Lab. |
| A numerical question | Open Experiments; change softmax temperature or a Bayesian base rate. |

## Quick start

Requirements: Git, Python 3.12, Node.js 20.9+, [uv](https://docs.astral.sh/uv/),
and a running [Ollama](https://ollama.com/) server or a supported cloud provider.
Run the following from a directory of your choice:

```bash
git clone --branch study/all-features https://github.com/Pranjulcr7/OpenTutor.git
cd OpenTutor
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r apps/api/requirements-core.txt
npm ci --prefix apps/web
ollama list
```

Use an **exact installed model tag** from `ollama list`. Custom aliases such as
`study-tutor` are optional; the app does not require them. Create a root `.env`
(or edit existing keys without discarding other settings):

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=your-installed-model-tag
LLM_REQUIRED=true
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODE=skip
AUTH_ENABLED=false
```

Replace `your-installed-model-tag` before starting. This configuration is for
local single-user use; keep the services on loopback.

```bash
.venv/bin/python scripts/run_study_lab.py
```

Open **http://127.0.0.1:3001/study-lab**. The launcher starts API and UI, binds
both to `127.0.0.1`, and uses the root `.env` for startup and Settings updates.
`LOCAL_ENV_FILE` can select another file. Stop both services with Ctrl+C.

<details>
<summary><strong>Already installed? Update without reinstalling</strong></summary>

Stop the running launcher. From the repository root:

```bash
git status --short
git fetch origin
git switch study/all-features
git pull --ff-only origin study/all-features
.venv/bin/python scripts/run_study_lab.py
```

Keep your `.env` and model choice. If Git reports local edits or divergence,
resolve them before pulling; do not reset or overwrite your files. Rerun the
package installation commands only if dependency files changed.

</details>

## Try a session

1. Leave **Source course** at **No sources · general knowledge**, keep review off,
   and choose Explain. Ask a topic question or paste a coding problem.
2. Read the example, then answer the tutor's question. Use Practice to request
   one question at a time; use Interview with a role and seniority in Goal.
3. Open **Explore the numbers** for softmax and Bayes exercises. Predict an
   outcome, move a control, and explain the result. These are deterministic
   calculations; they do not run model-generated code.
4. For source-backed study, upload material through the main workspace, wait
   for ingestion, then select that course. Check source excerpts and page
   numbers against the original document.
5. Optionally enable the independent reviewer. Inspect its individual claims
   and quoted evidence; “supported” is a model judgment, not proof of truth.

Changing course or reloading clears the Study Lab conversation. Chat history
is currently browser-session state, not a durable learner record.

<details>
<summary><strong>Course workspace preview (existing OpenTutor demo)</strong></summary>

![OpenTutor course workspace with chapters, notes and quiz blocks](../assets/demo-workspace-full.png)

Use the existing course workspace for uploaded materials, notes and quizzes.
Study Lab is a separate page at `/study-lab`; its conversation does not update
this workspace's mastery tracker. This screenshot is the upstream demo, not a
capture of the new Study Lab flow. Fresh Study Lab screenshots are pending the
updated local browser test.

</details>

### What happens to context?

The tutor receives the question, goal, bounded recent conversation and selected
course excerpts. This route loads no global user memory. Evidence is deduplicated
and budgeted; token estimates and provider-reported counts are shown separately.
The estimator is `cl100k_base`, which can differ from a local model's tokenizer.

Follow-up retrieval combines the current question with bounded keywords from
the latest user turn. It is lexical context expansion, not semantic query
rewriting. SQL ranks matching passages before applying the result limit.
Assignments and exam documents are searchable as well as retaining their
specialized records. Older uploads affected by missing indexing need re-ingestion.

### Optional reviewer

```dotenv
STUDY_REVIEWER_MODEL=your-installed-reviewer-tag
STUDY_REVIEWER_BASE_URL=http://localhost:11434/v1
STUDY_REVIEWER_API_KEY=
STUDY_REVIEWER_TIMEOUT_SECONDS=30
```

The separate model receives the latest answer, question, goal, last assistant
exercise and retrieved evidence. It does not receive the full conversation.
JSON-object output is requested, then claims, source IDs and exact quoted
substrings are validated. Empty or malformed reviews remain **not checked**.
No evidence means there is no source-based check; the reviewer cannot validate
general knowledge without evidence. It never falls back to the tutor.

A smaller model is not automatically a useful reviewer. The initial tiny-model
experiment produced no usable reviews; see [the validation record](validation.md).
Review is off by default and is not a guarantee against hallucination.

## Privacy and API keys

- Settings stores keys in the backend `.env`, with owner-only `0600` file
  permissions on supported systems. **This is plaintext storage, not encryption.**
- Saved keys are never returned by the runtime configuration endpoint, even
  partially. The UI shows a fixed mask. Draft keys are sent to the backend when
  testing or saving; use loopback locally and authenticated HTTPS for deployments.
- Configuration values reject control characters, and dotenv values are quoted
  to prevent injecting additional settings. Validation and tested provider-error
  responses omit submitted secrets.
- Global provider settings, connection tests and model discovery are unavailable
  in multi-user mode. This does not make the prototype ready for public hosting.
- A cloud provider receives submitted study content. The tutor retains OpenTutor's
  existing provider selection/fallback behavior: configure only providers you
  intend to use. Optional ingestion may make separate model calls.
- Keep `.env`, private documents and raw logs out of Git. Review logs before
  sharing them. These targeted checks are not a complete security audit.

## Troubleshooting

| Symptom | Check |
|---|---|
| No answer | Settings → provider/model; verify the exact tag with `ollama list`. A blank completion now produces an actionable error instead of an empty success. |
| Model thinks but emits no answer | Some reasoning models exhaust their output limit before answering. If supported by your model/server, try the optional controls below. |
| Request times out | Tutor default is 120 seconds; configurable up to 300. Reviewer default is 30, up to 120. The UI/proxy allow 435 seconds for both. No automatic retry. |
| Course list fails | The combined branch fixes the course-list proxy redirect. Restart the launcher after updating. |
| Review says not checked | Check reviewer availability, JSON support and evidence. Do not interpret this as a passed review. |
| Answer has unknown citations | The UI flags source IDs absent from the packet. General-knowledge mode tells the model not to cite nonexistent sources; models can still ignore instructions. |
| PDF lacks equations or diagrams | Current extraction is native text with page references and quality flags, not OCR or semantic figure understanding. |

Optional Ollama controls (defaults preserve the model/server defaults):

```dotenv
STUDY_TUTOR_TIMEOUT_SECONDS=120
OLLAMA_REASONING_EFFORT=
OLLAMA_MAX_TOKENS=0
```

For a compatible reasoning model, `OLLAMA_REASONING_EFFORT=none` and
`OLLAMA_MAX_TOKENS=4096` may help. Support varies; these are not universal model
settings. Restart after editing `.env`. A nonempty answer stopped at the output
limit is shown with a truncation warning.

### Verify delivery with your actual model

With the app already running, in another terminal from the repository root:

```bash
.venv/bin/python scripts/verify_study_lab.py
```

This makes three real tutor calls through the UI proxy: attention, binary search
and a follow-up. It prints latency, token counts and citation/truncation flags,
without printing keys or response bodies. If authentication is enabled, supply
`OPENTUTOR_TEST_TOKEN` through your environment. A pass proves response delivery,
not accuracy. `run_study_lab.py --smoke-test` only checks server startup and HTTP
responses; it does not test a model.

## Contribution scope

| Branch | Scope |
|---|---|
| `feat/bounded-study-lab` | Original study route, UI and context budgets |
| `feat/latest-answer-review` | Original optional independent reviewer |
| `feat/page-aware-pdf` | Native page-aware PDF extraction |
| `feat/interactive-study-experiments` | Softmax and Bayes exercises |
| `fix/study-runtime` | Empty answers, local-model controls, deadlines, UI errors and proxy behavior |
| `fix/provider-config-security` | Key masking, safe config persistence and error handling; stacked on runtime |
| `fix/study-source-retrieval` | Searchable classified documents and contextual ranking; stacked on security |
| `docs/study-lab-guide` | Public setup guide and live delivery check; stacked on retrieval |
| `study/all-features` | Combined integration branch for testing |

Existing `fix/upstream-typecheck` and `fix/ingestion-test-mocks` branches remain.
For upstream review, extract general fixes onto current upstream main and open
small focused PRs after testing. Discuss larger additions according to
[CONTRIBUTING.md](../../CONTRIBUTING.md). No upstream PR is opened automatically.

**Still missing:** persistent Study Lab sessions, a stateful diagnostic/hint/
feedback loop, mastery updates, video processing, general image understanding,
symbolic/code correctness checks and measured learning gains. The current
learning modes are prompts, not a validated adaptive teaching algorithm.
