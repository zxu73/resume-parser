# BetterCV backend (LangGraph)

this backend `requires-python = ">=3.11,<4.0"`

install the app using [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
```

now run the FastAPI app with uvicorn

```bash
uvicorn src.agent.app:app --reload --port 8000
```

The agent pipeline is three compiled LangGraph graphs in `src/agent/agent.py`
(`evaluate_only_graph`, `rate_only_graph`, `optimizer_graph`), invoked from
`src/agent/app.py`.
