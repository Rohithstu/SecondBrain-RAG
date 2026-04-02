"""
SecondBrain Core Engine (Cycle 5)
Advanced RAG with Metadata Enrichment & LLM Generation.
- Automated Topic/Keyword/Risk Extraction (Cycle 5)
- LLM-Grounded Answer Generation
- FAISS Vector Management with Metadata Persistence
"""

import os
import re
import json
import hashlib
import numpy as np # type: ignore
import faiss # type: ignore
import time
import requests # type: ignore
# from sentence_transformers import SentenceTransformer # type: ignore (Skipping Hugging Face)
from threading import Thread
import google.generativeai as genai # type: ignore
from typing import List, Dict, Set, Any, cast, Tuple, Optional, Union, SupportsIndex

# Format Support Imports
import PyPDF2 # type: ignore
from docx import Document as DocxDocument # type: ignore
from pptx import Presentation # type: ignore
import pandas as pd # type: ignore
from PIL import Image # type: ignore
import pytesseract # type: ignore

# Monitoring
from watchdog.observers import Observer # type: ignore
from watchdog.events import FileSystemEventHandler # type: ignore


# ── LLM PROVIDERS ─────────────────────────────────────────────────────────────

class BaseLLMProvider:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model_name = "gemini-2.5-flash" 
        self.model = genai.GenerativeModel(self.model_name)
        print(f"[Gemini] Initialized with model: {self.model_name}")

    def generate(self, prompt: str) -> str:
        for attempt in range(3):
            try:
                response = self.model.generate_content(prompt)
                if hasattr(response, "text"):
                    return str(response.text)
                return "Error: No text in response"
            except Exception as e:
                # Handle 429 Quota Exceeded with backoff
                if "429" in str(e):
                    wait = (attempt + 1) * 3
                    print(f"[Gemini] Quota hit, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"[Gemini] Generation error: {e}")
                return f"Error generating answer: {str(e)}"
        return "Service temporarily unavailable due to quota limits. Please try again in a few minutes."

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        prompt = f"""
        Analyze the following text and extract metadata in JSON format ONLY:
        Text: {text}
        
        Required JSON Fields:
        - topics: list of 3-5 main topics
        - keywords: list of 5-8 key terms
        - summary: a 2-sentence concise summary
        - risks: any potential risks or conflicts mentioned (if none, return empty list)
        
        JSON:
        """
        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text
            # Simple JSON extraction
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"topics": ["General"], "keywords": [], "summary": "No summary generated.", "risks": []}
        except Exception as e:
            print(f"[Gemini] Metadata error: {e}")
            return {"topics": ["General"], "keywords": [], "summary": "N/A", "risks": []}


class MockLLMProvider(BaseLLMProvider):
    """Fallback for local testing without API keys."""
    def generate(self, prompt: str) -> str:
        return "This is a mock answer based on the provided context. (Add API key for real generation)"

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        return {
            "topics": ["Analysis Pending"],
            "keywords": ["Local", "Knowledge"],
            "summary": "This document has been indexed locally.",
            "risks": []
        }


# ── CORE ENGINE ─────────────────────────────────────────────────────────────

