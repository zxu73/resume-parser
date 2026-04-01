# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BetterCV — an AI-powered resume optimization platform. Users upload a `.docx` resume and paste a job description, then a multi-agent pipeline evaluates fit, rates bullets, suggests rewrites, and optionally recommends experience swaps from a pool.

## Architecture

- **Frontend**: React 19 + TypeScript + Vite, styled with Tailwind CSS and Radix UI components. Path alias `@/*` maps to `./src/*`.
- **Backend**: FastAPI + Google ADK (Agent Development Kit) for multi-agent orchestration. AI calls go through LiteLLM to OpenAI models (configurable via `REASONING_MODEL` env var, defaults to `gpt-4o-mini`).
- **Document handling**: python-docx for `.docx` manipulation, PyPDF2/pymupdf for PDFs.

### Agent Pipeline (sequential)

1. **Evaluation Agent** — exhaustive keyword extraction, STAR analysis, produces `EvaluationResponse` (scores, strengths, weaknesses, missing skills, weak bullets).
2. **Rating Agent** — detailed scoring + 5–8 priority paraphrasing suggestions. Governed by strict anti-hallucination rules in `backend/src/agent/guidelines.md`: exact text matching, no fabricated metrics, keywords in suggestions must match `keywords_added`.
3. **Experience Optimizer Agent** (optional) — scores resume vs pool experiences on JD fit, recommends 1-for-1 swaps only if pool score exceeds resume by 20+ points.

### Key Backend Files

- `backend/src/agent/app.py` — FastAPI app, all API routes, ADK runner setup
- `backend/src/agent/agent.py` — agent definitions and output schemas
- `backend/src/agent/tools.py` — document extraction and AI analysis helpers
- `backend/src/agent/guidelines.md` — bullet rewriting rules loaded into Rating Agent prompt

### Key Frontend Files

- `frontend/src/App.tsx` — main workflow state machine (upload → analyze → dashboard)
- `frontend/src/components/AnalysisDashboard.tsx` — scores, recommendations, preview
- `frontend/src/components/ExperienceManager.tsx` — manage experience pool for swaps
- `frontend/src/types/analysis.ts` — shared TypeScript types for analysis results

## Development Commands

### Run both servers concurrently
```
make dev
```

### Frontend only (Vite dev server on :5173, proxies API to :8000)
```
cd frontend && npm run dev
```

### Backend only (Google ADK dev server)
```
cd backend && adk web
```

### Backend linting and formatting (from `backend/`)
```
make lint          # ruff check + ruff format --diff + mypy --strict
make format        # auto-fix formatting
```

### Backend tests (from `backend/`)
```
make test                         # all unit tests
make test TEST_FILE=tests/unit_tests/test_foo.py  # single file
make test_watch                   # watch mode
```

Package manager: `uv` (backend), `npm` (frontend).

## Environment Variables

- `OPENAI_API_KEY` — required for AI model calls
- `REASONING_MODEL` — LiteLLM model identifier (default: `gpt-4o-mini`)

## Deployment

Docker multi-stage build (Node 20 → Python 3.11) or Render.com (`render.yaml`). Production entry: `uvicorn src.agent.app:app`. Frontend dist is served as static files from the FastAPI app.
