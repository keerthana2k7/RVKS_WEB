from flask import Blueprint, jsonify, request, g
from database.db import get_db
from routes.auth import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.route("/status", methods=["GET"])
@admin_required
def get_admin_status():
    """Confirms admin authentication status and privileges."""
    return jsonify({
        "status": "authenticated",
        "role": "owner_admin",
        "username": g.user.get("username"),
        "full_name": g.user.get("full_name", "Farm Owner"),
        "access_level": "Full System Administrator"
    })

@admin_bp.route("/overview", methods=["GET"])
@admin_required
def get_admin_overview():
    """Direct high-level operational overview for the Farm Owner."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM workers WHERE status = 'Active'")
        active_workers = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM workers")
        total_workers = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COALESCE(SUM(current_quantity), 0) as count FROM bird_batches WHERE status = 'Active'")
        total_flock = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COALESCE(SUM(current_stock), 0) as stock FROM raw_materials")
        materials_stock = cursor.fetchone()["stock"]
        
        cursor.execute("SELECT COALESCE(SUM(current_stock), 0) as stock FROM feed_stock")
        feed_stock = cursor.fetchone()["stock"]
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as pending FROM worker_payments WHERE status = 'Pending'")
        pending_wages = cursor.fetchone()["pending"]
        
    return jsonify({
        "admin_user": g.user.get("username"),
        "total_workers": total_workers,
        "active_workers": active_workers,
        "total_flock": total_flock,
        "raw_materials_kg": materials_stock,
        "finished_feed_kg": feed_stock,
        "pending_wages_inr": pending_wages
    })
