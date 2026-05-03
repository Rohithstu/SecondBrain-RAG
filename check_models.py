import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import numpy as np
    import faiss
    import google.generativeai as genai
    from fastembed import TextEmbedding
    print("Dependencies loaded successfully.")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Check Local Embeddings (FastEmbed)
try:
    print("Checking local embedding model (FastEmbed)...")
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    result = list(model.embed(["Test query"]))
    print(f"Local embedding successful. Vector size: {len(result[0])}")
except Exception as e:
    print(f"Local embedding error: {e}")
    sys.exit(1)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found in .env (Skipping generation check)")
else:
    genai.configure(api_key=api_key)
    # Check Gemini Generation
    gen_model_name = "gemini-1.5-flash"
    try:
        print(f"Checking generation model {gen_model_name}...")
        m = genai.GenerativeModel(gen_model_name)
        response = m.generate_content("Hello")
        print(f"Gemini response: {response.text}")
    except Exception as e:
        print(f"Gemini error: {e}")
        sys.exit(1)
