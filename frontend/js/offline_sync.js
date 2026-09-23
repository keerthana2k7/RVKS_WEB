// RVKS WEB: Offline Storage & Synchronization Engine (IndexedDB + Auto Sync)
import { Api } from "./api.js";

const DB_NAME = "RVKS_Poultry_OfflineDB";
const STORE_NAME = "offline_sync_queue";
const DB_VERSION = 1;

class OfflineSyncEngine {
  constructor() {
    this.db = null;
    this.isSyncing = false;
    this.initIndexedDB();
    this.bindNetworkListeners();
  }

  initIndexedDB() {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "queue_id" });
      }
    };
    request.onsuccess = (e) => {
      this.db = e.target.result;
      this.updateStatusBadge();
      // Auto-sync on startup if online
      if (navigator.onLine) {
        this.syncNow();
      }
    };
    request.onerror = (e) => {
      console.warn("[OfflineSync] IndexedDB failed to initialize. Falling back to localStorage.", e);
    };
  }

  bindNetworkListeners() {
    window.addEventListener("online", () => {
      console.log("[OfflineSync] Device is back ONLINE. Initiating sync...");
      this.updateStatusBadge();
      this.syncNow();
    });

    window.addEventListener("offline", () => {
      console.warn("[OfflineSync] Device went OFFLINE. Offline mode enabled.");
      this.updateStatusBadge();
    });
  }

  async enqueue(type, payload) {
    const record = {
      queue_id: `OFFLINE_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      payload,
      created_at: new Date().toISOString(),
      status: "pending_sync"
    };

    if (this.db) {
      return new Promise((resolve, reject) => {
        const tx = this.db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        const req = store.add(record);
        req.onsuccess = () => {
          this.updateStatusBadge();
          resolve(record);
        };
        req.onerror = () => reject(req.error);
      });
    } else {
      // Fallback
      const current = JSON.parse(localStorage.getItem("rvks_offline_queue") || "[]");
      current.push(record);
      localStorage.setItem("rvks_offline_queue", JSON.stringify(current));
      this.updateStatusBadge();
      return record;
    }
  }

  async getPendingRecords() {
    if (this.db) {
      return new Promise((resolve) => {
        const tx = this.db.transaction(STORE_NAME, "readonly");
        const store = tx.objectStore(STORE_NAME);
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => resolve([]);
      });
    } else {
      return JSON.parse(localStorage.getItem("rvks_offline_queue") || "[]");
    }
  }

  async removeRecord(queue_id) {
    if (this.db) {
      return new Promise((resolve) => {
        const tx = this.db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        const req = store.delete(queue_id);
        req.onsuccess = () => resolve();
        req.onerror = () => resolve();
      });
    } else {
      let current = JSON.parse(localStorage.getItem("rvks_offline_queue") || "[]");
      current = current.filter(r => r.queue_id !== queue_id);
      localStorage.setItem("rvks_offline_queue", JSON.stringify(current));
    }
  }

  async syncNow() {
    if (this.isSyncing || !navigator.onLine || !Api.isLoggedIn()) {
      return;
    }

    const pending = await this.getPendingRecords();
    if (pending.length === 0) {
      this.updateStatusBadge();
      return;
    }

    this.isSyncing = true;
    console.log(`[OfflineSync] Syncing ${pending.length} pending records with backend...`);
    this.renderSyncState("syncing", pending.length);

    try {
      const response = await Api.post("/api/sync", { records: pending });
      if (response && response.results) {
        for (const res of response.results) {
          if (res.status === "synced") {
            await this.removeRecord(res.queue_id);
          }
        }
      }
      this.renderSyncState("synced");
      window.dispatchEvent(new CustomEvent("farm:data_synced"));
    } catch (error) {
      console.error("[OfflineSync] Error syncing records:", error);
    } finally {
      this.isSyncing = false;
      this.updateStatusBadge();
    }
  }

  async updateStatusBadge() {
    const pending = await this.getPendingRecords();
    const count = pending.length;
    const isOnline = navigator.onLine;

    if (!isOnline) {
      this.renderSyncState("offline", count);
    } else if (count > 0) {
      this.renderSyncState("pending", count);
    } else {
      this.renderSyncState("online");
    }
  }

  renderSyncState(state, count = 0) {
    const indicator = document.getElementById("syncIndicator");
    if (!indicator) return;

    indicator.className = `sync-indicator ${state}`;
    if (state === "offline") {
      indicator.innerHTML = `<span class="status-dot"></span> Offline ${count > 0 ? `(${count} Pending)` : ''}`;
      indicator.title = "Offline Mode - Records will be saved locally and synced once internet connects.";
    } else if (state === "pending" || state === "syncing") {
      indicator.innerHTML = `<span class="status-dot"></span> Pending Sync (${count})`;
      indicator.title = "Click to sync offline records to the farm server.";
    } else if (state === "synced") {
      indicator.className = "sync-indicator online";
      indicator.innerHTML = `<span class="status-dot"></span> Synced ✓`;
      setTimeout(() => this.updateStatusBadge(), 3000);
    } else {
      indicator.innerHTML = `<span class="status-dot"></span> Online`;
      indicator.title = "Connected to RVKS Farm Backend";
    }
  }
}

export const OfflineSync = new OfflineSyncEngine();
