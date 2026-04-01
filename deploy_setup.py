import os
import sys

# Ensure common directories exist for persistence
os.makedirs("data", exist_ok=True)

# Add Gunicorn as a deployment-ready server
with open("requirements.txt", "a") as f:
    f.write("\ngunicorn")

print("\n🚀 Ready for deployment!")
print("1. Build your container: docker build -t secondbrain .")
print("2. Run with persistence: docker run -p 5001:5001 -v $(pwd)/data:/app/data --env-file .env secondbrain")
