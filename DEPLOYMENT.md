# 🌍 Deploying SecondBrain-RAG (Free Tier)

Since we are skipping Hugging Face, we've optimized your engine to use **Gemini Embeddings** instead of local models. This makes the application incredibly light and perfect for free hosting platforms like **Render**.

## 1. Embedding Engine Update
The project has been updated to use `models/text-embedding-004` (Gemini's latest embedding model).
- **Benefit**: No more 500MB+ model downloads.
- **Benefit**: Faster startup and lower RAM usage (perfect for free tiers).
- **Action**: You don't need to do anything; the `sb_engine.py` is already updated.

## 2. Deploying on Render (Free Tier)
Render is a great free alternative to Hugging Face Spaces for Flask apps.

### Steps:
1.  **Push to GitHub**: Ensure your latest changes are pushed to your repo.
2.  **Create Web Service**:
    - Go to [Render Dashboard](https://dashboard.render.com).
    - Click **New +** > **Web Service**.
    - Connect your GitHub repository.
3.  **Configure Environment**:
    - **Name**: `secondbrain-rag`
    - **Runtime**: `Docker` (Render will automatically detect your `Dockerfile`).
    - **Plan**: `Free`.
4.  **Environment Variables**:
    - Click **Advanced** > **Add Environment Variable**.
    - Key: `GEMINI_API_KEY`
    - Value: `YOUR_ACTUAL_API_KEY`
5.  **Build & Deploy**:
    - Render will build the Docker image.
    - Since your `Dockerfile` uses port `7860`, Render might ask for the port. You can add an environment variable `PORT` = `7860` if it doesn't auto-detect.

## 3. Alternative: Koyeb
If you prefer another platform, [Koyeb](https://www.koyeb.com/) also offers a "Nano" free instance that supports Docker.

---

### 🛠️ What's Changed in the Code?
- **`sb_engine.py`**: Now uses `genai.embed_content` for all vector operations.
- **`requirements.txt`**: Removed `sentence-transformers` (saving ~400MB of installation space).
- **Indentation & Logic**: Fixed search logic to use `numpy` for distance calculation since we removed `torch`.
