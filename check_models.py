import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer
    import google.generativeai as genai
    print("Dependencies loaded successfully.")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

model_name = "all-MiniLM-L6-v2"
try:
    print(f"Loading embedding model {model_name}...")
    model = SentenceTransformer(model_name)
    print("Model loaded.")
except Exception as e:
    print(f"Model load error: {e}")
    sys.exit(1)

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    try:
        genai.configure(api_key=api_key)
        # Try a simple generation
        m = genai.GenerativeModel("gemini-1.5-flash")
        response = m.generate_content("Hello")
        print(f"Gemini response: {response.text}")
    except Exception as e:
        print(f"Gemini error: {e}")
else:
    print("No GEMINI_API_KEY found in .env")
