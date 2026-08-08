# AlphaVest Capital — AI Investment & Financial Research Assistant

Capstone Project 3 implementation. Built with LangChain + Streamlit, using **OpenRouter**
as the LLM provider (same pattern as `basic.ipynb`).

## Setup

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then add your OPENROUTER_API_KEY
streamlit run app.py
```

## What's implemented (mapped to the handbook's modules)

| Module | Feature | File(s) |
|---|---|---|
| 1 | Chat interface | `app.py` |
| 2 | Financial news search (DuckDuckGo) | `tools/search_tools.py` |
| 3 | Company research agent (news + Wikipedia + calc tools, ReAct agent) | `agents/research_agent.py` |
| 4 | Annual report RAG (PDF upload → Chroma) | `rag/loader.py`, `rag/vectorstore.py` |
| 5 | Parallel multi-company comparison | `agents/coordinator.py` → `compare_companies()` |
| 6 | Structured investment report (Pydantic) | `models/schemas.py` |
| 7 | Sequential pipeline (research → PDF → merge → report) | `agents/coordinator.py` → `run_sequential_pipeline()` |
| 8 | Conditional routing (RunnableBranch) | `agents/coordinator.py` → `route_query()` |
| 9 | Short-term (session), persistent (SQLite), long-term (investor profile) memory | `memory/db.py` |
| 10 | CAGR / growth % / ROI / comparison table tools | `tools/financial_tools.py` |
| 11 | Email | *Not wired up — see note below* |
| 12 | Google Drive | *Optional — not implemented* |

## Notes / things to know before you demo this

- **Embeddings run locally**, not through OpenRouter — OpenRouter proxies chat
  completions but not the embeddings endpoint, so `rag/vectorstore.py` uses a free
  local HuggingFace model (`all-MiniLM-L6-v2`) instead. No extra API key needed for RAG.
- **`openrouter/free` may not support tool calling or `with_structured_output`
  reliably.** If the research agent or structured reports throw errors, switch
  `OPENROUTER_MODEL` in `.env` to a tool-calling-capable model such as
  `meta-llama/llama-3.1-8b-instruct` or `google/gemini-flash-1.5`.
- **Gmail sending isn't wired in.** The handbook's simplest path is generating the
  draft with the LLM and sending via `smtplib` + a Gmail app password — add this as
  a follow-up if your demo requires it.
- **Comparison/company extraction is regex-based** (`extract_companies` in
  `agents/coordinator.py`), not an LLM call — good enough for "Compare Google,
  Microsoft and Amazon" style phrasing but not much more. Swap for an LLM-based
  extractor if you need more robustness.

## Try these in the chat box

- `Research NVIDIA`
- `Compare Google, Microsoft and Amazon`
- `Calculate CAGR for a stock that went from 100 to 250 over 5 years`
- `Remember that I prefer low-risk technology investments`
- Upload an annual report PDF, build the knowledge base, then ask: `Summarize the risk factors`
