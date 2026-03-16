# CodeRAG — Chat with Any GitHub Repository

A RAG pipeline that lets you ask natural language questions about any GitHub codebase using Endee Vector DB and Google Gemini.

## How it works
```
GitHub URL → chunker.py → data_ingestion.py → dataadd.py → main.py → answer
```

## File structure
```
CodeBase/
├── chunker.py          # fetch repo from GitHub URL + split into chunks
├── data_ingestion.py   # embed chunks using Gemini embedding model
├── dataadd.py          # create Endee index + upsert vectors
├── chatting.py         # query pipeline + LLM answer generation
└── main.py             # entry point, ties everything together
```

## Stack

| Layer | Tool |
|---|---|
| Fetching | GitHub REST API |
| Chunking | Sliding window — 20 lines, 4-line overlap |
| Embedding | `gemini-embedding-2-preview` — 768 dims |
| Vector DB | Endee — cosine similarity |
| LLM | Google Gemini |

## Setup
```bash
pip install endee langchain-google-genai python-dotenv requests
```

Create a `.env` file:
```
GOOGLE_API_KEY=your_google_key
GITHUB_API_KEY=your_github_token
```

## Run
```bash
# 1 — fetch repo and save chunks to disk
python chunker.py

# 2 — embed chunks and load vectors into Endee
python data_ingestion.py

# 3 — start chatting
python main.py
```

## Notes

- Vector dimension is fixed at **768** — must match in both `data_ingestion.py` and `dataadd.py`
- If you change the dimension, delete and recreate the Endee index
- Run `chunker.py` again any time you want to ingest a different repo
