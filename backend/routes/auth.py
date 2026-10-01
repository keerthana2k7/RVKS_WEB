from flask import Blueprint, request, jsonify, g
import hashlib
import hmac
import time
import json
import base64
from functools import wraps
from database.db import get_db, log_audit

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SECRET_KEY = "rvks_secret_token_key_farm_2026"
SALT = "rvks_poultry_salt_2026"

def hash_password(password: str) -> str:
    return hashlib.sha256(f"{SALT}_{password}".encode("utf-8")).hexdigest()

def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + (30 * 24 * 3600) # 30 days session
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def verify_token(token: str):
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        # Pad b64
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif "token" in request.args:
            token = request.args.get("token")
        
        user_data = verify_token(token)
        if not user_data:
            return jsonify({"error": "Admin authentication required. Please log in as Farm Owner / Admin."}), 401
        
        # Enforce that ONLY Farm Owner / Admin can access protected endpoints
        if user_data.get("role") not in ("owner_admin", "admin"):
            return jsonify({"error": "Access denied. Only Farm Owner / Admin can access this system."}), 403
        
        g.user = user_data
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif "token" in request.args:
            token = request.args.get("token")
        
        user_data = verify_token(token)
        if not user_data:
            return jsonify({"error": "Admin authentication required. Please log in as Farm Owner / Admin."}), 401
        
        if user_data.get("role") not in ("owner_admin", "admin"):
            return jsonify({"error": "Access denied. Only Farm Owner / Admin can access this system."}), 403
        
        g.user = user_data
        return f(*args, **kwargs)
    return decorated

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "Admin Username/Email and Password are required"}), 400
    
    hashed = hash_password(password)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, full_name, role, status FROM users WHERE (username = ? OR LOWER(username) = LOWER(?)) AND password_hash = ?",
            (username, username, hashed)
        )
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "Invalid credentials. Admin access only."}), 401
            
        # STRICT ADMIN-ONLY: reject any non-admin account immediately
        if user.get("role") not in ("owner_admin", "admin"):
            return jsonify({"error": "Access denied. Only Farm Owner / Admin has access to this system. Workers do not have login accounts."}), 403
            
        if user["status"] != "active":
            return jsonify({"error": "Admin account is deactivated."}), 403
        
        token = create_token(user["id"], user["username"], user["role"])
        log_audit("Admin Login", "Auth", user["id"], f"Farm Owner logged in from {request.remote_addr}", user_id=user["id"], username=user["username"], conn=conn)
        
        return jsonify({
            "message": "Admin authentication successful",
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": "owner_admin"
            }
        })

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_audit("Admin Logout", "Auth", g.user.get("user_id"), "Admin logged out", user_id=g.user.get("user_id"), username=g.user.get("username"))
    return jsonify({"message": "Logged out successfully"})

@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role, status, created_at FROM users WHERE id = ?", (g.user["user_id"],))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Admin user not found"}), 404
        return jsonify({"user": user})

@auth_bp.route("/status", methods=["GET"])
@login_required
def status():
    return jsonify({
        "status": "authenticated",
        "role": "owner_admin",
        "username": g.user.get("username"),
        "user_id": g.user.get("user_id")
    })
