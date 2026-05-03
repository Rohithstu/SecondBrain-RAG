import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import numpy as np
    import faiss
    import google.generativeai as genai
    print("Dependencies loaded successfully.")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found in .env")
    sys.exit(1)

genai.configure(api_key=api_key)

# Check Gemini Embeddings
embedding_model = "models/text-embedding-004"
try:
    print(f"Checking embedding model {embedding_model}...")
    result = genai.embed_content(
        model=embedding_model,
        content="Test embedding query",
        task_type="retrieval_query"
    )
    print(f"Embedding check successful. Vector size: {len(result['embedding'])}")
except Exception as e:
    print(f"Embedding error: {e}")
    sys.exit(1)

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
