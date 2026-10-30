# 🚀 InsightEngine — AI-Powered Knowledge Retrieval System

InsightEngine AI is a full-stack AI platform that enables users to intelligently query their own data using a hybrid retrieval architecture combining **Retrieval-Augmented Generation (RAG)** and **Knowledge Graphs (KG)**.

The system supports semantic understanding, structured reasoning, and conversational querying across uploaded data sources.

---

# 🖼️ Application UI

> 📌 A glimpse of the Insight Engine frontend interface — with many more features and enhancements coming soon.

![InsightEngine AI UI](./screenshots/rag-ui-chat-image.png)

---

## ✨ Features

- 📂 Upload and process PDF and UTF-8 text files
- 🔍 Semantic retrieval using vector embeddings (FAISS)
- 🧠 Knowledge Graph extraction using triplets
- ⚡ Hybrid Retrieval (Vector Search + KG Search)
- 💬 Conversational AI chat interface
- ⌨️ Enter-to-send messaging
- 📌 Cost-optimized KG retrieval (No KG embeddings)
- 🔄 Incremental knowledge updates
- 🌐 FastAPI backend with Angular frontend

---

# 🏗️ System Architecture

```text
                ┌────────────────────┐
                │   User Uploads     │
                │ PDFs / TXT files  │
                └─────────┬──────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Data Processing │
                 │ Chunking Layer  │
                 └────────┬────────┘
                          │
          ┌───────────────┴────────────────┐
          │                                │
          ▼                                ▼
 ┌─────────────────┐              ┌──────────────────┐
 │ Vector Embedding │              │ Knowledge Graph │
 │ text-embedding   │              │ Triplet Extract │
 └────────┬────────┘              └────────┬─────────┘
          │                                │
          ▼                                ▼
     ┌─────────┐                     ┌──────────┐
     │  FAISS  │                     │ KG Store │
     └────┬────┘                     └────┬─────┘
          │                                │
          └──────────────┬─────────────────┘
                         ▼
                ┌────────────────┐
                │ Hybrid Retrieval│
                └────────┬───────┘
                         ▼
                ┌────────────────┐
                │ GPT-4.1-mini   │
                └────────┬───────┘
                         ▼
                 ┌──────────────┐
                 │ Final Answer │
                 └──────────────┘
```

---

# 🧩 Tech Stack

## Backend

- FastAPI
- Python
- FAISS (Vector Database)
- OpenAI API

## Frontend

- Angular
- TypeScript
- CSS

---

# 📂 Project Structure

```text
backend/
├── app.py
├── rag_faiss.py
├── kg_layer.py
├── hybrid_rag.py
├── config.py
└── data/                 # Local uploads, FAISS index, chunks, and KG dump (gitignored)

frontend/
└── src/app/              # Angular UI
```

---

# ⚙️ Core Components

## 🔹 RAG Layer

The semantic retrieval layer:

- Chunks uploaded data
- Generates embeddings using:
  ```
  text-embedding-3-small
  ```
- Stores vectors in FAISS
- Retrieves top-k semantically relevant chunks

---

## 🔹 Knowledge Graph Layer

The Knowledge Graph layer extracts structured relationships in the form:

```text
(subject, relation, object)
```

### Example

```text
(Rohit, works_at, LTIMindtree)
```

### Retrieval Strategy

- Token matching
- Scoring-based ranking
- Symbolic relationship lookup

### Cost Optimization

Unlike many GraphRAG systems:

- ❌ No embeddings are generated for KG triplets
- ✅ Reduces embedding cost significantly
- ✅ Improves scalability

---

## 🔹 Hybrid Retrieval Pipeline

```python
rag_docs = retrieve(query, index, chunks)
kg_facts = query_kg(query)

prompt = f"""
Structured Knowledge:
{kg_facts}

Context:
{rag_docs}

Question:
{query}
"""
```

This combines:

- semantic similarity search
- structured knowledge retrieval
- contextual LLM reasoning

---

# 🌐 API Endpoints

| Endpoint      | Description               |
| ------------- | ------------------------- |
| `/upload`     | Upload a PDF or UTF-8 TXT |
| `/ask`        | RAG-only retrieval        |
| `/hybrid-ask` | Hybrid RAG + KG retrieval |
| `/kg-query`   | Knowledge Graph querying  |

---

# 🎨 Frontend Features

The Angular frontend provides:

- 💬 Conversational AI interface
- 📄 Upload panel for user data
- ↔️ User/Bot message alignment
- ⌨️ Enter key message submission
- 🔄 Auto-scrolling chat window
- 🌐 Real-time FastAPI integration

---

# 🧪 Running the Project

## Backend Setup

```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env and set OPENAI_API_KEY
cd backend
uvicorn app:app --reload
```

The backend reads its OpenAI model names and generation token limit from
`backend/.env`. Available settings are `OPENAI_CHAT_MODEL`,
`OPENAI_EMBEDDING_MODEL`, `OPENAI_MAX_OUTPUT_TOKENS`, `MAX_UPLOAD_BYTES`, and
`MAX_PDF_PAGES`. Defaults are provided in `backend/.env.example`;
`OPENAI_API_KEY` is also read by the OpenAI SDK. Uploads are limited to 20 MiB;
PDFs are additionally limited to 500 pages. TXT uploads must be UTF-8 encoded.

---

## Frontend Setup

```bash
cd frontend
npm install
ng serve
```

Open:

```text
http://localhost:4200
```

---

# ⚠️ FastAPI CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

# 💡 Key Engineering Decisions

- ✅ Hybrid retrieval improves response quality
- ✅ Knowledge Graph adds structured reasoning
- ✅ No KG embeddings reduces operational cost
- ✅ Incremental graph updates from newly uploaded data
- ✅ Modular retrieval architecture
- ✅ Scalable for future multimodal support

---

# 🚀 Future Enhancements

- 🔥 Streaming AI responses
- 🔥 Source citations in responses
- 🔥 Multi-user support
- 🔥 Authentication & authorization
- 🔥 Replace pickle with PostgreSQL / DynamoDB
- 🔥 Support for image/audio/video querying
- 🔥 Graph visualization dashboard

---

# 🌍 Real-World Use Cases

- Enterprise knowledge assistants
- AI document copilots
- Research assistants
- Internal company search systems
- Customer support AI
- Multimodal AI retrieval systems

---

# 👨‍💻 Author

## Rohit Shakya

- Full Stack Developer
- Backend-focused Engineer
- Java • Spring Boot • Python • Angular
- Working at LTIMindtree

---

# ⭐ Support

If you like this project:

- Give it a star ⭐
- Fork the repository
- Feel free to contribute
