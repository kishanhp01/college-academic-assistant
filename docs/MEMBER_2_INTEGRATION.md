# Member 2 Integration Guide

## What Member 2 implemented

Member 2 added configurable chat-model providers, including Hugging Face text generation; college-document RAG answers; general academic answers; a simple question router; and conditional routing in the existing LangGraph workflow. The college path retrieves and cites document excerpts. The general path answers without document retrieval.

## Architecture

```text
                         USER QUESTION
                               |
                               v
                           LANGGRAPH
                               |
                               v
                             ROUTER
                        /              \
                       v                v
                 COLLEGE PATH       GENERAL PATH
                       |                |
                 FAISS retrieval    Configured LLM
                       |            (Hugging Face when
                 College RAG         selected in .env)
                       \                /
                        \              /
                         v            v
                          FINAL ANSWER
```

The LLM provider is configurable. Hugging Face is one option; OpenAI and Ollama are still supported. The college RAG answer uses the configured LLM with retrieved college-document text as context.

## Important files

- `app/assistant/providers.py` creates the configured chat model.
- `app/assistant/answering.py` creates grounded answers from retrieved college documents and formats source details.
- `app/assistant/general_answering.py` answers general questions without retrieval.
- `app/assistant/router.py` classifies a question as `college` or `general`.
- `app/workflows/academic.py` defines the existing LangGraph workflow and its conditional branches.

## Interface and result fields

The existing workflow entry point is:

```python
from app.workflows.academic import build_academic_graph

graph = build_academic_graph()
result = graph.invoke({"question": user_question})
```

The main result fields are:

- `answer`: answer text for the student.
- `sources`: retrieved source labels and excerpts; empty for general answers.
- `analyzed_query`: trimmed question sent to routing and retrieval.
- `question`: trimmed student question.
- `route`: `college` or `general`.
- `source`: `college_documents` or `general_llm`.

The college branch also keeps retrieved LangChain `documents` in the graph state. An API should return the fields above rather than pass that internal value directly to JSON encoding.

### Example: college question

```json
{
  "question": "What is the attendance requirement?",
  "analyzed_query": "What is the attendance requirement?",
  "route": "college",
  "answer": "<answer grounded in the retrieved college documents>",
  "source": "college_documents",
  "sources": [
    {
      "label": "academic_regulations.pdf (page 2)",
      "excerpt": "<relevant excerpt from the document>"
    }
  ]
}
```

If no documents are retrieved, the answerer says the provided college documents do not contain enough information.

### Example: general question

```json
{
  "question": "What is polymorphism in Java?",
  "analyzed_query": "What is polymorphism in Java?",
  "route": "general",
  "answer": "Polymorphism lets code use a shared interface while different object types provide their own behavior.",
  "source": "general_llm",
  "sources": []
}
```

## Environment configuration

Put settings in the local `.env` file (do not commit it). For Hugging Face, set:

```dotenv
LLM_PROVIDER=huggingface
HUGGINGFACE_API_KEY=your Hugging Face token
HUGGINGFACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
```

Change `HUGGINGFACE_MODEL` to use another supported model. OpenAI and Ollama remain available through their existing `LLM_PROVIDER` choices and settings.

## Flask and frontend integration

Member 3's Flask backend should call the graph and return the student-facing fields through an API. Flask is not currently part of this repository; this is an integration example only and does not add or change Flask code here.

```python
from flask import Flask, jsonify, request

from app.workflows.academic import build_academic_graph

app = Flask(__name__)
academic_graph = build_academic_graph()


@app.post("/api/academic/ask")
def ask_academic_question():
    body = request.get_json(silent=True) or {}
    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "Question cannot be empty."}), 400

    result = academic_graph.invoke({"question": question})
    response_fields = (
        "answer", "sources", "analyzed_query", "question", "route", "source"
    )
    return jsonify({key: result[key] for key in response_fields})
```

Member 4's frontend should send the question to this Flask API and display its response. It should not call Hugging Face or FAISS directly; the backend workflow owns provider and retrieval access.

## Run and test

From the repository root, with `.env` configured, manually invoke the graph with:

```powershell
.\.venv\Scripts\python.exe -c "from app.workflows.academic import build_academic_graph; print(build_academic_graph().invoke({'question': 'What is polymorphism in Java?'}))"
```

Run the Member 2 tests (they use fake models and retrievers, so they need no API key, internet, or real FAISS index):

```powershell
.\.venv\Scripts\python.exe -m pytest -v tests/test_providers.py tests/test_general_answering.py tests/test_router.py tests/test_workflows.py
```

**Windows test-environment note:** the full suite may encounter a `PermissionError` when pytest creates its `tmp_path` for the existing ingestion test under the Windows temporary directory. That is an environment permission issue; it is separate from the Member 2 tests.
