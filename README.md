# College Academic Assistant

A beginner-friendly Python application that answers questions using college documents and creates adaptable study plans. It combines LangChain, LangGraph, Hugging Face sentence embeddings, and a local FAISS index.

## Requirements

Python 3.11 or newer. The first run of Hugging Face embeddings may download the configured model.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

## Configure

Copy `.env.example` to `.env`, then set `LLM_PROVIDER` and `LLM_MODEL`. Supported choices are `openai` (provide `LLM_API_KEY`), `openai_compatible` (provide `LLM_API_KEY` and `LLM_BASE_URL`), and `ollama` (provide the model name and optional `LLM_BASE_URL`; no API key is needed). Keep secrets in `.env`; it is ignored by Git.

## Add documents and index them

Place college PDF and TXT files in `data/documents/`. Real college documents are intentionally not included. Build or refresh the local index with:

```powershell
python -m app.ingestion.cli
```

The index is stored under `data/index/` and ignored by Git. Re-run the command after changing source documents.

## Run the app

```powershell
streamlit run app/ui/streamlit_app.py
```

The app offers academic Q&A with source references, an ingestion/re-index button, and study-plan generation and revision.

## Run tests

```powershell
python -m pytest
```

Tests exercise parsing, chunking, retrieval ranking, graph behavior, and study-plan generation without requiring an API key or downloading embedding models.
