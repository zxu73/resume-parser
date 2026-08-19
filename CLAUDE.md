# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BetterCV — an AI-powered resume optimization platform. Users upload a `.docx` resume and paste a job description, then a multi-agent pipeline evaluates fit, rates bullets, suggests rewrites, and optionally recommends experience swaps from a pool.

## Architecture

- **Frontend**: React 19 + TypeScript + Vite, styled with Tailwind CSS and Radix UI components. Path alias `@/*` maps to `./src/*`.
- **Backend**: FastAPI + LangGraph for multi-agent orchestration. Agent nodes call OpenAI via `langchain_openai.ChatOpenAI` with `.with_structured_output(...)`; the chat and clarifying-question endpoints call LiteLLM directly. Model is configurable via the `REASONING_MODEL` env var (defaults to `gpt-4o-mini`).
- **Document handling**: python-docx for `.docx` manipulation, PyPDF2/pymupdf for PDFs.

### Agent Pipeline (sequential)

1. **Evaluation** (`evaluate_only_graph`, single node) — exhaustive keyword extraction, STAR analysis, produces `EvaluationResponse` (scores, strengths, weaknesses, missing skills) plus **anchored clarifying questions**. Every `ClarifyingQuestion` carries a `target_bullet`: the verbatim resume line the question is about ("when you did X, did you use <missing skill>?"). `evaluate_node` runs each anchor through `_snap_to_resume`, which fuzzy-snaps a lightly-paraphrased anchor back to real resume text and blanks it otherwise — a near-miss anchor would produce a `current_text` the document editor can never match.
2. **Rating** (`rate_only_graph`, fanned out) — takes the user's answers and produces:
   - `keyword_suggestions`: rewrites that insert missing JD skills in STAR format. `keywords_added` must be non-empty, each keyword a literal substring of `suggested_text`.
   - `star_suggestions` (target 5-10): STAR-format improvements only. `keywords_added` must be `[]`.
   - Each bullet appears in at most one section. All section invariants are enforced in one place — `RatingResponse.normalize_sections` in `agent.py` — at pydantic validation time; `app.py` does no post-processing. Governed by anti-hallucination rules in `backend/src/agent/guidelines.md`.
3. **Experience Optimizer** (`optimizer_graph`, single node, optional) — scores resume vs pool experiences on JD fit, recommends 1-for-1 swaps only if pool score exceeds resume by 20+ points.

Graphs are invoked from `app.py` with `await graph.ainvoke(state)`. Evaluation and rating are split into separate graphs (and separate endpoints) so the clarifying-questions step can run in between — that HTTP round-trip is the human-in-the-loop step, which is why no checkpointer is needed. Nothing persists across requests: all context must be passed in the state dict (`ResumeState` / `OptimizerState`).

#### Rating fan-out

`rate_only_graph` is the only multi-node graph. `plan_rating` groups the user's confirmed answers **by `target_bullet`** and emits one `Send` per bullet, plus a sweep and an overall pass, all running concurrently:

```
         ┌─> rate_bullet  (one per confirmed bullet, parallel)  ─┐
START ───┼─> rate_sweep   (missing skills no answer covered)    ─┼─> assemble ─> END
         └─> rate_overall (detailed_ratings + STAR-only polish) ─┘
```

Design constraints worth preserving:

- **Group by bullet, not by skill.** Two skills confirmed for the same line must be handled by one pass; otherwise parallel branches emit two competing rewrites of the same bullet and the second can never be applied (the DOCX replacement matches on the pre-edit text).
- **`rate_bullet` retries** (`_MAX_LANDING_RETRIES`) while a confirmed skill is missing from `suggested_text`. Multi-word JD phrases like `Team leadership and mentoring` get reworded to read better, then stripped by `ParaphrasingSuggestion.strip_missing_keywords` — leaving the user nothing for a question they answered. The prompt supplies carrier-clause examples for exactly this.
- **Answers denying experience** (`_is_denial`) are dropped before fan-out, so a "No" never forces a keyword in.
- `keyword_parts` / `star_parts` in `ResumeState` need `Annotated[list, operator.add]` reducers — concurrent branches write the same key, and plain fields raise `InvalidUpdateError`.
- Answers missing `skill_targeted` / `target_bullet` (older clients) fall through to the sweep, so the endpoint stays backward compatible.

