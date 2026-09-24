
import os, uuid, secrets, sqlite3, time, io
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from services.converter import inspect_pdf, convert_pdf_to_docx, ocr_pdf_to_docx

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "app.db"
UPLOADS, OUTPUTS = BASE/"uploads", BASE/"outputs"
UPLOADS.mkdir(exist_ok=True); OUTPUTS.mkdir(exist_ok=True)

app = Flask(__name__)
_secret_file = DATA / "secret.key"
if os.environ.get("SECRET_KEY"):
    _secret_key = os.environ["SECRET_KEY"]
elif _secret_file.exists():
    _secret_key = _secret_file.read_text(encoding="utf-8").strip()
else:
    _secret_key = secrets.token_hex(32)
    _secret_file.write_text(_secret_key, encoding="utf-8")
app.secret_key = _secret_key
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
FREE_CREDITS = int(os.environ.get("FREE_CREDITS", "3"))

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, credits INTEGER NOT NULL DEFAULT 3,
        created_at INTEGER NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY, user_id INTEGER, filename TEXT, pages INTEGER,
        mode TEXT, status TEXT, created_at INTEGER NOT NULL)""")
    c.commit(); c.close()

init_db()

def current_user():
    uid = session.get("user_id")
    if not uid: return None
    c=db(); u=c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone(); c.close()
    return u

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user(): return jsonify(error="Login required."), 401
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def index():
    return render_template("index.html", user=current_user())

@app.get("/pricing")
def pricing(): return render_template("pricing.html", user=current_user())

@app.get("/dashboard")
def dashboard():
    u=current_user()
    if not u: return redirect(url_for("login"))
    c=db(); jobs=c.execute("SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC", (u["id"],)).fetchall(); c.close()
    return render_template("dashboard.html", user=u, jobs=jobs)

@app.get("/register")
def register(): return render_template("auth.html", mode="register")

@app.get("/login")
def login(): return render_template("auth.html", mode="login")

@app.post("/api/register")
def api_register():
    data=request.form
    email=data.get("email","").strip().lower(); pw=data.get("password","")
    if len(email)<5 or "@" not in email or len(pw)<8:
        return jsonify(error="Use a valid email and a password of at least 8 characters."),400
    c=db()
    try:
        cur=c.execute("INSERT INTO users(email,password_hash,credits,created_at) VALUES(?,?,?,?)",
                      (email,generate_password_hash(pw),FREE_CREDITS,int(time.time())))
        c.commit(); uid=cur.lastrowid
    except sqlite3.IntegrityError:
        c.close(); return jsonify(error="An account with that email already exists."),409
    c.close(); session["user_id"]=uid
    return jsonify(ok=True)

@app.post("/api/login")
def api_login():
    email=request.form.get("email","").strip().lower(); pw=request.form.get("password","")
    c=db(); u=c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone(); c.close()
    if not u or not check_password_hash(u["password_hash"],pw):
        return jsonify(error="Invalid email or password."),401
    session["user_id"]=u["id"]; return jsonify(ok=True)

@app.get("/logout")
def logout(): session.clear(); return redirect(url_for("index"))

@app.get("/health")
def health(): return jsonify(status="ok", version="7.0")

@app.post("/api/inspect")
def inspect():
    f=request.files.get("file")
    if not f or not f.filename.lower().endswith(".pdf"):
        return jsonify(error="Please upload a PDF file."),400
    src=UPLOADS/(uuid.uuid4().hex+".pdf"); f.save(src)
    try:
        return jsonify(inspect_pdf(src))
    except Exception:
        return jsonify(error="The uploaded file is not a valid/readable PDF."), 400
    finally:
        src.unlink(missing_ok=True)

@app.post("/api/convert")
@login_required
def convert():
    u=current_user()
    # Reserve one credit atomically to prevent two simultaneous requests from
    # consuming the same last credit. Refund it automatically if conversion fails.
    c = db()
    cur = c.execute("UPDATE users SET credits=credits-1 WHERE id=? AND credits>0", (u["id"],))
    c.commit(); c.close()
    if cur.rowcount != 1:
        return jsonify(error="No credits remaining. Upgrade your plan to continue."),402
    f=request.files.get("file")
    if not f or not f.filename.lower().endswith(".pdf"):
        return jsonify(error="Please upload a PDF file."),400

    job_id=uuid.uuid4().hex
    src=UPLOADS/f"{job_id}.pdf"
    name=secure_filename(Path(f.filename).stem) or "converted"
    dst=OUTPUTS/f"{job_id}.docx"
    f.save(src)
    try:
        info=inspect_pdf(src)
        if info["type"]=="scanned_or_image":
            ocr_pdf_to_docx(src,dst); mode="ocr"
        else:
            convert_pdf_to_docx(src,dst); mode="layout"

        c=db()
        c.execute("INSERT INTO jobs(id,user_id,filename,pages,mode,status,created_at) VALUES(?,?,?,?,?,?,?)",
                  (job_id,u["id"],name+".pdf",info["pages"],mode,"completed",int(time.time())))
        c.commit(); c.close()

        # Read the finished file into memory before deleting it. This avoids
        # Windows file-lock issues caused by deleting a file still being sent.
        payload = dst.read_bytes()
        return send_file(io.BytesIO(payload), as_attachment=True, download_name=name+".docx",
                         mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        # Refund the reserved credit when conversion fails.
        c=db(); c.execute("UPDATE users SET credits=credits+1 WHERE id=?", (u["id"],)); c.execute("INSERT INTO jobs(id,user_id,filename,pages,mode,status,created_at) VALUES(?,?,?,?,?,?,?)",
                          (job_id,u["id"],name+".pdf",0,"unknown","failed",int(time.time()))); c.commit(); c.close()
        return jsonify(error=f"Conversion failed: {e}"),500
    finally:
        src.unlink(missing_ok=True); dst.unlink(missing_ok=True)

@app.errorhandler(413)
def too_large(_): return jsonify(error="Maximum file size is 50 MB."),413

if __name__=="__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT","5000")), debug=False)
