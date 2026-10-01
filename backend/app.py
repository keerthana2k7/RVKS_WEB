import os
import sys
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import init_db
from database.seed_data import seed
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.dashboard import dashboard_bp
from routes.workers import workers_bp, get_attendance, mark_single_attendance, mark_bulk_attendance, get_attendance_stats, get_payments, record_payment
from routes.birds import birds_bp
from routes.eggs import eggs_bp
from routes.raw_materials import raw_materials_bp
from routes.feed import feed_bp
from routes.finance import finance_bp
from routes.reports import reports_bp
from routes.sync import sync_bp

FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# Register API Blueprints (All Admin Protected)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(workers_bp)
app.register_blueprint(birds_bp)
app.register_blueprint(eggs_bp)
app.register_blueprint(raw_materials_bp)
app.register_blueprint(raw_materials_bp, url_prefix="/api/materials", name="materials") # Alias
app.register_blueprint(feed_bp)
app.register_blueprint(finance_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(sync_bp)

# Top-level API aliases for Attendance & Payments
@app.route("/api/attendance", methods=["GET", "POST"])
def api_attendance_alias():
    if request.method == "GET":
        return get_attendance()
    return mark_single_attendance()

@app.route("/api/attendance/bulk", methods=["POST"])
def api_attendance_bulk_alias():
    return mark_bulk_attendance()

@app.route("/api/attendance/stats", methods=["GET"])
def api_attendance_stats_alias():
    return get_attendance_stats()

@app.route("/api/payments", methods=["GET", "POST"])
def api_payments_alias():
    if request.method == "GET":
        return get_payments()
    return record_payment()

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "details": str(e)}), 500

def create_app():
    # Initialize DB and seed
    init_db()
    seed()
    return app

if __name__ == "__main__":
    init_db()
    seed()
    port = int(os.environ.get("PORT", 5000))
    print(f"============================================================")
    print(f"  RVKS WEB - Poultry Farm Management System (Admin Only)")
    print(f"  Server starting at: http://127.0.0.1:{port}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