### Key Backend Files

- `backend/src/agent/app.py` — FastAPI app, all API routes, graph invocation
- `backend/src/agent/agent.py` — prompts, node functions, state TypedDicts, compiled graphs, pydantic output schemas (`RatingResponse` with `keyword_suggestions`/`star_suggestions`)
- `backend/src/agent/tools.py` — document extraction and AI analysis helpers
- `backend/src/agent/guidelines.md` — bullet rewriting rules, shared by all three rating prompts via `_STAR_AND_KEYWORD_BASE`

### Key Frontend Files

- `frontend/src/App.tsx` — main workflow state machine (upload → analyze → dashboard)
- `frontend/src/components/AnalysisDashboard.tsx` — scores, recommendations, preview; BetterCV Score = 40% keyword match + 35% overall quality + 25% experience relevance
- `frontend/src/components/ResumePreview.tsx` — three-pane change review UI (current bullet / suggestion / live doc preview), approve/skip per suggestion, docx download
- `frontend/src/components/ExperienceManager.tsx` — manage experience pool for swaps
- `frontend/src/components/SwapReview.tsx` — table of resume-vs-pool comparisons, accept/reject swaps
- `frontend/src/components/ClarifyingQuestions.tsx` — shows each question with the resume bullet it is anchored to; submits `{question, answer, skill_targeted, target_bullet}` so the rewriter knows which line to change
- `frontend/src/components/ChatBot.tsx` — floating assistant (bottom-right); sends message + history + resume + JD to `/chat`; returned suggestions join the ResumePreview queue
- `frontend/src/hooks/` — `useResumeUpload.ts`, `useResumeEvaluation.ts`, `useExperienceSwap.ts` encapsulate all API calls
- `frontend/src/types/analysis.ts` — shared TypeScript types (`StructuredRating` has `keyword_suggestions`/`star_suggestions`)

## Critical Implementation Invariant

`current_text` in every suggestion must be copied **character-for-character** from the resume (no whitespace normalization, no typo fixes). The DOCX/PDF replacement logic finds paragraphs by exact text match; any deviation breaks the replacement silently. This constraint is enforced in `guidelines.md` and must be preserved in any agent prompt changes.

## Development Commands

### Run both servers concurrently
```
make dev
```

### Frontend only (Vite dev server on :5173, proxies API to :8000)
```
cd frontend && npm run dev
```

### Backend only (Uvicorn on :8000)
```
cd backend && uvicorn src.agent.app:app --reload --port 8000
```

### Backend linting and formatting (from `backend/`)
```
make lint          # ruff check + ruff format --diff + mypy --strict
make format        # auto-fix formatting
make spell_check   # codespell check
make spell_fix     # codespell auto-fix
```

### Backend tests (from `backend/`)
```
make test                         # all unit tests
make test TEST_FILE=tests/unit_tests/test_foo.py  # single file
make test_watch                   # watch mode
make extended_tests               # extended test suite
```

Package manager: `uv` (backend), `npm` (frontend).

## Environment Variables

- `OPENAI_API_KEY` — required for AI model calls
- `REASONING_MODEL` — OpenAI model identifier used by both ChatOpenAI and LiteLLM (default: `gpt-4o-mini`)

## Deployment

Docker multi-stage build (Node 20 → Python 3.11) or Render.com (`render.yaml`). Production entry: `uvicorn src.agent.app:app` with `PYTHONPATH=backend/src`. Frontend dist is served as static files from the FastAPI app.

Uploaded documents are written to `tempfile.gettempdir()` and never deleted — they accumulate unbounded in long-running deployments.
