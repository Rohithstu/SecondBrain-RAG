# 🧠 SecondBrain-RAG — Semantic Knowledge Engine

> **A production-grade Retrieval-Augmented Generation (RAG) system** that lets you chat with your own documents using state-of-the-art semantic search and LLM-powered answer generation.

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Web%20Server-000000?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-00ADEF?style=flat-square)](https://github.com/facebookresearch/faiss)
[![Gemini](https://img.shields.io/badge/Google-Gemini%202.5%20Flash-4285F4?style=flat-square&logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📌 Overview

**SecondBrain** is a local-first, AI-powered knowledge management system. Drop your documents into a folder — PDFs, Word files, PowerPoints, spreadsheets, images, or plain text — and instantly query them in natural language. The system uses semantic embeddings and a FAISS vector index for lightning-fast retrieval, then grounds its answers using the Google Gemini LLM to eliminate hallucinations.

It supports both **online mode** (LLM-generated, grounded answers) and **offline mode** (local extractive summarization without any API calls).

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Semantic Search** | Sentence-transformer embeddings (`all-MiniLM-L6-v2`) for meaning-aware retrieval |
| 🤖 **LLM Answer Generation** | Grounded responses via Google Gemini 2.5 Flash — no hallucinations |
| 📄 **Multi-Format Ingestion** | PDF, DOCX, PPTX, XLSX, TXT, PNG/JPG (via OCR) |
| 🧩 **Smart Chunking** | Overlapping sentence-group chunking for high-recall context windows |
| 🏷️ **Auto Metadata Enrichment** | LLM-extracted topics, keywords, summaries, and risk flags per document |
| 💾 **Persistent Vector Index** | FAISS index + JSON metadata persist across restarts |
| 👁️ **Live File Monitoring** | Watchdog auto-reindexes documents the moment files are added or changed |
| 🌐 **Web Dashboard** | Glassmorphic Flask UI with Knowledge Hub and real-time search |
| 🖥️ **Terminal Mode** | Lightweight CLI interface for headless / server environments |
| 📴 **Offline Mode** | Cluster-based extractive retrieval — works with zero internet access |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SecondBrain System                      │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  /data   │───▶│  sb_engine   │───▶│   FAISS Index    │  │
│  │ (Docs)   │    │  (Core RAG)  │    │  (index.faiss)   │  │
│  └──────────┘    └──────┬───────┘    └──────────────────┘  │
│                         │                                   │
│              ┌──────────▼──────────┐                        │
│              │   LLM Provider      │                        │
│              │  (Gemini / Mock)    │                        │
│              └──────────┬──────────┘                        │
│                         │                                   │
│         ┌───────────────┼───────────────┐                   │
│         ▼               ▼               ▼                   │
│    app.py (Web)   main.py (CLI)   Watchdog Monitor          │
└─────────────────────────────────────────────────────────────┘
```

**Query Flow:**
1. User submits a natural-language question
2. Query is encoded into a semantic embedding
3. FAISS performs nearest-neighbor search against all document chunks
4. Top-k relevant chunks are assembled into a context block
5. Gemini LLM generates a grounded, source-cited answer
6. Response returned with confidence score, sources, and topics

---

## 📁 Project Structure

```
MINIPROJECT/
├── sb_engine.py          # 🧠 Core RAG engine — embeddings, FAISS, LLM, ingestion
├── app.py                # 🌐 Flask web server with REST API
├── main.py               # 🖥️  Terminal / CLI interface
├── requirements.txt      # 📦 Python dependencies
├── .env                  # 🔑 API keys (not committed)
├── .gitignore            # 🚫 Git exclusions
│
├── data/                 # 📂 Drop your documents here
│   ├── *.pdf
│   ├── *.docx / *.pptx / *.xlsx
│   ├── *.txt
│   └── *.png / *.jpg     # OCR supported
│
├── templates/
│   └── index.html        # 💎 Glassmorphic web dashboard
│
├── static/               # 🎨 CSS / JS assets
│
├── index.faiss           # 🗃️ Persisted vector index (auto-generated)
├── metadata.json         # 📋 Document metadata store (auto-generated)
└── secondbrain_history.db # 📜 Query history database (auto-generated)
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python **3.9+**
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (required for image ingestion)
- A **Google Gemini API key** (free tier available at [ai.google.dev](https://ai.google.dev))

### 2. Clone the Repository

```bash
git clone https://github.com/Rohithstu/SecondBrain-RAG.git
cd SecondBrain-RAG
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

> ⚠️ **Never commit your `.env` file.** It is already excluded via `.gitignore`.

### 5. Add Your Documents

Copy any PDF, DOCX, PPTX, XLSX, TXT, or image files into the `data/` folder:

```bash
# Example
cp my_report.pdf data/
cp lecture_notes.docx data/
```

### 6. Run

**Web Dashboard (recommended):**
```bash
python app.py
# Open http://localhost:5001 in your browser
```

**Terminal / CLI mode:**
```bash
python main.py
```

---

## 🌐 API Reference

The Flask server exposes the following REST endpoints:

### `POST /api/search`
Query the knowledge base with a natural language question.

**Request Body:**
```json
{
  "query": "What is the OSI model?",
  "offline": false
}
```

**Response:**
```json
{
  "query": "What is the OSI model?",
  "answer_data": {
    "answer": "The OSI model is a conceptual framework... [source.pdf]",
    "sources": ["network_notes.pdf"],
    "topics": ["Networking", "Protocols"],
    "confidence": 0.9,
    "status": "LLM Generated"
  }
}
```

---

### `GET /api/knowledge`
Retrieve the Knowledge Hub — all indexed files with extracted topics and summaries.

**Response:**
```json
[
  {
    "file": "lecture_notes.pdf",
    "topics": ["Machine Learning", "Neural Networks"],
    "summary": "A comprehensive overview of supervised learning techniques..."
  }
]
```

---

### `GET /api/status`
Check the engine status — total indexed chunks and file list.

**Response:**
```json
{
  "total_chunks": 842,
  "files": ["notes.pdf", "cloud_computing.txt", "ai_intro.docx"]
}
```

---

### `POST /api/upload`
Upload a new document directly via the web dashboard.

**Form Data:** `file` (multipart)

**Response:**
```json
{
  "message": "Successfully uploaded report.pdf",
  "filename": "report.pdf"
}
```

---

## ☁️ Deployment

Deploying the **SecondBrain Engine** requires a platform that supports Docker and persistent storage (for your indexed documents).

### 🚀 Recommended: Docker + Render/Railway
The easiest way is to use the provided `Dockerfile`.

1.  **Build the Image:**
    ```bash
    docker build -t secondbrain .
    ```
2.  **Run Locally with Docker:**
    ```bash
    docker run -p 5001:5001 -v $(pwd)/data:/app/data --env-file .env secondbrain
    ```

3.  **Deploy to Cloud:**
    -   Connect your GitHub repository to [Render.com](https://render.com) or [Railway.app](https://railway.app).
    -   Select **Web Service** and choose **Docker** as the runtime.
    -   Add your `GEMINI_API_KEY` as an environment variable in the dashboard.
    -   **Important:** Attach a **Persistent Disk** to the `/app/data` path to keep your vector index and uploaded documents across restarts.

---

## ⚙️ Configuration

Key parameters in `sb_engine.py` (constructor of `SecondBrainEngine`):

| Parameter | Default | Description |
|---|---|---|
| `data_folder` | `"data"` | Directory to watch for documents |
| `index_file` | `"index.faiss"` | FAISS index persistence path |
| `metadata_file` | `"metadata.json"` | Metadata store persistence path |
| `model_name` | `"all-MiniLM-L6-v2"` | Sentence transformer model for embeddings |
| `relevance_threshold` | `0.40` | Minimum similarity score to include a chunk |

---

## 🛠️ Supported File Formats

| Format | Extension | Method |
|---|---|---|
| PDF | `.pdf` | PyPDF2 text extraction |
| Word Document | `.docx` | python-docx paragraph parsing |
| PowerPoint | `.pptx` | python-pptx shape text extraction |
| Excel | `.xlsx` | pandas multi-sheet parsing |
| Plain Text | `.txt` | Direct UTF-8 read |
| Images | `.png`, `.jpg`, `.jpeg` | Tesseract OCR (`--psm 11`) |

---

## 🔬 How It Works — RAG Pipeline

```
Document Ingestion
      │
      ▼
 Text Extraction  ──► Format-specific parsers (PDF/DOCX/PPTX/XLSX/OCR)
      │
      ▼
 Text Cleaning    ──► Remove headers, page numbers, author artifacts
      │
      ▼
 Smart Chunking   ──► Overlapping sentence groups (3 sentences, stride 2)
      │
      ▼
 Embedding        ──► SentenceTransformer → 384-dim float32 vectors
      │
      ▼
 FAISS Indexing   ──► IndexFlatL2, persisted to disk
      │
      ▼
 Metadata Enrich  ──► Gemini extracts: topics, keywords, summary, risks
      │
      ▼
       ┌──────── Query Time ────────┐
       │  Query → Embed → FAISS     │
       │  → Top-K Chunks → LLM     │
       │  → Grounded Answer        │
       └───────────────────────────┘
```

**Offline Mode** skips the LLM call and instead uses cosine similarity (via `sentence-transformers`) to cluster and return the most relevant text section directly from the indexed chunks.

---

## 🔐 Security Notes

- Your `.env` file (containing the Gemini API key) is excluded from version control via `.gitignore`.
- The system runs **entirely locally** — documents never leave your machine unless the Gemini API is called for answer generation.
- Offline mode (`"offline": true`) ensures **zero data is sent externally**.

---

## 📦 Dependencies

```
sentence-transformers    # Semantic embedding model
faiss-cpu                # Vector similarity search
numpy                    # Numerical operations
flask                    # Web framework
PyPDF2                   # PDF text extraction
pytesseract              # OCR for images
Pillow                   # Image processing
python-docx              # Word document parsing
python-pptx              # PowerPoint parsing
pandas / openpyxl        # Excel parsing
watchdog                 # Live file system monitoring
google-generativeai      # Gemini LLM provider
requests                 # HTTP client
python-dotenv            # Environment variable loading
```

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**K. Rohith Reddy**  
[GitHub](https://github.com/Rohithstu) · [LinkedIn](https://linkedin.com/in/rohithreddy)

---

<div align="center">
  <sub>Built with ❤️ using Python, FAISS, Sentence Transformers, and Google Gemini</sub>
</div>
