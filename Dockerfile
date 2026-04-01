# Use a stable Python 3.10 image
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user (Hugging Face requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set the working directory
WORKDIR /app

# Install system dependencies (Hugging Face is Debian-based)
# Must use root briefly to install system packages
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch back to the non-root user
USER user

# Copy only requirements first to leverage Docker cache
COPY --chown=user requirements.txt .

# Install Python dependencies (CPU-only versions to save RAM)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy the rest of the application code
COPY --chown=user . .

# Expose the Flask port (Hugging Face expects 7860)
EXPOSE 7860

# Start the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "200", "app:app"]
