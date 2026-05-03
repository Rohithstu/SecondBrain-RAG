from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from sb_engine import SecondBrainManager, start_monitoring
from models import db, User, Document
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "super-secret-key-123")

# Use PostgreSQL if available (Render), otherwise SQLite (Local)
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///secondbrain_users.db'

app.config['UPLOAD_FOLDER'] = 'data'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extensions
db.init_app(app)
with app.app_context():
    db.create_all()
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@app.errorhandler(Exception)
def handle_exception(e):
    # If the error is on an API route, return JSON
    if request.path.startswith('/api/'):
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500
    # Otherwise return the default (which might be a template or error page)
    return e

# Engine Manager (Shared)
manager = SecondBrainManager(base_data_folder=app.config['UPLOAD_FOLDER'])
monitor = start_monitoring(manager)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── AUTH ROUTES ────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            flash("Account created! You can now login.", "success")
            return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ── APP ROUTES ─────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/profile")
@login_required
def profile():
    # Fetch all documents owned by the current user
    docs = Document.query.filter_by(user_id=current_user.id).all()
    return render_template("profile.html", documents=docs)

@app.route("/api/search", methods=["POST"])
@login_required
def search():
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "No query provided"}), 400
    
    engine = manager.get_engine(current_user.id)
    result = engine.search(data["query"], offline=data.get("offline", False))
    
    return jsonify({
        "query": data["query"],
        "answer_data": result
    })

@app.route("/api/knowledge", methods=["GET"])
@login_required
def knowledge():
    engine = manager.get_engine(current_user.id)
    hub_data = []
    for rel_path, meta in engine.file_metadata.items():
        hub_data.append({
            "file": rel_path,
            "topics": meta.get("topics", []),
            "summary": meta.get("summary", "No summary available.")
        })
    return jsonify(hub_data)

@app.route("/api/status", methods=["GET"])
@login_required
def status():
    engine = manager.get_engine(current_user.id)
    return jsonify({
        "total_chunks": len(engine.all_chunks),
        "files": list(engine.file_metadata.keys()),
        "user": current_user.username
    })

@app.route("/api/upload", methods=["POST"])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        engine = manager.get_engine(current_user.id)
        filename = secure_filename(file.filename)
        filepath = os.path.join(engine.docs_folder, filename)
        file.save(filepath)
        
        # Trigger immediate ingestion (don't wait for watcher)
        try:
            engine.ingest_new_files()
        except Exception as e:
            print(f"Ingestion error: {e}")
        
        # Track in DB
        new_doc = Document(filename=filename, user_id=current_user.id)
        db.session.add(new_doc)
        db.session.commit()
        
        return jsonify({"message": f"Successfully uploaded {filename}", "filename": filename}), 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    try:
        app.run(debug=True, port=5001)
    finally:
        monitor.stop()
        monitor.join()
