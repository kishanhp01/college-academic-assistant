# College Academic Assistant

A Streamlit-first academic assistant demo built with Python, LangChain, LangGraph, Hugging Face Sentence Transformers, and FAISS. It supports general academic Q&A, grounded answers from college documents once those are provided, and personalized study plans.

## Architecture

- **Streamlit UI:** presents the dashboard, chatbot, study planner, and session chat history.
- **Academic Q&A:** Streamlit calls the existing `build_academic_graph()`. Its router sends general questions to the configured LLM provider and college questions to retrieval and grounded answer generation.
- **College RAG:** PDF/TXT files are loaded, split into chunks, embedded, and saved in a local FAISS index. College answers use retrieved chunks and show available source details. The repository currently has no college documents or production index, so real college RAG is not yet available.
- **Study planner:** uses the existing study-plan workflow to generate and modify plans based on subjects, exam date, available time, difficulty, preferences, missed sessions, and changed priorities.
- **Chat history:** successful conversations are kept in the current Streamlit session only. They are not shared across sessions or saved by this UI to the Flask database.

The name-entry screen is **demo/session access**, not authentication. Do not enter passwords or sensitive personal information. Flask and the separate HTML frontend are optional secondary components and are not required for the Streamlit demo.

## Install

Python 3.11 or newer is required. From the project root in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

## Configure an LLM provider

Copy `.env.example` to `.env` and set the provider and model you intend to use:

- All providers: `LLM_PROVIDER` and `LLM_MODEL`.
- `openai`: `LLM_API_KEY`.
- `openai_compatible`: `LLM_API_KEY` and `LLM_BASE_URL`.
- `ollama`: a locally available `LLM_MODEL`; `LLM_BASE_URL` is optional.
- `huggingface`: `HUGGINGFACE_API_KEY` and `HUGGINGFACE_MODEL`.

`EMBEDDING_MODEL` selects the Sentence Transformers model used when building the document index. The first index build may download that model. Keep credentials in `.env`; never commit real keys.

## Start the Streamlit demo

```powershell
.venv\Scripts\python.exe -m streamlit run app/ui/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501).

## REAL COLLEGE DATA SETUP

1. Place approved college PDF or UTF-8 TXT files in:

   ```text
   data/documents/
   ```

2. Build or refresh the local FAISS index:

   ```powershell
   .venv\Scripts\python.exe -m app.ingestion.cli
   ```

3. Start Streamlit:

   ```powershell
   .venv\Scripts\python.exe -m streamlit run app/ui/streamlit_app.py
   ```

4. Open [http://localhost:8501](http://localhost:8501).

The loader scans subfolders. Scanned image-only PDFs need OCR before ingestion. The generated index is stored under `data/index/` and is ignored by Git. Rebuild it after changing documents. The ingestion command reports an error when no supported documents are present. No real college data is included in this repository.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The tests use fake providers and deterministic test embeddings where appropriate; they do not require a real LLM API key. Flask HTTP tests require Flask to be installed. Some Windows environments may prevent pytest from creating or scanning its temporary directories.

## Limitations

- College-specific answers require approved source documents and a successfully built FAISS index. Until then, the UI shows a friendly knowledge-base message for college questions.
- General LLM answers require a configured, reachable provider.
- Study plans and chat history in the Streamlit demo are session-local; this UI does not use Flask authentication or persistent chat history.
