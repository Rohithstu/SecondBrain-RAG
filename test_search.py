from sb_engine import SecondBrainEngine
import os
from dotenv import load_dotenv

load_dotenv()

engine = SecondBrainEngine()
query = "Explain Apache Sqoop" # Example based on Unit 2.pdf content I saw in metadata
result = engine.search(query)
print(f"Query: {query}")
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
print(f"Confidence: {result['confidence']}")