class SecondBrainEngine:
    def __init__(
        self,
        data_folder: str = "data",
        index_file: str = "index.faiss",
        metadata_file: str = "metadata.json",
        model_name: str = "all-MiniLM-L6-v2",
        relevance_threshold: float = 0.40
    ):
        self.data_folder: str = data_folder
        self.index_file: str = index_file
        self.metadata_file: str = metadata_file
        self.relevance_threshold: float = relevance_threshold
        
        print(f"[Engine] Using Gemini Embedding Model: text-embedding-004...")
        # We don't initialize a local model anymore; embeddings will be fetched via API.
        self.embed_model_name = "models/text-embedding-004"
        
        # LLM Initialization
        api_key = os.getenv("GEMINI_API_KEY")
        self.llm: BaseLLMProvider
        if api_key:
            print("[Engine] Using Gemini LLM Provider")
            self.llm = GeminiProvider(api_key)
        else:
            print("[Engine] Using Mock LLM Provider (No API Key found)")
            self.llm = MockLLMProvider()
        
        self.all_chunks: List[str] = []
        self.chunk_sources: List[str] = []
        self.file_metadata: Dict[str, Dict[str, Any]] = {}
        self.index: Optional[faiss.IndexFlatL2] = None
        
        self._load_from_disk()
        self.refresh_index()
        self._patch_missing_metadata()

    def _patch_missing_metadata(self) -> None:
        """Heuristic: if topics are missing, the file needs enrichment."""
        to_patch = [rel for rel, meta in self.file_metadata.items() if "topics" not in meta]
        if not to_patch: return
        
        print(f"[Engine] Patching metadata for {len(to_patch)} legacy files...")
        for rel in to_patch:
            full = os.path.join(self.data_folder, rel)
            ext = rel.lower().split(".")[-1] if "." in rel else ""
            content = ""
            try:
                if ext == "txt":
                    with open(full, "r", encoding="utf-8", errors="ignore") as f: content = f.read()
                else: content = self._load_formats(full, ext)
                
                if content.strip():
                    cleaned = self._advanced_clean(content)
                    doc_meta = self._extract_file_metadata(cleaned, rel)
                    # Merge with existing hash/mtime
                    self.file_metadata[rel].update(doc_meta)
            except Exception as e:
                print(f"  [Patch] Failed for {rel}: {e}")
        
        self._save_to_disk()

    # ── CYCLE 5: ADVANCED METADATA ENRICHMENT ──────────────────────────────
    def _extract_file_metadata(self, text: str, rel_path: str) -> Dict[str, Any]:
        """Extracts topics, keywords, and summary using the LLM."""
        print(f"  [Enrichment] Analyzing {rel_path}...")
        # Slice string safely for type checker
        snippet_chars = [c for i, c in enumerate(text) if i < 4000]
        snippet = "".join(snippet_chars)
        meta = cast(Dict[str, Any], self.llm.extract_metadata(snippet))
        meta["last_indexed"] = time.time()
        return meta

    # ── CYCLE 3/4 REFINEMENTS ─────────────────────────────────────────────
    def _advanced_clean(self, text: str) -> str:
        text = re.sub(r'(UNIT|Unit|Slide|SLIDE|PAGE|Page)\s+\d+', '', text)
        text = re.sub(r'Author:.*|Bharath\s+Yannam', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        return " ".join(text.split())

    def _chunk_text(self, text: str) -> List[str]:
        """Splits text into overlapping chunks for better retrieval."""
        raw_sentences: List[Any] = re.split(r'(?<=[.!?])\s+', text)
        sentences: List[str] = [str(s).strip() for s in raw_sentences if s and len(str(s).strip()) > 5]
        chunks: List[str] = []
        # Group sentences into chunks safely
        for i in range(0, len(sentences), 2):
            limit = i + 3
            # cast to appease the linter's slicing rules
            chunk_sents = [sentences[j] for j in range(i, min(limit, len(sentences)))]
            if not chunk_sents: continue
            chunk = " ".join(chunk_sents)
            chunks.append(str(chunk))
        return chunks

    # ── PERSISTENCE ──────────────────────────────────────────────────────────
    def _get_file_hash(self, filepath: str) -> str:
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f: hasher.update(f.read())
            return hasher.hexdigest()
        except: return ""

    def _load_from_disk(self) -> None:
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            try:
                self.index = faiss.read_index(self.index_file)
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.all_chunks = data.get("all_chunks", [])
                    self.chunk_sources = data.get("chunk_sources", [])
                    self.file_metadata = data.get("file_metadata", {})
            except Exception as e:
                print(f"[Engine] Load error: {e}")
                self.index = None

    def _save_to_disk(self) -> None:
        if self.index is not None:
            faiss.write_index(self.index, self.index_file)
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump({
                "all_chunks": self.all_chunks, 
                "chunk_sources": self.chunk_sources, 
                "file_metadata": self.file_metadata
            }, f, indent=2)

    def _load_formats(self, path: str, ext: str) -> str:
        try:
            if ext == "pdf":
                with open(path, "rb") as f:
                    return " ".join(p.extract_text() or "" for p in PyPDF2.PdfReader(f).pages)
            if ext == "docx":
                doc = DocxDocument(path)
                return "\n".join(p.text for p in doc.paragraphs)
            if ext == "pptx":
                t_builder = []
                prs = Presentation(path)
                for s in prs.slides:
                    for sh in s.shapes:
                        t = getattr(sh, "text", "")
                        if t: t_builder.append(str(t))
                return " ".join(t_builder)
            if ext == "xlsx":
                df_d = pd.read_excel(path, sheet_name=None)
                return " ".join(str(df.to_string()) for df in df_d.values())
            if ext in ["png", "jpg", "jpeg"]:
                print(f"  [OCR] Analyzing image: {path}...")
                img = Image.open(path)
                text = str(pytesseract.image_to_string(img, config='--psm 11')) # Use sparse text PSM for better detection 
                if text.strip():
                    print(f"  [OCR] Successfully extracted {len(text)} characters.")
                    return text
                else:
                    print(f"  [OCR] No text found in image.")
                    return ""
        except Exception as e:
            print(f"  [Format Error] Failed to load {ext}: {e}")
        return ""

    def refresh_index(self) -> None:
        print("[Engine] Refreshing Index (Cycle 5)...")
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        c_state = {}
        for r, ds, fs in os.walk(self.data_folder):
            for f in fs:
                p = os.path.join(r, f)
                c_state[os.path.relpath(p, self.data_folder)] = {"hash": self._get_file_hash(p)} # type: ignore

        # Handle removals and changes
        changed = set(rel for rel in self.file_metadata if rel not in c_state or self.file_metadata[rel].get("hash") != c_state[rel]["hash"]) # type: ignore
        if changed:
            print(f"  [Sync] Re-indexing {len(changed)} files...")
            pac: List[str] = [str(x) for x in self.all_chunks]
            pcs: List[str] = [str(x) for x in self.chunk_sources]
            self.all_chunks, self.chunk_sources = [], []
            for c, s in zip(pac, pcs):
                if str(s) not in changed:
                    self.all_chunks.append(str(c))
                    self.chunk_sources.append(str(s))
            for s in changed: self.file_metadata.pop(str(s), None)
            
            if self.all_chunks:
                raw_embs = self._get_gemini_embeddings(self.all_chunks)
                embs = np.array(raw_embs, dtype=np.float32)
                self.index = cast(faiss.IndexFlatL2, faiss.IndexFlatL2(embs.shape[1]))
                if self.index is not None and hasattr(self.index, "add"):
                    getattr(self.index, "add")(embs)
            else:
                self.index = None

        # Add new/modified files
        modified = False
        for rel in c_state:
            if rel not in self.file_metadata:
                full = os.path.join(self.data_folder, rel)
                ext = rel.lower().split(".")[-1] if "." in rel else ""
                content = ""
                if ext == "txt":
                    with open(full, "r", encoding="utf-8", errors="ignore") as f: content = f.read()
                else: content = self._load_formats(full, ext)
                
                cleaned = self._advanced_clean(content)
                
                # ALWAYS add to file_metadata so it shows in tracking even if empty
                doc_meta: Dict[str, Any] = {}
                if cleaned.strip():
                    doc_meta = self._extract_file_metadata(cleaned, rel)
                else:
                    print(f"  [Notice] {rel} has no readable text content.")
                    doc_meta = {
                        "topics": ["Unreadable Content"], 
                        "keywords": [], 
                        "summary": "This file was indexed but no text content could be extracted.",
                        "risks": []
                    }
                
                doc_meta["hash"] = c_state[rel]["hash"]
                self.file_metadata[rel] = doc_meta
                modified = True # Ensure we save even if just updating metadata
                
                if cleaned.strip():
                    new_chunks = self._chunk_text(cleaned)
                    if new_chunks:
                        print(f"  [Load] {rel} ({len(new_chunks)} chunks indexed)")
                        raw_embs = self._get_gemini_embeddings(new_chunks)
                        embs = np.array(raw_embs, dtype=np.float32)
                        if self.index is None: 
                            self.index = cast(faiss.IndexFlatL2, faiss.IndexFlatL2(embs.shape[1]))
                        if self.index is not None and hasattr(self.index, "add"):
                            getattr(self.index, "add")(embs)
                        self.all_chunks.extend(new_chunks)
                        self.chunk_sources.extend([str(rel)] * len(new_chunks))
                    else:
                        print(f"  [Load] {rel} (0 chunks - text too short)")
        
        if modified or changed:
            self._save_to_disk()

    # ── SEARCH & GENERATION ───────────────────────────────────────────────
    def search(self, query: str, top_k: int = 4, offline: bool = False) -> Dict[str, Any]:
        """Performs semantic search and uses LLM to generate a grounded answer."""
        # Use substantial context for offline mode to find the best cluster
        if offline: top_k = 10
        if self.index is None or not self.all_chunks:
            return {"answer": "I don't have any knowledge yet. Please add documents to the data folder.", "confidence": 0}

        q_emb_list = self._get_gemini_embeddings([query])
        q_emb = np.array(q_emb_list, dtype=np.float32)
        if self.index is not None and hasattr(self.index, "search"):
            distances, indices = getattr(self.index, "search")(q_emb, top_k)
        else:
            return {"answer": "Index unavailable.", "confidence": 0}
        
        context_chunks = []
        sources = set()
        
        # Casting distances and indices for type checker
        dist_row = cast(List[float], distances[0])
        idx_row = cast(List[int], indices[0])
        
        for d, i in zip(dist_row, idx_row):
            idx = int(i)
            if idx == -1: continue
            score = 1.0 / (1.0 + float(d))
            if score < self.relevance_threshold: continue
            
            # cast for linter
            chunk_text = str(cast(List[str], self.all_chunks)[idx]) # type: ignore
            source = str(cast(List[str], self.chunk_sources)[idx]) # type: ignore
            context_chunks.append(f"[Source: {source}] {chunk_text}")
            sources.add(source)

        if not context_chunks:
            return {"answer": "I found some content, but it doesn't seem relevant enough to provide a confident answer.", "confidence": 0}

        # ── OFFLINE MODE: LOCAL EXTRACTIVE SUMMARIZATION ───────────────────
        if offline:
            return self._offline_synthesize(query, context_chunks, list(sources))

        # ── LLM GENERATION ────────────────────────────────────────────────
        context_block = "\n---\n".join(context_chunks)
        prompt = f"""
        Answer the following question based ONLY on the strictly provided context chunks. 
        If the answer is not explicitly stated in the context, say "I don't find this information in my documents."
        
        Context:
        {context_block}
        
        Question: {query}
        
        CRITICAL INSTRUCTIONS:
        - DO NOT hallucinate, guess, or add ANY outside information.
        - Be extremely concise and stick ONLY to the exact facts presented in the context.
        - If the context provides bullet points, output them as bullet points.
        - Do not weave a long descriptive story. Keep it factual and brief.
        - Cite your sources inline exactly as they appear (e.g. [filename.pdf]).
        
        Answer:
        """
        
        answer = self.llm.generate(prompt)
        
        # Extract metadata for the UI (topics related to results)
        featured_topics = []
        for s in sources:
            if s in self.file_metadata:
                featured_topics.extend(self.file_metadata[s].get("topics", []))
        
        out_topics = [t for idx, t in enumerate(set(featured_topics)) if idx < 5]

        return {
            "answer": str(answer),
            "sources": list(sources),
            "topics": out_topics,
            "confidence": 0.9, # Simplified for UI
            "status": "LLM Generated"
        }


    def _get_gemini_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Fetch embeddings from Gemini API."""
        try:
            # Gemini allows batch embedding
            result = genai.embed_content(
                model=self.embed_model_name,
                content=texts,
                task_type="retrieval_document" if len(texts) > 1 else "retrieval_query"
            )
            # result['embedding'] is a list of lists if multiple, or a single list if one
            embeddings = result.get('embedding', [])
            if len(texts) == 1 and embeddings and not isinstance(embeddings[0], list):
                return [embeddings]
            return embeddings
        except Exception as e:
            print(f"[Gemini] Embedding error: {e}")
            # Return zero vectors as fallback (should match dimension 768 for text-embedding-004)
            return [[0.0] * 768 for _ in texts]

    def _offline_synthesize(self, query: str, context_chunks: List[str], sources: List[str]) -> Dict[str, Any]:
        """Cluster Retrieval for Full-Paragraph Offline Context."""
        try:
            q_emb = np.array(self._get_gemini_embeddings([query]), dtype=np.float32)[0]
            chunk_texts_only = [re.sub(r'\[Source: .*?\]', '', c).strip() for c in context_chunks]
            chunk_embs = np.array(self._get_gemini_embeddings(chunk_texts_only), dtype=np.float32)
            
            # Use dot product for cosine similarity with Gemini normalized embeddings
            dots = np.dot(chunk_embs, q_emb)
            norms = np.linalg.norm(chunk_embs, axis=1) * np.linalg.norm(q_emb)
            # Handle zero norms
            norms[norms == 0] = 1e-9
            chunk_scores = dots / norms
            top_chunk_idx = int(np.argmax(chunk_scores))
            
            if chunk_scores[top_chunk_idx] < 0.35:
                return {"answer": "Offline: No documents seem highly relevant to this specific query.", "sources": sources, "confidence": 0}

            # 2. Get the best chunk and its source
            best_chunk_raw = context_chunks[top_chunk_idx]
            source_match = re.search(r'\[Source: (.*?)\]', best_chunk_raw)
            best_src = source_match.group(1) if source_match else "Dataset"
            best_chunk_clean = re.sub(r'\[Source: .*?\]', '', best_chunk_raw).strip()

            # 3. Assemble the "Answer Cluster"
            # Since the chunk itself is a contextual unit, we return it as a "Smart Section"
            # But we also look for the #2 highest chunk if it's from a different file or section
            second_chunk_idx = -1
            if len(chunk_scores) > 1:
                # Find the next best chunk with a different enough score or source
                scores_sorted, indices_sorted = torch.sort(chunk_scores, descending=True)
                for i in range(1, len(indices_sorted)):
                    idx = int(indices_sorted[i].item())
                    if scores_sorted[i] > 0.35: 
                        second_chunk_idx = idx
                        break

            ans = f"### Content Cluster from **{best_src}**\n"
            ans += f"I found a highly relevant section in your documents:\n\n"
            ans += f"> {best_chunk_clean}\n\n"
            
            if second_chunk_idx != -1:
                sec_raw = context_chunks[second_chunk_idx]
                sec_src = re.search(r'\[Source: (.*?)\]', sec_raw)
                sec_src = sec_src.group(1) if sec_src else "Dataset"
                sec_clean = re.sub(r'\[Source: .*?\]', '', sec_raw).strip()
                ans += f"**Additional Relevant Context ({sec_src}):**\n"
                # Shorten the context snippet for the second hit
                ans += f"• {sec_clean[:300]}...\n"
            
            return {
                "answer": ans,
                "sources": list(set([best_src])),
                "confidence": chunk_scores[top_chunk_idx].item(),
                "status": "Offline Cluster"
            }
        except Exception as e:
            return {"answer": f"Offline Cluster Error: {str(e)}", "sources": sources, "confidence": 0}


# ── MONITORING ─────────────────────────────────────────────────────────────
class DataMonitorHandler(FileSystemEventHandler):
    def __init__(self, engine: SecondBrainEngine): self.engine = engine
    def on_any_event(self, event):
        if not event.is_directory and not event.src_path.endswith((".json", ".faiss")):
            time.sleep(1); self.engine.refresh_index()

def start_monitoring(engine: SecondBrainEngine):
    handler = DataMonitorHandler(engine)
    ob = Observer()
    ob.schedule(handler, engine.data_folder, recursive=True)
    ob.start(); return ob
