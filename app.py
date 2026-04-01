"""
SecondBrain Web Server (Cycle 4)
Updated to serve assembled answers.
"""

from flask import Flask, render_template, request, jsonify # type: ignore
from werkzeug.utils import secure_filename # type: ignore
from sb_engine import SecondBrainEngine, start_monitoring # type: ignore
import os
from dotenv import load_dotenv # type: ignore

load_dotenv() # Load GEMINI_API_KEY from .env

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

engine = SecondBrainEngine()
monitor = start_monitoring(engine)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/search", methods=["POST"])
def search():
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "No query provided"}), 400
    
    query = data["query"]
    is_offline = data.get("offline", False)
    result = engine.search(query, offline=is_offline)
    
    return jsonify({
        "query": query,
        "answer_data": result
    })

@app.route("/api/knowledge", methods=["GET"])
def knowledge():
    # Return extracted topics and summaries for the Knowledge Hub
    hub_data = []
    for rel_path, meta in engine.file_metadata.items():
        hub_data.append({
            "file": rel_path,
            "topics": meta.get("topics", []),
            "summary": meta.get("summary", "No summary available.")
        })
    return jsonify(hub_data)

@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "total_chunks": len(engine.all_chunks),
        "files": list(engine.file_metadata.keys())
    })

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # The watchdog monitor in engine.py will automatically pick this up and re-index!
        return jsonify({"message": f"Successfully uploaded {filename}", "filename": filename}), 200

if __name__ == "__main__":
    try:
        # Hugging Face usually provides the PORT variable or expects 7860
        port = int(os.environ.get("PORT", 7860))
        app.run(host="0.0.0.0", port=port, debug=False)
    finally:
        monitor.stop()
        monitor.join()
