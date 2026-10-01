// RVKS WEB — Poultry Farm Management System Master Controller
import { Api } from "./api.js";
import { OfflineSync } from "./offline_sync.js";
import { showToast, openModal, closeModal, formatDate, formatDateTime } from "./utils.js";
import { Auth } from "./auth.js";
import { loadDashboard } from "./dashboard.js";
import { loadComponent, loadShellComponents, ensureViewLoaded, preloadAllViews, initModalListeners, populateDropdowns, initForms } from "./components.js";

// Global App State
export const State = {
  currentView: "dashboard",
  user: null,
  dashboardData: null,
  cachedDropdowns: {
    batches: [],
    workers: [],
    suppliers: [],
    materials: [],
    recipes: [],
    feedTypes: []
  }
};

/**
 * Router & View Switcher
 * Ensures modular page HTML is loaded, activates section, and dispatches data loader
 * @param {string} viewId - ID of view section
 */
export async function navigateTo(viewId) {
  State.currentView = viewId;

  // Update sidebar active class
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.dataset.view === viewId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Ensure view component is fetched & mounted into DOM
  await ensureViewLoaded(viewId);

  // Hide all view sections and children of appContent
  const container = document.getElementById("appContent");
  if (container) {
    Array.from(container.children).forEach(el => {
      el.classList.remove("active");
      el.style.display = "none";
    });
  }
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.classList.remove("active");
    sec.style.display = "none";
  });

  // Show target section
  const targetId = `view-${viewId === 'birds' ? 'batches' : viewId}`;
  const targetSec = document.getElementById(targetId);
  if (targetSec) {
    targetSec.classList.add("active");
    targetSec.style.display = "block";
  }

  // Close mobile sidebar if open
  const sidebar = document.getElementById("appSidebar");
  if (sidebar && sidebar.classList.contains("open")) {
    sidebar.classList.remove("open");
  }

  // Load view data
  await loadViewData(viewId);
}

/**
 * Data Loader Dispatcher
 * @param {string} viewId
 */
export async function loadViewData(viewId) {
  try {
    switch (viewId) {
      case "dashboard":
        await loadDashboard();
        break;
      case "workers":
        await loadWorkers();
        break;
      case "attendance":
        await loadAttendance();
        break;
      case "payments":
        await loadPayments();
        break;
      case "birds":
        await loadBirds();
        break;
      case "batches":
        await loadBatches();
        break;
      case "mortality":
        await loadMortality();
        break;
      case "eggs":
        await loadEggs();
        break;
      case "suppliers":
        await loadSuppliers();
        break;
      case "raw-materials":
        await loadRawMaterials();
        break;
      case "purchases":
        await loadPurchases();
        break;
      case "feed-recipes":
        await loadRecipes();
        break;
      case "feed-production":
        await loadFeedProduction();
        break;
      case "feed-stock":
        await loadFeedStock();
        break;
      case "feed-usage":
        await loadFeedUsage();
        break;
      case "expenses":
        await loadExpenses();
        break;
      case "income":
        await loadIncome();
        break;
      case "reports":
        await loadReportsView();
        break;
      case "audit":
        await loadAuditLogs();
        break;
      case "profile":
      case "settings":
        loadProfile();
        break;
      case "inventory":
        await loadFeedStock();
        break;
    }
  } catch (error) {
    console.error(`Error loading view ${viewId}:`, error);
    showToast(`Error: ${error.message}`, "error");
  }
}

// ----------------- VIEW 2: WORKERS (ADMIN ONLY - WORKERS ARE RECORDS ONLY) ----------------- //
let allWorkersCache = [];

async function loadWorkers() {
  const data = await Api.get("/api/workers");
  allWorkersCache = data.workers || [];
  State.cachedDropdowns.workers = allWorkersCache;
  renderWorkersTable(allWorkersCache);
}

function renderWorkersTable(workers) {
  const tbody = document.querySelector("#tableWorkers tbody");
  if (!tbody) return;

  if (workers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-dim); padding: 2rem;">No worker records found. Click "+ Add Worker Record" to add personnel.</td></tr>`;
    return;
  }

  tbody.innerHTML = workers.map(w => `
    <tr>
      <td><strong>${w.worker_code}</strong></td>
      <td>
        <strong style="color: #fff; cursor: pointer;" onclick="window.viewWorkerHistory(${w.id})" title="Click to view history">${w.name}</strong>
      </td>
      <td>${w.job_role}</td>
      <td>
        <div>📞 ${w.phone || '-'}</div>
        <div style="font-size: 0.8rem; color: var(--text-dim);">${w.address || ''}</div>
      </td>
      <td>${w.date_of_joining || '-'}</td>
      <td><strong>₹${Number(w.salary_amount || 0).toLocaleString()}</strong> <span style="font-size: 0.78rem; color: var(--text-dim);">(${w.salary_type})</span></td>
      <td>
        <span class="badge ${w.payment_status === 'Paid' ? 'success' : 'warning'}">${w.payment_status || 'Pending'}</span>
      </td>
      <td>${w.payment_date || '-'}</td>
      <td>
        <span class="badge ${w.status === 'Active' ? 'success' : 'danger'}">${w.status}</span>
      </td>
      <td>
        <div style="display: flex; gap: 0.35rem; justify-content: center; flex-wrap: wrap;">
          <button class="btn btn-primary btn-sm" onclick="window.openMakePayment(${w.id})" title="Make Payment for ${w.name}">
            💳 Pay
          </button>
          <button class="btn btn-secondary btn-sm" onclick="window.editWorker(${w.id})" title="Edit Worker Details">
            ✏️ Edit
          </button>
          <button class="btn btn-secondary btn-sm" onclick="window.viewWorkerHistory(${w.id})" title="View Attendance & Payment History">
            📜 History
          </button>
          <button class="btn btn-secondary btn-sm" onclick="window.toggleWorkerStatus(${w.id}, '${w.status === 'Active' ? 'Inactive' : 'Active'}')" title="Toggle Active/Inactive">
            ${w.status === 'Active' ? 'Deactivate' : 'Activate'}
          </button>
          <button class="btn btn-danger btn-sm" onclick="window.deleteWorker(${w.id}, '${w.name.replace(/'/g, "\\'")}')" title="Delete Record">
            🗑️
          </button>
        </div>
      </td>
    </tr>
  `).join("");
}

window.filterWorkers = function() {
  const search = (document.getElementById("workerSearchInput")?.value || "").toLowerCase().trim();
  const status = document.getElementById("workerStatusFilter")?.value || "";

  let filtered = allWorkersCache;
  if (status) {
    filtered = filtered.filter(w => w.status === status);
  }
  if (search) {
    filtered = filtered.filter(w => 
      (w.name && w.name.toLowerCase().includes(search)) ||
      (w.worker_code && w.worker_code.toLowerCase().includes(search)) ||
      (w.job_role && w.job_role.toLowerCase().includes(search)) ||
      (w.phone && w.phone.toLowerCase().includes(search))
    );
  }
  renderWorkersTable(filtered);
};

window.editWorker = async function(workerId) {
  try {
    const data = await Api.get(`/api/workers/${workerId}`);
    const w = data.worker;
    if (!w) return;

    document.getElementById("editWorkerId").value = w.id;
    document.getElementById("editWorkerName").value = w.name;
    document.getElementById("editWorkerRole").value = w.job_role;
    document.getElementById("editWorkerPhone").value = w.phone || "";
    document.getElementById("editWorkerDoj").value = w.date_of_joining || "";
    document.getElementById("editWorkerSalaryType").value = w.salary_type || "Monthly";
    document.getElementById("editWorkerSalaryAmount").value = w.salary_amount || 0;
    document.getElementById("editWorkerPaymentStatus").value = w.payment_status || "Pending";
    document.getElementById("editWorkerPaymentDate").value = w.payment_date || "";
    document.getElementById("editWorkerPayMethod").value = w.payment_method || "Cash";
    document.getElementById("editWorkerStatus").value = w.status || "Active";
    document.getElementById("editWorkerAddress").value = w.address || "";
    document.getElementById("editWorkerNotes").value = w.notes || "";

    openModal("modalEditWorker");
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.deleteWorker = async function(workerId, workerName) {
  if (!confirm(`Are you sure you want to permanently delete worker record "${workerName}"?\n\nThis will remove this worker from the system, including linked attendance and payment records.`)) {
    return;
  }
  try {
    const res = await Api.delete(`/api/workers/${workerId}`);
    showToast(res.message);
    await loadWorkers();
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.toggleWorkerStatus = async function(workerId, newStatus) {
  if (!confirm(`Are you sure you want to mark this worker as ${newStatus}?`)) return;
  try {
    await Api.patch(`/api/workers/${workerId}/status`, { status: newStatus });
    showToast(`Worker marked as ${newStatus}`);
    await loadWorkers();
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.viewWorkerHistory = async function(workerId) {
  try {
    const data = await Api.get(`/api/workers/${workerId}/history`);
    const w = data.worker;
    const att = data.attendance || [];
    const pmt = data.payments || [];
    const attStats = data.attendance_stats || {};
    const pmtStats = data.payment_stats || {};

    const container = document.getElementById("workerHistoryContent");
    if (!container) return;

    container.innerHTML = `
      <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
          <div>
            <h4 style="font-size: 1.25rem; font-weight: 700; color: #fff; margin-bottom: 0.25rem;">${w.name} <span class="badge ${w.status === 'Active' ? 'success' : 'danger'}">${w.status}</span></h4>
            <p style="color: var(--amber-400); font-weight: 600; font-size: 0.95rem; margin-bottom: 0.35rem;">${w.job_role} &bull; ${w.worker_code}</p>
            <p style="font-size: 0.85rem; color: var(--text-dim);">Phone: <strong style="color: var(--text-main);">${w.phone || '-'}</strong> | Joined: <strong style="color: var(--text-main);">${w.date_of_joining || '-'}</strong></p>
            <p style="font-size: 0.85rem; color: var(--text-dim); margin-top: 0.2rem;">Address: ${w.address || 'None'}</p>
          </div>
          <div style="text-align: right; background: rgba(0,0,0,0.2); padding: 0.75rem 1rem; border-radius: 6px;">
            <div style="font-size: 0.8rem; color: var(--text-dim);">Salary Setting</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: var(--primary-400);">₹${Number(w.salary_amount).toLocaleString()}</div>
            <div style="font-size: 0.8rem; color: var(--text-dim);">${w.salary_type} via ${w.payment_method}</div>
          </div>
        </div>
      </div>

      <!-- KPI Summary Row -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem;">
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); padding: 0.75rem; border-radius: 6px; text-align: center;">
          <div style="font-size: 0.75rem; color: var(--text-dim);">Present Days</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: var(--primary-400);">${attStats.present_days || 0}</div>
        </div>
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.75rem; border-radius: 6px; text-align: center;">
          <div style="font-size: 0.75rem; color: var(--text-dim);">Absent Days</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: var(--danger-500);">${attStats.absent_days || 0}</div>
        </div>
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); padding: 0.75rem; border-radius: 6px; text-align: center;">
          <div style="font-size: 0.75rem; color: var(--text-dim);">Half / Leave</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: var(--amber-400);">${(attStats.half_days || 0) + (attStats.leave_days || 0)}</div>
        </div>
        <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); padding: 0.75rem; border-radius: 6px; text-align: center;">
          <div style="font-size: 0.75rem; color: var(--text-dim);">Total Paid Wages</div>
          <div style="font-size: 1.15rem; font-weight: 700; color: #60a5fa;">₹${Number(pmtStats.total_paid || 0).toLocaleString()}</div>
        </div>
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); padding: 0.75rem; border-radius: 6px; text-align: center;">
          <div style="font-size: 0.75rem; color: var(--text-dim);">Pending Wages</div>
          <div style="font-size: 1.15rem; font-weight: 700; color: var(--amber-400);">₹${Number(pmtStats.total_pending || 0).toLocaleString()}</div>
        </div>
      </div>

      <!-- Wage Payments Section -->
      <h4 style="font-size: 1rem; color: var(--text-main); margin-bottom: 0.75rem;">💳 Wage Settlements & Payment History</h4>
      <div class="table-responsive" style="max-height: 200px; overflow-y: auto; margin-bottom: 1.5rem; border: 1px solid var(--border-color); border-radius: 6px;">
        <table class="data-table" style="font-size: 0.85rem;">
          <thead>
            <tr>
              <th>Code</th>
              <th>Period</th>
              <th>Payment Date</th>
              <th>Amount</th>
              <th>Method</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            ${pmt.length === 0 ? `<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">No payment records found for this worker.</td></tr>` : 
              pmt.map(p => `
                <tr>
                  <td><strong>${p.payment_code}</strong></td>
                  <td>${p.salary_period}</td>
                  <td>${p.payment_date}</td>
                  <td><strong style="color: var(--primary-300);">₹${Number(p.amount).toLocaleString()}</strong></td>
                  <td>${p.payment_method}</td>
                  <td><span class="badge ${p.status === 'Paid' ? 'success' : 'warning'}">${p.status}</span></td>
                  <td>${p.notes || '-'}</td>
                </tr>
              `).join("")
            }
          </tbody>
        </table>
      </div>

      <!-- Attendance History Section -->
      <h4 style="font-size: 1rem; color: var(--text-main); margin-bottom: 0.75rem;">📅 Recent Attendance Logs (Last 60 Records)</h4>
      <div class="table-responsive" style="max-height: 220px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 6px;">
        <table class="data-table" style="font-size: 0.85rem;">
          <thead>
            <tr>
              <th>Date</th>
              <th>Status</th>
              <th>Check-in</th>
              <th>Check-out</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            ${att.length === 0 ? `<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No attendance records found for this worker.</td></tr>` : 
              att.map(a => `
                <tr>
                  <td><strong>${a.date}</strong></td>
                  <td>
                    <span class="badge ${a.status === 'Present' ? 'success' : a.status === 'Absent' ? 'danger' : 'warning'}">${a.status}</span>
                  </td>
                  <td>${a.check_in_time || '-'}</td>
                  <td>${a.check_out_time || '-'}</td>
                  <td>${a.notes || '-'}</td>
                </tr>
              `).join("")
            }
          </tbody>
        </table>
      </div>
    `;

    openModal("modalWorkerHistory");
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ----------------- VIEW 3: ATTENDANCE ----------------- //
async function loadAttendance() {
  const dateInput = document.getElementById("attendanceDateFilter");
  const selectedDate = dateInput ? dateInput.value : new Date().toISOString().slice(0, 10);
  
  const data = await Api.get("/api/workers/attendance", { date: selectedDate });
  const tbody = document.querySelector("#tableAttendance tbody");
  if (!tbody) return;

  tbody.innerHTML = data.records.map(r => `
    <tr>
      <td><strong>${r.worker_code}</strong></td>
      <td><strong>${r.name}</strong></td>
      <td>${r.job_role}</td>
      <td>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <label style="cursor: pointer;"><input type="radio" name="att_${r.worker_id}" value="Present" ${r.status === 'Present' ? 'checked' : ''} onchange="window.markAttendance(${r.worker_id}, 'Present')"> Present</label>
          <label style="cursor: pointer;"><input type="radio" name="att_${r.worker_id}" value="Absent" ${r.status === 'Absent' ? 'checked' : ''} onchange="window.markAttendance(${r.worker_id}, 'Absent')"> Absent</label>
          <label style="cursor: pointer;"><input type="radio" name="att_${r.worker_id}" value="Half Day" ${r.status === 'Half Day' ? 'checked' : ''} onchange="window.markAttendance(${r.worker_id}, 'Half Day')"> Half Day</label>
          <label style="cursor: pointer;"><input type="radio" name="att_${r.worker_id}" value="Leave" ${r.status === 'Leave' ? 'checked' : ''} onchange="window.markAttendance(${r.worker_id}, 'Leave')"> Leave</label>
        </div>
      </td>
      <td><input type="text" class="form-control" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;" value="${r.check_in_time || ''}" placeholder="06:30" onblur="window.updateAttTime(${r.worker_id}, 'check_in', this.value)"></td>
      <td><input type="text" class="form-control" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;" value="${r.check_out_time || ''}" placeholder="18:00" onblur="window.updateAttTime(${r.worker_id}, 'check_out', this.value)"></td>
      <td><input type="text" class="form-control" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;" value="${r.notes || ''}" placeholder="Notes" onblur="window.updateAttNotes(${r.worker_id}, this.value)"></td>
    </tr>
  `).join("");
}

window.markAttendance = async function(workerId, status) {
  const date = document.getElementById("attendanceDateFilter")?.value || new Date().toISOString().slice(0, 10);
  const payload = {
    worker_id: workerId,
    date,
    status,
    check_in_time: status === "Present" || status === "Half Day" ? "06:30" : null,
    check_out_time: status === "Present" || status === "Half Day" ? "18:00" : null
  };

  try {
    if (!navigator.onLine) {
      await OfflineSync.enqueue("attendance", payload);
      showToast("Offline: Attendance saved locally as Pending Sync", "info");
    } else {
      await Api.post("/api/workers/attendance", payload);
      showToast(`Marked ${status} for worker #${workerId}`);
    }
  } catch (err) {
    if (err.isOffline) {
      await OfflineSync.enqueue("attendance", payload);
      showToast("Network down. Saved locally as Pending Sync", "info");
    } else {
      showToast(err.message, "error");
    }
  }
};

window.updateAttTime = async function(workerId, type, val) {
  // Optional detailed time edit
};

window.updateAttNotes = async function(workerId, val) {
  // Optional notes edit
};

// ----------------- VIEW 4: DIRECT WORKER PAYROLL & PAYMENTS ----------------- //
let cachedPayrollWorkers = [];

export async function loadPayments() {
  const searchInput = document.getElementById("payrollSearchInput");
  const statusFilter = document.getElementById("payrollStatusFilter");
  const monthFilter = document.getElementById("payrollMonthFilter");

  // Default month filter to current year-month if empty
  const today = new Date();
  const currentMonthIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  if (monthFilter && !monthFilter.value) {
    monthFilter.value = currentMonthIso;
  }

  const selectedMonth = monthFilter?.value || currentMonthIso;
  const selectedStatus = statusFilter?.value || "All";
  const searchVal = searchInput?.value?.trim() || "";

  const queryParams = new URLSearchParams();
  if (selectedMonth) queryParams.set("month", selectedMonth);
  if (selectedStatus && selectedStatus !== "All") queryParams.set("status", selectedStatus);
  if (searchVal) queryParams.set("search", searchVal);

  try {
    const data = await Api.get(`/api/workers/payroll?${queryParams.toString()}`);
    cachedPayrollWorkers = data.payroll || [];
    const summary = data.summary || {};

    // 1. Update 6 Summary KPI Cards
    const elWorkers = document.getElementById("payrollSummaryWorkers");
    if (elWorkers) elWorkers.innerText = summary.total_workers || 0;

    const elDue = document.getElementById("payrollSummarySalaryDue");
    if (elDue) elDue.innerText = `₹${Number(summary.total_salary_due || 0).toLocaleString()}`;

    const elPaid = document.getElementById("payrollSummaryPaid");
    if (elPaid) elPaid.innerText = `₹${Number(summary.total_paid || 0).toLocaleString()}`;

    const elPending = document.getElementById("payrollSummaryPending");
    if (elPending) elPending.innerText = `₹${Number(summary.total_pending || 0).toLocaleString()}`;

    const elAdvance = document.getElementById("payrollSummaryAdvance");
    if (elAdvance) elAdvance.innerText = `₹${Number(summary.total_advance_paid || 0).toLocaleString()}`;

    const elExtra = document.getElementById("payrollSummaryExtra");
    if (elExtra) elExtra.innerText = `₹${Number(summary.total_extra_paid || 0).toLocaleString()}`;

    const elPeriod = document.getElementById("payrollSummaryPeriod");
    if (elPeriod) elPeriod.innerText = `${summary.salary_period || 'Current Cycle'} Cycle`;

    const elBadge = document.getElementById("payrollWorkerCountBadge");
    if (elBadge) elBadge.innerText = `${cachedPayrollWorkers.length} worker${cachedPayrollWorkers.length === 1 ? '' : 's'}`;

    // 2. Render Payroll Ledger Table
    const tbody = document.getElementById("payrollTableBody");
    if (tbody) {
      if (cachedPayrollWorkers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 2rem; color: var(--text-dim);">No payroll records found for the selected criteria.</td></tr>`;
      } else {
        tbody.innerHTML = cachedPayrollWorkers.map(w => {
          let statusBadgeClass = "info";
          if (w.payment_status === "Paid") statusBadgeClass = "success";
          else if (w.payment_status === "Pending") statusBadgeClass = "warning";
          else if (w.payment_status === "Partially Paid") statusBadgeClass = "info";
          else if (w.payment_status === "Overpaid") statusBadgeClass = "danger";

          const dueAlert = w.is_payment_due
            ? `<div style="margin-top: 0.25rem;"><span class="badge danger" style="font-size: 0.72rem;">⚠️ DUE NOW</span></div>`
            : '';

          const remainingColor = w.remaining_amount > 0 ? "var(--amber-400)" : "var(--primary-400)";

          const advanceDisplay = w.advance_paid > 0
            ? `<strong style="color: #a855f7;">₹${Number(w.advance_paid).toLocaleString()}</strong> <span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; font-size: 0.7rem;">Advance</span>`
            : `<span style="color: var(--text-dim);">₹0</span>`;

          const extraDisplay = w.extra_amount_paid > 0
            ? `<strong style="color: #06b6d4;">₹${Number(w.extra_amount_paid).toLocaleString()}</strong> <span class="badge" style="background: rgba(6, 182, 212, 0.15); color: #22d3ee; font-size: 0.7rem;">Extra</span>`
            : `<span style="color: var(--text-dim);">₹0</span>`;

          return `
            <tr style="${w.is_payment_due ? 'background: rgba(239, 68, 68, 0.04);' : ''}">
              <td>
                <span style="font-family: monospace; font-weight: 700; color: var(--primary-300);">${w.worker_code}</span>
              </td>
              <td>
                <div style="font-weight: 700; color: var(--text-main); font-size: 0.98rem;">${w.name}</div>
                <div style="font-size: 0.76rem; color: var(--text-dim); margin-top: 0.1rem;">${w.job_role}</div>
              </td>
              <td>
                <strong>₹${Number(w.regular_salary_due).toLocaleString()}</strong>
                <div style="font-size: 0.74rem; color: var(--text-dim);">${w.salary_type}</div>
              </td>
              <td>
                <div>${formatDate(w.payment_due_date)}</div>
                ${dueAlert}
              </td>
              <td><strong>₹${Number(w.amount_already_paid).toLocaleString()}</strong></td>
              <td>${advanceDisplay}</td>
              <td>${extraDisplay}</td>
              <td>
                <strong style="color: ${remainingColor}; font-size: 1.05rem;">₹${Number(w.remaining_amount).toLocaleString()}</strong>
              </td>
              <td>
                <div style="font-size: 0.85rem;">${w.last_payment_date && w.last_payment_date !== '-' ? formatDate(w.last_payment_date) : '-'}</div>
              </td>
              <td>
                <span class="badge ${statusBadgeClass}">${w.payment_status}</span>
              </td>
              <td style="text-align: center;">
                <div style="display: flex; gap: 0.35rem; justify-content: center; flex-wrap: wrap;">
                  <button class="btn btn-primary btn-sm" onclick="window.openMakePayment(${w.worker_id})" title="Make Payment for ${w.name}">
                    💳 Make Payment
                  </button>
                  <button class="btn btn-secondary btn-sm" onclick="window.viewWorkerPaymentHistory(${w.worker_id})" title="View History">
                    📜 View History
                  </button>
                </div>
              </td>
            </tr>
          `;
        }).join("");
      }
    }

    // 3. Load Global Transactions Log
    await loadAllPaymentTransactions();

  } catch (err) {
    console.error("Failed to load payroll:", err);
    showToast("Error loading payroll data: " + err.message, "error");
  }
}

async function loadAllPaymentTransactions() {
  const tbody = document.getElementById("allPaymentsBody");
  if (!tbody) return;

  try {
    const res = await Api.get("/api/workers/payments");
    const payments = res.payments || [];
    const countBadge = document.getElementById("allPaymentsCountBadge");
    if (countBadge) countBadge.innerText = `${payments.length} record${payments.length === 1 ? '' : 's'}`;

    if (payments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">No transactions recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = payments.map(p => {
      const typeBadge = p.payment_type === 'Advance' ? 'warning' : (p.payment_type === 'Extra' || p.payment_type === 'Bonus') ? 'info' : 'success';
      const baseAmt = Number(p.amount || 0);
      const extraAmt = Number(p.extra_amount || 0);
      const totalAmt = baseAmt + extraAmt;

      return `
        <tr>
          <td><strong>${p.payment_code}</strong></td>
          <td>${formatDate(p.payment_date)}</td>
          <td>
            <strong>${p.worker_name}</strong> 
            <span style="font-size: 0.78rem; color: var(--text-dim);">(${p.worker_code})</span>
          </td>
          <td><span class="badge ${typeBadge}">${p.payment_type || 'Salary'}</span></td>
          <td>₹${baseAmt.toLocaleString()}</td>
          <td>${extraAmt > 0 ? `<span style="color: #06b6d4;">+₹${extraAmt.toLocaleString()}</span>` : '-'}</td>
          <td><strong style="color: var(--primary-400);">₹${totalAmt.toLocaleString()}</strong></td>
          <td>${p.payment_method || 'Cash'}</td>
          <td>
            <div>${p.notes || '-'}</div>
            ${p.extra_reason ? `<small style="color: var(--text-dim);">(Reason: ${p.extra_reason})</small>` : ''}
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.warn("Could not load global payments:", err);
  }
}

// Global Payroll Actions for Window
window.loadPayments = loadPayments;

window.openMakePayment = async function(workerId = null) {
  try {
    let select = document.getElementById("payWorkerSelect");
    
    // 1. Ensure modal markup is loaded in DOM
    if (!select) {
      await loadComponent("/components/modals.html", "modalsMount");
      select = document.getElementById("payWorkerSelect");
    }

    // 2. Ensure payroll workers cache is populated
    if (!cachedPayrollWorkers || cachedPayrollWorkers.length === 0) {
      try {
        const data = await Api.get("/api/workers/payroll");
        cachedPayrollWorkers = data.payroll || [];
      } catch (err) {
        console.warn("Could not load payroll overview for modal:", err);
      }
    }

    // 3. Fallback to /api/workers if payroll list was empty
    if (!cachedPayrollWorkers || cachedPayrollWorkers.length === 0) {
      try {
        const wData = await Api.get("/api/workers?status=Active");
        cachedPayrollWorkers = (wData.workers || []).map(w => ({
          worker_id: w.id,
          worker_code: w.worker_code,
          name: w.name,
          job_role: w.job_role,
          salary_type: w.salary_type || "Monthly",
          regular_salary_due: Number(w.salary_amount || 0),
          remaining_amount: Number(w.salary_amount || 0),
          total_amount_paid: 0,
          payment_due_date: new Date().toISOString().slice(0, 10)
        }));
      } catch (err) {
        console.warn("Could not load workers list:", err);
      }
    }

    // 4. Populate worker select options
    if (select) {
      select.innerHTML = `<option value="">-- Choose Worker --</option>` + cachedPayrollWorkers.map(w => `
        <option value="${w.worker_id}" ${w.worker_id == workerId ? 'selected' : ''}>
          ${w.name} (${w.worker_code}) — Remaining: ₹${Number(w.remaining_amount || 0).toLocaleString()}
        </option>
      `).join("");
      if (workerId) {
        select.value = String(workerId);
      }
    }

    // 5. Pre-fill salary period
    const monthInput = document.getElementById("payrollMonthFilter");
    const periodInput = document.getElementById("payPeriod");
    if (periodInput) {
      if (monthInput && monthInput.value) {
        const parts = monthInput.value.split("-");
        const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, 1);
        periodInput.value = d.toLocaleString('en-US', { month: 'short', year: 'numeric' });
      } else {
        periodInput.value = new Date().toLocaleString('en-US', { month: 'short', year: 'numeric' });
      }
    }

    // 6. Set payment date default to today
    const payDateInput = document.getElementById("payDate");
    if (payDateInput) {
      payDateInput.value = new Date().toISOString().slice(0, 10);
    }

    // 7. Reset extra amount & notes
    const extraInput = document.getElementById("payExtraAmount");
    if (extraInput) extraInput.value = 0;
    const notesInput = document.getElementById("payNotes");
    if (notesInput) notesInput.value = "";
    const typeSelect = document.getElementById("payTypeSelect");
    if (typeSelect) typeSelect.value = "Salary";
    const reasonSelect = document.getElementById("payExtraReason");
    if (reasonSelect) reasonSelect.value = "";

    // 8. Update ledger info banner
    window.onPayWorkerSelected();

    // 9. Open modal
    openModal("modalRecordPayment");
  } catch (err) {
    console.error("Error opening make payment modal:", err);
    showToast("Error opening payment form: " + err.message, "error");
  }
};

window.onPayWorkerSelected = function() {
  const select = document.getElementById("payWorkerSelect");
  const workerId = parseInt(select?.value);
  const worker = cachedPayrollWorkers.find(w => w.worker_id === workerId);

  const elDue = document.getElementById("payModalSalaryDue");
  const elPaid = document.getElementById("payModalAlreadyPaid");
  const elRem = document.getElementById("payModalRemainingDue");
  const elDueDate = document.getElementById("payModalDueDate");
  const amtInput = document.getElementById("payAmount");

  if (worker) {
    if (elDue) elDue.innerText = `₹${Number(worker.regular_salary_due).toLocaleString()}`;
    if (elPaid) elPaid.innerText = `₹${Number(worker.total_amount_paid).toLocaleString()}`;
    if (elRem) elRem.innerText = `₹${Number(worker.remaining_amount).toLocaleString()}`;
    if (elDueDate) elDueDate.innerText = formatDate(worker.payment_due_date);

    if (amtInput) {
      amtInput.value = worker.remaining_amount > 0 ? worker.remaining_amount : worker.regular_salary_due;
    }
  } else {
    if (elDue) elDue.innerText = "₹0";
    if (elPaid) elPaid.innerText = "₹0";
    if (elRem) elRem.innerText = "₹0";
    if (elDueDate) elDueDate.innerText = "-";
    if (amtInput) amtInput.value = "";
  }

  window.updatePayFormPreview();
};

window.updatePayFormPreview = function() {
  const amt = parseFloat(document.getElementById("payAmount")?.value || 0) || 0;
  const extra = parseFloat(document.getElementById("payExtraAmount")?.value || 0) || 0;
  const total = amt + extra;
  const previewEl = document.getElementById("payModalTotalPreview");
  if (previewEl) {
    previewEl.innerText = `₹${total.toLocaleString()}`;
  }

  const select = document.getElementById("payWorkerSelect");
  const workerId = parseInt(select?.value);
  const worker = cachedPayrollWorkers.find(w => w.worker_id === workerId);
  const statusEl = document.getElementById("payModalStatusPreview");

  // 5-step waterfall elements
  const elWfSalary = document.getElementById("calcWaterfallSalary");
  const elWfPaid = document.getElementById("calcWaterfallPaid");
  const elWfAdvance = document.getElementById("calcWaterfallAdvance");
  const elWfExtra = document.getElementById("calcWaterfallExtra");
  const elWfRem = document.getElementById("calcWaterfallRemaining");

  if (worker) {
    const regularSalary = Number(worker.regular_salary_due || 0);
    const alreadyPaid = Number(worker.amount_already_paid || 0);
    const advancePaid = Number(worker.advance_paid || 0);
    
    // New total effective paid towards regular salary
    const newEffPaid = alreadyPaid + advancePaid + amt;
    const newRem = Math.max(0, regularSalary - newEffPaid);

    if (elWfSalary) elWfSalary.innerText = `₹${regularSalary.toLocaleString()}`;
    if (elWfPaid) elWfPaid.innerText = `₹${alreadyPaid.toLocaleString()}`;
    if (elWfAdvance) elWfAdvance.innerText = `₹${advancePaid.toLocaleString()}`;
    if (elWfExtra) elWfExtra.innerText = `₹${extra.toLocaleString()}`;
    if (elWfRem) elWfRem.innerText = `₹${newRem.toLocaleString()}`;

    let expectedStatus = "Pending";
    if (newEffPaid >= regularSalary) {
      expectedStatus = newEffPaid > regularSalary ? "Overpaid" : "Paid";
    } else if (newEffPaid > 0) {
      expectedStatus = "Partially Paid";
    }

    let statusBadgeClass = "info";
    if (expectedStatus === "Paid") statusBadgeClass = "success";
    else if (expectedStatus === "Pending") statusBadgeClass = "warning";
    else if (expectedStatus === "Overpaid") statusBadgeClass = "danger";

    if (statusEl) {
      statusEl.innerHTML = `Status: <span class="badge ${statusBadgeClass}">${expectedStatus}</span> (Balance: ₹${newRem.toLocaleString()})`;
    }
  } else {
    if (elWfSalary) elWfSalary.innerText = "₹0";
    if (elWfPaid) elWfPaid.innerText = "₹0";
    if (elWfAdvance) elWfAdvance.innerText = "₹0";
    if (elWfExtra) elWfExtra.innerText = `₹${extra.toLocaleString()}`;
    if (elWfRem) elWfRem.innerText = "₹0";
    if (statusEl) statusEl.innerHTML = `Status: <span class="badge info">Select Worker</span>`;
  }
};

window.submitRecordPayment = async function(event) {
  if (event) event.preventDefault();
  
  const select = document.getElementById("payWorkerSelect");
  const workerId = parseInt(select?.value);
  const baseAmount = parseFloat(document.getElementById("payAmount")?.value || 0) || 0;
  const extraAmount = parseFloat(document.getElementById("payExtraAmount")?.value || 0) || 0;

  if (!workerId || isNaN(workerId)) {
    showToast("Please select a worker to record payment", "warning");
    return;
  }
  if (baseAmount + extraAmount <= 0) {
    showToast("Please enter a valid payment amount greater than ₹0", "warning");
    return;
  }

  const payload = {
    worker_id: workerId,
    salary_period: document.getElementById("payPeriod")?.value || new Date().toLocaleString('en-US', { month: 'short', year: 'numeric' }),
    payment_date: document.getElementById("payDate")?.value || new Date().toISOString().slice(0, 10),
    amount: baseAmount,
    extra_amount: extraAmount,
    payment_type: document.getElementById("payTypeSelect")?.value || "Salary",
    extra_reason: document.getElementById("payExtraReason")?.value || null,
    payment_method: document.getElementById("payMethodSelect")?.value || "Cash",
    notes: document.getElementById("payNotes")?.value || ""
  };

  const btnSubmit = document.getElementById("btnSavePayment");
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerText = "⏳ Saving...";
  }

  try {
    const res = await Api.post("/api/workers/payments", payload);
    showToast(res.message || "Payment recorded successfully!", "success");
    closeModal("modalRecordPayment");
    
    const form = document.getElementById("formRecordPayment");
    if (form) form.reset();
    
    // Refresh payroll table & stats immediately
    await loadPayments();
  } catch (err) {
    console.error("Payment error:", err);
    showToast("Payment failed: " + err.message, "error");
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerText = "💳 Make Payment";
    }
  }
};

window.viewWorkerPaymentHistory = async function(workerId) {
  try {
    const res = await Api.get(`/api/workers/${workerId}/payments`);
    const worker = res.worker || {};
    const payments = res.payments || [];
    const stats = res.stats || {};

    const subEl = document.getElementById("historyWorkerSub");
    if (subEl) {
      subEl.innerHTML = `<strong>${worker.name}</strong> (${worker.worker_code}) &bull; ${worker.job_role} &bull; Salary: ₹${Number(worker.salary_amount || 0).toLocaleString()} (${worker.salary_type || 'Monthly'})`;
    }

    const baseEl = document.getElementById("historyBasePaid");
    if (baseEl) baseEl.innerText = `₹${Number(stats.total_base_paid || 0).toLocaleString()}`;
    const advEl = document.getElementById("historyAdvancePaid");
    if (advEl) advEl.innerText = `₹${Number(stats.total_advance_paid || 0).toLocaleString()}`;
    const extEl = document.getElementById("historyExtraPaid");
    if (extEl) extEl.innerText = `₹${Number(stats.total_extra_paid || 0).toLocaleString()}`;
    const totEl = document.getElementById("historyTotalReceived");
    if (totEl) totEl.innerText = `₹${Number(stats.total_received || 0).toLocaleString()}`;

    const tbody = document.getElementById("historyTableBody");
    if (tbody) {
      if (payments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">No previous payments found for this worker.</td></tr>`;
      } else {
        tbody.innerHTML = payments.map(p => {
          const typeBadge = p.payment_type === 'Advance' ? 'warning' : (p.payment_type === 'Extra' || p.payment_type === 'Bonus') ? 'info' : 'success';
          const bAmt = Number(p.amount || 0);
          const eAmt = Number(p.extra_amount || 0);
          const tAmt = bAmt + eAmt;

          return `
            <tr>
              <td>${formatDate(p.payment_date)}</td>
              <td><strong>${p.payment_code}</strong></td>
              <td>${p.salary_period || '-'}</td>
              <td><span class="badge ${typeBadge}">${p.payment_type || 'Salary'}</span></td>
              <td>₹${bAmt.toLocaleString()}</td>
              <td>${eAmt > 0 ? `<span style="color: #06b6d4;">+₹${eAmt.toLocaleString()}</span>` : '-'}</td>
              <td><strong style="color: var(--primary-400);">₹${tAmt.toLocaleString()}</strong></td>
              <td>${p.payment_method || 'Cash'}</td>
              <td>
                <div>${p.notes || '-'}</div>
                ${p.extra_reason ? `<small style="color: var(--text-dim);">(Reason: ${p.extra_reason})</small>` : ''}
              </td>
            </tr>
          `;
        }).join("");
      }
    }

    const btnPay = document.getElementById("btnHistoryMakePayment");
    if (btnPay) {
      btnPay.onclick = () => {
        closeModal("modalWorkerPaymentHistory");
        window.openMakePayment(workerId);
      };
    }

    openModal("modalWorkerPaymentHistory");
  } catch (err) {
    showToast("Error loading payment history: " + err.message, "error");
  }
};

window.filterPayroll = function() {
  loadPayments();
};

window.resetPayrollFilters = function() {
  const searchInput = document.getElementById("payrollSearchInput");
  const statusFilter = document.getElementById("payrollStatusFilter");
  const monthFilter = document.getElementById("payrollMonthFilter");

  if (searchInput) searchInput.value = "";
  if (statusFilter) statusFilter.value = "All";
  if (monthFilter) {
    const today = new Date();
    monthFilter.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  }
  loadPayments();
};

window.toggleAllPaymentsList = function() {
  const container = document.getElementById("allPaymentsContainer");
  const chevron = document.getElementById("allPaymentsChevron");
  if (!container) return;
  if (container.style.display === "none") {
    container.style.display = "block";
    if (chevron) chevron.innerText = "▼";
  } else {
    container.style.display = "none";
    if (chevron) chevron.innerText = "▶";
  }
};

// ----------------- VIEW 5: BIRDS & BATCHES ----------------- //
async function loadBatches() {
  const data = await Api.get("/api/birds/batches");
  State.cachedDropdowns.batches = data.batches;

  const tbody = document.querySelector("#tableBatches tbody");
  if (!tbody) return;

  tbody.innerHTML = data.batches.map(b => `
    <tr>
      <td><strong>${b.batch_code}</strong></td>
      <td><strong>${b.batch_name}</strong></td>
      <td><span class="badge info">${b.bird_type}</span></td>
      <td>${formatDate(b.arrival_date)}</td>
      <td>${Number(b.initial_quantity).toLocaleString()}</td>
      <td><strong style="color: var(--primary-400); font-size: 1.05rem;">${Number(b.current_quantity).toLocaleString()}</strong></td>
      <td>${b.shed_location || '-'}</td>
      <td>${b.age_weeks} weeks</td>
      <td><span class="badge ${b.status === 'Active' ? 'success' : 'warning'}">${b.status}</span></td>
      <td>${b.notes || '-'}</td>
    </tr>
  `).join("");
}

async function loadBirds() {
  await loadBatches();
}

// ----------------- VIEW 6: MORTALITY ----------------- //
async function loadMortality() {
  const data = await Api.get("/api/birds/mortality");
  const tbody = document.querySelector("#tableMortality tbody");
  if (!tbody) return;

  tbody.innerHTML = data.records.map(m => `
    <tr>
      <td>${formatDate(m.date)}</td>
      <td><strong>${m.batch_name}</strong> (${m.batch_code})</td>
      <td>${m.bird_type}</td>
      <td><strong style="color: var(--danger-500); font-size: 1.05rem;">${m.number_of_birds}</strong></td>
      <td><span class="badge danger">${m.reason}</span></td>
      <td>${m.shed_location || '-'}</td>
      <td>${m.notes || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 7: EGG PRODUCTION ----------------- //
async function loadEggs() {
  const [recordsData, statsData] = await Promise.all([
    Api.get("/api/eggs"),
    Api.get("/api/eggs/stats")
  ]);

  const todayEl = document.getElementById("eggTodayCount");
  if (todayEl) todayEl.innerText = Number(statsData.today.total).toLocaleString();
  const weekEl = document.getElementById("eggWeekCount");
  if (weekEl) weekEl.innerText = Number(statsData.week.total).toLocaleString();
  const monthEl = document.getElementById("eggMonthCount");
  if (monthEl) monthEl.innerText = Number(statsData.month.total).toLocaleString();
  const incomeEl = document.getElementById("eggMonthIncome");
  if (incomeEl) incomeEl.innerText = `₹${Number(statsData.month.income).toLocaleString()}`;

  const tbody = document.querySelector("#tableEggs tbody");
  if (!tbody) return;

  tbody.innerHTML = recordsData.records.map(e => `
    <tr>
      <td>${formatDate(e.date)}</td>
      <td><strong>${e.batch_name}</strong></td>
      <td><strong>${Number(e.total_eggs).toLocaleString()}</strong></td>
      <td><span style="color: var(--primary-400);">${Number(e.good_eggs).toLocaleString()}</span></td>
      <td><span style="color: var(--amber-400);">${e.broken_eggs}</span> / <span style="color: var(--danger-500);">${e.damaged_eggs}</span></td>
      <td><strong>${Number(e.sold_eggs).toLocaleString()}</strong></td>
      <td>${Number(e.remaining_eggs).toLocaleString()}</td>
      <td>₹${Number(e.selling_price).toFixed(2)}</td>
      <td><strong style="color: var(--primary-400);">₹${Number(e.total_income).toLocaleString()}</strong></td>
      <td>${e.notes || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 8: SUPPLIERS ----------------- //
async function loadSuppliers() {
  const data = await Api.get("/api/raw-materials/suppliers");
  State.cachedDropdowns.suppliers = data.suppliers;

  const tbody = document.querySelector("#tableSuppliers tbody");
  if (!tbody) return;

  tbody.innerHTML = data.suppliers.map(s => `
    <tr>
      <td><strong>${s.supplier_code}</strong></td>
      <td><strong>${s.supplier_name}</strong></td>
      <td>${s.phone || '-'}</td>
      <td>${s.address || '-'}</td>
      <td><span style="color: var(--amber-400);">${s.materials_supplied || '-'}</span></td>
      <td>${s.total_purchases_count}</td>
      <td><strong>₹${Number(s.total_purchase_amount).toLocaleString()}</strong></td>
      <td><span style="color: var(--danger-500); font-weight: 600;">₹${Number(s.pending_payments).toLocaleString()}</span></td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="window.viewSupplierHistory(${s.id})">
          View History
        </button>
      </td>
    </tr>
  `).join("");
}

window.viewSupplierHistory = async function(supplierId) {
  try {
    const data = await Api.get(`/api/raw-materials/suppliers/${supplierId}/history`);
    const historyModal = document.getElementById("modalSupplierHistory");
    if (!historyModal) return;

    document.getElementById("supHistoryName").innerText = data.supplier.supplier_name;
    document.getElementById("supHistoryTotalSpent").innerText = `₹${Number(data.total_spent).toLocaleString()}`;
    document.getElementById("supHistoryPending").innerText = `₹${Number(data.pending_amount).toLocaleString()}`;

    // Material breakdown
    const matDiv = document.getElementById("supHistoryMaterials");
    if (matDiv) {
      matDiv.innerHTML = data.materials_breakdown.map(m => `
        <div style="background: var(--bg-surface-elevated); padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
          <strong style="color: var(--primary-300);">${m.material_name}</strong>: 
          <span>${Number(m.total_qty).toLocaleString()} ${m.unit}</span> (₹${Number(m.total_spent).toLocaleString()})
        </div>
      `).join("");
    }

    // Purchases table
    const tbody = document.querySelector("#tableSupplierPurchases tbody");
    if (tbody) {
      tbody.innerHTML = data.purchases.map(p => `
        <tr>
          <td>${formatDate(p.purchase_date)}</td>
          <td><strong>${p.material_name}</strong></td>
          <td>${Number(p.quantity).toLocaleString()} ${p.material_unit}</td>
          <td>₹${p.rate_per_unit}</td>
          <td><strong>₹${Number(p.total_cost).toLocaleString()}</strong></td>
          <td><span class="badge ${p.payment_status === 'Paid' ? 'success' : 'warning'}">${p.payment_status}</span></td>
        </tr>
      `).join("");
    }

    openModal("modalSupplierHistory");
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ----------------- VIEW 9: RAW MATERIALS ----------------- //
async function loadRawMaterials() {
  const data = await Api.get("/api/raw-materials");
  State.cachedDropdowns.materials = data.materials;

  const tbody = document.querySelector("#tableRawMaterials tbody");
  if (!tbody) return;

  tbody.innerHTML = data.materials.map(m => `
    <tr>
      <td><strong>${m.material_code}</strong></td>
      <td><strong>${m.material_name}</strong></td>
      <td>${m.category}</td>
      <td><strong style="font-size: 1.1rem; color: ${m.status === 'Low Stock' ? 'var(--amber-400)' : m.status === 'Out of Stock' ? 'var(--danger-500)' : 'var(--text-main)'};">${Number(m.current_stock).toLocaleString()} ${m.unit}</strong></td>
      <td>${Number(m.minimum_stock_level).toLocaleString()} ${m.unit}</td>
      <td><span class="badge ${m.status === 'Normal' ? 'success' : m.status === 'Low Stock' ? 'warning' : 'danger'}">${m.status}</span></td>
      <td>${m.notes || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 10: FEED RAW MATERIAL DEALS & PURCHASES ----------------- //
let cachedRawMaterialDeals = [];

export async function loadPurchases() {
  const searchInput = document.getElementById("dealSearchInput");
  const supplierFilter = document.getElementById("dealSupplierFilter");
  const statusFilter = document.getElementById("dealStatusFilter");

  const queryParams = new URLSearchParams();
  if (supplierFilter && supplierFilter.value !== "All") queryParams.set("supplier_id", supplierFilter.value);
  if (statusFilter && statusFilter.value !== "All") queryParams.set("payment_status", statusFilter.value);
  if (searchInput && searchInput.value.trim()) queryParams.set("search", searchInput.value.trim());

  try {
    const data = await Api.get(`/api/raw-materials/deals?${queryParams.toString()}`);
    cachedRawMaterialDeals = data.deals || data.purchases || [];
    const summary = data.summary || {};

    // 1. Update 5 Summary KPI Cards
    const elCount = document.getElementById("dealSummaryCount");
    if (elCount) elCount.innerText = summary.total_deals || 0;

    const elTotal = document.getElementById("dealSummaryTotalAmount");
    if (elTotal) elTotal.innerText = `₹${Number(summary.total_deal_amount || 0).toLocaleString()}`;

    const elPaid = document.getElementById("dealSummaryPaid");
    if (elPaid) elPaid.innerText = `₹${Number(summary.total_amount_paid || 0).toLocaleString()}`;

    const elAdvance = document.getElementById("dealSummaryAdvance");
    if (elAdvance) elAdvance.innerText = `₹${Number(summary.total_advance_paid || 0).toLocaleString()}`;

    const elPending = document.getElementById("dealSummaryPending");
    if (elPending) elPending.innerText = `₹${Number(summary.total_amount_pending || 0).toLocaleString()}`;

    const elBadge = document.getElementById("dealCountBadge");
    if (elBadge) elBadge.innerText = `${cachedRawMaterialDeals.length} deal${cachedRawMaterialDeals.length === 1 ? '' : 's'}`;

    // Populate supplier filter dropdown if empty
    if (supplierFilter && supplierFilter.options.length <= 1) {
      try {
        const suppliersRes = await Api.get("/api/raw-materials/suppliers");
        const sups = suppliersRes.suppliers || [];
        sups.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s.id;
          opt.textContent = `${s.supplier_name} (${s.supplier_code})`;
          supplierFilter.appendChild(opt);
        });
      } catch (e) {
        console.warn("Could not load suppliers for deal filter:", e);
      }
    }

    // 2. Render Deals Table
    renderDealsTable(cachedRawMaterialDeals);
  } catch (err) {
    console.error("Error loading raw material deals:", err);
    showToast(`Error loading deals: ${err.message}`, "error");
  }
}

function renderDealsTable(deals) {
  const tbody = document.getElementById("dealTableBody") || document.querySelector("#tablePurchases tbody");
  if (!tbody) return;

  if (deals.length === 0) {
    tbody.innerHTML = `<tr><td colspan="13" style="text-align: center; padding: 2rem; color: var(--text-dim);">No raw material deals found matching the criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = deals.map(d => {
    let statusClass = "warning";
    if (d.payment_status === "Paid") statusClass = "success";
    else if (d.payment_status === "Partially Paid") statusClass = "info";

    const advanceDisplay = d.advance_paid > 0
      ? `<strong style="color: #a855f7;">₹${Number(d.advance_paid).toLocaleString()}</strong>`
      : `<span style="color: var(--text-dim);">₹0</span>`;

    const pendingColor = d.amount_pending > 0 ? "var(--amber-400)" : "var(--primary-400)";

    return `
      <tr>
        <td>
          <span style="font-family: monospace; font-weight: 700; color: var(--primary-300); font-size: 0.92rem;">${d.purchase_code}</span>
        </td>
        <td>${formatDate(d.deal_date || d.purchase_date)}</td>
        <td>
          <div style="font-weight: 700; color: var(--text-main);">${d.supplier_name}</div>
          <div style="font-size: 0.76rem; color: var(--text-dim); margin-top: 0.1rem;">
            ${d.supplier_code} &bull; ${d.supplier_phone || 'No phone'}
          </div>
        </td>
        <td>
          <div style="font-weight: 600;">${d.material_name}</div>
          <div style="font-size: 0.75rem; color: var(--text-dim);">${d.material_category || 'Feed Ingredient'}</div>
        </td>
        <td>
          <strong>${Number(d.quantity).toLocaleString()} ${d.unit || d.material_unit || 'Kg'}</strong>
        </td>
        <td>₹${Number(d.rate_per_unit).toLocaleString()}</td>
        <td>
          <strong style="color: #60a5fa; font-size: 1.02rem;">₹${Number(d.total_deal_amount || d.total_cost).toLocaleString()}</strong>
        </td>
        <td>${advanceDisplay}</td>
        <td><strong>₹${Number(d.amount_paid || 0).toLocaleString()}</strong></td>
        <td>
          <strong style="color: ${pendingColor}; font-size: 1.02rem;">₹${Number(d.amount_pending || 0).toLocaleString()}</strong>
        </td>
        <td>
          <div style="font-size: 0.84rem;">${d.payment_due_date ? formatDate(d.payment_due_date) : '-'}</div>
        </td>
        <td>
          <span class="badge ${statusClass}">${d.payment_status}</span>
        </td>
        <td style="text-align: center;">
          <div style="display: flex; gap: 0.35rem; justify-content: center; flex-wrap: wrap;">
            <button class="btn btn-primary btn-sm" onclick="window.openRecordDealPayment(${d.id})" title="Record Payment for Deal ${d.purchase_code}">
              💳 Payment
            </button>
            <button class="btn btn-secondary btn-sm" onclick="window.openDealPaymentHistory(${d.id})" title="View Payment History">
              📜 History
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

window.filterDeals = function() {
  loadPurchases();
};

window.resetDealFilters = function() {
  const searchInput = document.getElementById("dealSearchInput");
  const supplierFilter = document.getElementById("dealSupplierFilter");
  const statusFilter = document.getElementById("dealStatusFilter");
  if (searchInput) searchInput.value = "";
  if (supplierFilter) supplierFilter.value = "All";
  if (statusFilter) statusFilter.value = "All";
  loadPurchases();
};

window.openNewDealModal = async function() {
  await populateDropdowns();
  const form = document.getElementById("formRecordPurchase");
  if (form) form.reset();

  const todayIso = new Date().toISOString().slice(0, 10);
  const dealDateInput = document.getElementById("purDealDate");
  if (dealDateInput) dealDateInput.value = todayIso;

  window.onDealMaterialSelected();
  window.updateDealPreview();
  openModal("modalRecordPurchase");
};

window.onDealMaterialSelected = function() {
  const select = document.getElementById("purMaterialSelect");
  if (!select) return;
  const unitInput = document.getElementById("purUnit");
  const matText = select.options[select.selectedIndex]?.text || "";
  if (unitInput) {
    if (matText.includes("Litre")) unitInput.value = "Litre";
    else if (matText.includes("Ton")) unitInput.value = "Ton";
    else unitInput.value = "Kg";
  }
  window.updateDealPreview();
};

window.updateDealPreview = function() {
  const qty = parseFloat(document.getElementById("purQty")?.value || 0) || 0;
  const rate = parseFloat(document.getElementById("purRate")?.value || 0) || 0;
  const transport = parseFloat(document.getElementById("purTransport")?.value || 0) || 0;
  const advance = parseFloat(document.getElementById("purAdvancePaid")?.value || 0) || 0;

  const materialCost = qty * rate;
  const total = materialCost + transport;
  const pending = Math.max(0, total - advance);

  const elTotal = document.getElementById("previewDealTotal");
  const elAdvance = document.getElementById("previewDealAdvance");
  const elPending = document.getElementById("previewDealPending");
  const elStatus = document.getElementById("previewDealStatus");

  if (elTotal) elTotal.innerText = `₹${Math.round(total).toLocaleString()}`;
  if (elAdvance) elAdvance.innerText = `₹${Math.round(advance).toLocaleString()}`;
  if (elPending) elPending.innerText = `₹${Math.round(pending).toLocaleString()}`;

  if (elStatus) {
    let statusText = "Pending";
    let statusClass = "warning";
    if (total > 0 && pending <= 0) {
      statusText = "Paid";
      statusClass = "success";
    } else if (advance > 0) {
      statusText = "Partially Paid";
      statusClass = "info";
    }
    elStatus.innerHTML = `<span class="badge ${statusClass}">${statusText}</span>`;
  }
};

window.submitRecordDeal = async function(event) {
  if (event) event.preventDefault();

  const supplierId = parseInt(document.getElementById("purSupplierSelect")?.value);
  const materialId = parseInt(document.getElementById("purMaterialSelect")?.value);
  const qty = parseFloat(document.getElementById("purQty")?.value || 0);
  const rate = parseFloat(document.getElementById("purRate")?.value || 0);
  const transport = parseFloat(document.getElementById("purTransport")?.value || 0) || 0;
  const advance = parseFloat(document.getElementById("purAdvancePaid")?.value || 0) || 0;

  if (!supplierId || !materialId || qty <= 0 || rate <= 0) {
    showToast("Please enter valid supplier, material, quantity, and rate", "warning");
    return;
  }

  const payload = {
    supplier_id: supplierId,
    material_id: materialId,
    deal_date: document.getElementById("purDealDate")?.value || new Date().toISOString().slice(0, 10),
    payment_due_date: document.getElementById("purPaymentDueDate")?.value || null,
    expected_delivery_date: document.getElementById("purExpectedDelivery")?.value || null,
    actual_delivery_date: document.getElementById("purActualDelivery")?.value || null,
    quantity: qty,
    rate_per_unit: rate,
    transport_cost: transport,
    advance_paid: advance,
    payment_method: document.getElementById("purPaymentMethod")?.value || "Bank Transfer",
    invoice_number: document.getElementById("purInvoice")?.value?.trim() || "",
    notes: document.getElementById("purNotes")?.value?.trim() || ""
  };

  const btn = document.getElementById("btnSaveDeal");
  if (btn) { btn.disabled = true; btn.innerText = "Recording Deal..."; }

  try {
    const res = await Api.post("/api/raw-materials/deals", payload);
    showToast(res.message || "Feed raw material deal recorded successfully!");
    closeModal("modalRecordPurchase");
    document.getElementById("formRecordPurchase")?.reset();
    await loadPurchases();
    await populateDropdowns();
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = "Save Deal & Update Inventory"; }
  }
};

window.openRecordDealPayment = function(dealId) {
  const deal = cachedRawMaterialDeals.find(d => d.id === dealId);
  if (!deal) {
    showToast("Deal record not found", "error");
    return;
  }

  const inputId = document.getElementById("dpayDealId");
  if (inputId) inputId.value = deal.id;

  const elCode = document.getElementById("dpayBannerCode");
  if (elCode) elCode.innerText = deal.purchase_code;

  const elSup = document.getElementById("dpayBannerSupplier");
  if (elSup) elSup.innerText = `${deal.supplier_name} (${deal.material_name})`;

  const elTot = document.getElementById("dpayBannerTotal");
  if (elTot) elTot.innerText = `₹${Number(deal.total_deal_amount || deal.total_cost).toLocaleString()}`;

  const elPaid = document.getElementById("dpayBannerPaid");
  if (elPaid) elPaid.innerText = `₹${Number(deal.amount_paid || 0).toLocaleString()}`;

  const elPend = document.getElementById("dpayBannerPending");
  if (elPend) elPend.innerText = `₹${Number(deal.amount_pending || 0).toLocaleString()}`;

  const dateInput = document.getElementById("dpayDate");
  if (dateInput) dateInput.value = new Date().toISOString().slice(0, 10);

  const amtInput = document.getElementById("dpayAmount");
  if (amtInput) amtInput.value = deal.amount_pending > 0 ? deal.amount_pending : "";

  window.updateDealPaymentPreview();
  openModal("modalRecordDealPayment");
};

window.updateDealPaymentPreview = function() {
  const dealId = parseInt(document.getElementById("dpayDealId")?.value);
  const deal = cachedRawMaterialDeals.find(d => d.id === dealId);
  if (!deal) return;

  const amtToPay = parseFloat(document.getElementById("dpayAmount")?.value || 0) || 0;
  const currentPaid = Number(deal.amount_paid || 0);
  const total = Number(deal.total_deal_amount || deal.total_cost || 0);

  const newTotalPaid = currentPaid + amtToPay;
  const newBalance = Math.max(0, total - newTotalPaid);

  const elBal = document.getElementById("dpayModalBalancePreview");
  if (elBal) elBal.innerText = `₹${Math.round(newBalance).toLocaleString()}`;

  const elStatus = document.getElementById("dpayModalStatusPreview");
  if (elStatus) {
    let statusText = "Pending";
    let statusClass = "warning";
    if (newBalance <= 0) {
      statusText = "Fully Paid";
      statusClass = "success";
    } else if (newTotalPaid > 0) {
      statusText = "Partially Paid";
      statusClass = "info";
    }
    elStatus.innerHTML = `Status: <span class="badge ${statusClass}">${statusText}</span>`;
  }
};

window.submitRecordDealPayment = async function(event) {
  if (event) event.preventDefault();

  const dealId = parseInt(document.getElementById("dpayDealId")?.value);
  const amount = parseFloat(document.getElementById("dpayAmount")?.value || 0);

  if (!dealId || isNaN(dealId) || amount <= 0) {
    showToast("Please enter a valid payment amount greater than ₹0", "warning");
    return;
  }

  const payload = {
    payment_date: document.getElementById("dpayDate")?.value || new Date().toISOString().slice(0, 10),
    payment_type: document.getElementById("dpayTypeSelect")?.value || "Payment",
    amount: amount,
    payment_method: document.getElementById("dpayMethodSelect")?.value || "Bank Transfer",
    notes: document.getElementById("dpayNotes")?.value?.trim() || ""
  };

  try {
    const res = await Api.post(`/api/raw-materials/deals/${dealId}/payments`, payload);
    showToast(res.message || "Payment recorded successfully!");
    closeModal("modalRecordDealPayment");
    document.getElementById("formRecordDealPayment")?.reset();
    await loadPurchases();
    await loadSuppliers();
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
};

window.openDealPaymentHistory = async function(dealId) {
  try {
    const data = await Api.get(`/api/raw-materials/deals/${dealId}/payments`);
    const deal = data.deal || {};
    const payments = data.payments || [];

    const subEl = document.getElementById("dealHistorySub");
    if (subEl) {
      subEl.innerHTML = `Deal: <strong style="color: var(--primary-300);">${deal.purchase_code}</strong> &bull; Supplier: <strong>${deal.supplier_name}</strong> &bull; Material: <strong>${deal.material_name}</strong>`;
    }

    const elTot = document.getElementById("dealHistTotal");
    if (elTot) elTot.innerText = `₹${Number(deal.total_cost || 0).toLocaleString()}`;

    const elPaid = document.getElementById("dealHistPaid");
    if (elPaid) elPaid.innerText = `₹${Number(deal.amount_paid || 0).toLocaleString()}`;

    const elAdv = document.getElementById("dealHistAdvance");
    if (elAdv) elAdv.innerText = `₹${Number(deal.advance_paid || 0).toLocaleString()}`;

    const elPend = document.getElementById("dealHistPending");
    if (elPend) elPend.innerText = `₹${Number(deal.amount_pending || 0).toLocaleString()}`;

    const tbody = document.getElementById("dealPaymentHistoryBody");
    if (tbody) {
      if (payments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">No payment transactions recorded for this deal yet.</td></tr>`;
      } else {
        tbody.innerHTML = payments.map(p => `
          <tr>
            <td>${formatDate(p.payment_date)}</td>
            <td>
              <span class="badge ${p.payment_type === 'Advance' ? 'info' : (p.payment_type === 'Final Payment' ? 'success' : '')}" style="font-size: 0.78rem;">
                ${p.payment_type}
              </span>
            </td>
            <td><strong style="color: var(--primary-400);">₹${Number(p.amount).toLocaleString()}</strong></td>
            <td>${p.payment_method}</td>
            <td>${p.notes || '-'}</td>
          </tr>
        `).join("");
      }
    }

    openModal("modalDealPaymentHistory");
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
};

// ----------------- VIEW 11: FEED RECIPES ----------------- //
async function loadRecipes() {
  const data = await Api.get("/api/feed/recipes");
  State.cachedDropdowns.recipes = data.recipes;

  const container = document.getElementById("recipesGrid");
  if (!container) return;

  container.innerHTML = data.recipes.map(r => `
    <div class="kpi-card" style="display: flex; flex-direction: column; justify-content: space-between;">
      <div>
        <div class="kpi-card-header">
          <span class="badge info">${r.feed_type}</span>
          <span style="font-size: 0.8rem; color: var(--text-dim);">${r.recipe_code}</span>
        </div>
        <h3 style="font-size: 1.2rem; margin-bottom: 0.35rem;">${r.recipe_name}</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">${r.description || 'Standard formulation'}</p>
        
        <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.5rem;">Formula Composition:</h4>
        <div style="display: flex; flex-direction: column; gap: 0.35rem;">
          ${r.items.map(i => `
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.2rem 0; border-bottom: 1px solid var(--border-light);">
              <span>${i.material_name}</span>
              <strong>${i.percentage}% (${i.quantity_per_100kg} kg/100kg)</strong>
            </div>
          `).join("")}
        </div>
      </div>
      <div style="margin-top: 1.25rem;">
        <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="window.quickProduceFromRecipe(${r.id}, '${r.feed_type}', '${r.recipe_name}')">
          Produce Feed with this Recipe
        </button>
      </div>
    </div>
  `).join("");
}

window.quickProduceFromRecipe = function(recipeId, feedType, recipeName) {
  const selRecipe = document.getElementById("feedProdRecipeSelect");
  if (selRecipe) selRecipe.value = recipeId;
  const selType = document.getElementById("feedProdTypeSelect");
  if (selType) selType.value = feedType;
  openModal("modalProduceFeed");
};

// ----------------- VIEW 12: FEED PRODUCTION ----------------- //
async function loadFeedProduction() {
  const data = await Api.get("/api/reports/feed");
  const tbody = document.querySelector("#tableFeedProduction tbody");
  if (!tbody) return;

  tbody.innerHTML = data.data.map(fp => `
    <tr>
      <td><strong>${fp.production_code}</strong></td>
      <td>${formatDate(fp.date)}</td>
      <td><span class="badge info">${fp.feed_type}</span></td>
      <td>${fp.batch_number}</td>
      <td><strong>${Number(fp.quantity_produced).toLocaleString()} ${fp.unit}</strong></td>
      <td>₹${Number(fp.raw_material_cost).toLocaleString()}</td>
      <td>₹${Number(fp.labour_cost).toLocaleString()}</td>
      <td>₹${Number(fp.electricity_cost).toLocaleString()}</td>
      <td><strong style="color: var(--primary-400); font-size: 1.05rem;">₹${Number(fp.total_cost).toLocaleString()}</strong></td>
      <td><strong style="color: var(--amber-400);">₹${Number(fp.cost_per_kg).toFixed(2)}/kg</strong></td>
      <td>${fp.produced_by || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 13: FEED STOCK ----------------- //
async function loadFeedStock() {
  const data = await Api.get("/api/feed/stock");
  State.cachedDropdowns.feedTypes = data.stocks;

  const container = document.getElementById("feedStockCardsGrid");
  if (!container) return;

  container.innerHTML = data.stocks.map(fs => `
    <div class="kpi-card">
      <div class="kpi-card-header">
        <span class="kpi-title">${fs.feed_type}</span>
        <div class="kpi-icon">🌾</div>
      </div>
      <div class="kpi-value">${Number(fs.current_stock).toLocaleString()} ${fs.unit}</div>
      <div class="kpi-subtext ${fs.is_low_stock ? 'highlight' : ''}">
        ${fs.is_low_stock ? `⚠️ Low Stock! Minimum is ${fs.minimum_stock_level} kg` : `Minimum Level: ${fs.minimum_stock_level} kg`}
      </div>
    </div>
  `).join("");
}

// ----------------- VIEW 14: FEED USAGE ----------------- //
async function loadFeedUsage() {
  const data = await Api.get("/api/feed/usage");
  const tbody = document.querySelector("#tableFeedUsage tbody");
  if (!tbody) return;

  tbody.innerHTML = data.usages.map(u => `
    <tr>
      <td><strong>${u.usage_code}</strong></td>
      <td>${formatDate(u.date)}</td>
      <td><strong>${u.batch_name}</strong> (${u.batch_code})</td>
      <td>${u.bird_type}</td>
      <td>${u.feed_type}</td>
      <td><strong style="color: var(--amber-400); font-size: 1.05rem;">${Number(u.quantity).toLocaleString()} ${u.unit}</strong></td>
      <td>${u.notes || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 15: EXPENSES ----------------- //
async function loadExpenses() {
  const data = await Api.get("/api/finance/expenses");
  const tbody = document.querySelector("#tableExpenses tbody");
  if (!tbody) return;

  const expTotal = document.getElementById("expensesTotalAmount");
  if (expTotal) expTotal.innerText = `₹${Number(data.total).toLocaleString()}`;

  tbody.innerHTML = data.expenses.map(e => `
    <tr>
      <td><strong>${e.expense_code}</strong></td>
      <td>${formatDate(e.date)}</td>
      <td><span class="badge info">${e.category}</span></td>
      <td>${e.description}</td>
      <td><strong style="color: var(--danger-500); font-size: 1.05rem;">₹${Number(e.amount).toLocaleString()}</strong></td>
      <td>${e.payment_method}</td>
      <td>${e.paid_by || '-'}</td>
      <td>${e.notes || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 16: INCOME ----------------- //
async function loadIncome() {
  const data = await Api.get("/api/finance/income");
  const tbody = document.querySelector("#tableIncome tbody");
  if (!tbody) return;

  const incTotal = document.getElementById("incomeTotalAmount");
  if (incTotal) incTotal.innerText = `₹${Number(data.total).toLocaleString()}`;

  tbody.innerHTML = data.incomes.map(i => `
    <tr>
      <td><strong>${i.income_code}</strong></td>
      <td>${formatDate(i.date)}</td>
      <td><span class="badge success">${i.source}</span></td>
      <td>${i.description}</td>
      <td>${i.quantity > 0 ? `${Number(i.quantity).toLocaleString()} @ ₹${i.rate}` : '-'}</td>
      <td><strong style="color: var(--primary-400); font-size: 1.05rem;">₹${Number(i.amount).toLocaleString()}</strong></td>
      <td>${i.payment_method}</td>
      <td>${i.notes || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 17: REPORTS ----------------- //
async function loadReportsView() {
  const reportType = document.getElementById("reportTypeSelect")?.value || "complete";
  const fromDate = document.getElementById("reportFromDate")?.value || "";
  const toDate = document.getElementById("reportToDate")?.value || "";

  const params = {};
  if (fromDate) params.from_date = fromDate;
  if (toDate) params.to_date = toDate;

  const res = await Api.get(`/api/reports/${reportType}`, params);

  const titleEl = document.getElementById("reportTitleDisplay");
  if (titleEl) titleEl.innerText = res.title;
  const rangeEl = document.getElementById("reportDateRangeDisplay");
  if (rangeEl) rangeEl.innerText = `${res.date_range.from || 'All Time'} to ${res.date_range.to || 'All Time'}`;
  const genEl = document.getElementById("reportGeneratedAt");
  if (genEl) genEl.innerText = res.generated_at;

  // Render Table Columns
  const thead = document.querySelector("#tableReport thead");
  if (thead) thead.innerHTML = `<tr>${res.columns.map(c => `<th>${c}</th>`).join("")}</tr>`;

  // Render Table Body
  const tbody = document.querySelector("#tableReport tbody");
  if (tbody) {
    tbody.innerHTML = res.data.map(row => {
      const values = Object.values(row);
      return `<tr>${values.map(v => `<td>${typeof v === 'number' ? Number(v).toLocaleString() : (v || '-')}</td>`).join("")}</tr>`;
    }).join("");
  }

  // Render Totals
  const totalsDiv = document.getElementById("reportTotalsDisplay");
  if (totalsDiv) {
    if (res.totals && Object.keys(res.totals).length > 0) {
      totalsDiv.innerHTML = Object.entries(res.totals).map(([k, v]) => `
        <div style="background: var(--bg-surface-elevated); padding: 0.75rem 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <span style="font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase;">${k.replace(/_/g, ' ')}</span>
          <div style="font-size: 1.3rem; font-weight: 800; color: var(--primary-400);">${typeof v === 'number' ? `₹${Number(v).toLocaleString()}` : v}</div>
        </div>
      `).join("");
    } else {
      totalsDiv.innerHTML = "";
    }
  }
}

// ----------------- VIEW 18: AUDIT LOGS ----------------- //
async function loadAuditLogs() {
  const data = await Api.get("/api/dashboard/recent-activities?limit=100");
  const tbody = document.querySelector("#tableAuditLogs tbody");
  if (!tbody) return;

  tbody.innerHTML = data.activities.map(a => `
    <tr>
      <td>${formatDateTime(a.timestamp)}</td>
      <td><strong>${a.username}</strong></td>
      <td><span class="badge info">${a.module}</span></td>
      <td><strong>${a.action}</strong></td>
      <td>${a.record_id || '-'}</td>
      <td>${a.details || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- VIEW 19: USER PROFILE ----------------- //
function loadProfile() {
  const user = Auth.getCurrentUser();
  if (!user) return;
  const nameEl = document.getElementById("profileFullName");
  if (nameEl) nameEl.innerText = user.full_name || user.username;
  const roleEl = document.getElementById("profileRole");
  if (roleEl) roleEl.innerText = "Owner / Administrator (Full System Control)";
  const userEl = document.getElementById("profileUsername");
  if (userEl) userEl.innerText = user.username;
}

// ----------------- EXPORT & PRINT ACTIONS ----------------- //
window.exportReportCSV = function() {
  const reportType = document.getElementById("reportTypeSelect")?.value || "complete";
  const fromDate = document.getElementById("reportFromDate")?.value || "";
  const toDate = document.getElementById("reportToDate")?.value || "";
  const url = `/api/reports/${reportType}?format=csv&from_date=${fromDate}&to_date=${toDate}&token=${Api.getToken()}`;
  window.open(url, "_blank");
};

window.printReport = function() {
  window.print();
};

window.navigateTo = navigateTo;
window.loadDashboard = loadDashboard;
window.loadPurchases = loadPurchases;

// ----------------- APP BOOTSTRAP ----------------- //
export async function initializeApp() {
  console.log("[RVKS] Bootstrapping modular architecture...");

  // 1. Service Worker Registration
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(err => {
      console.log("ServiceWorker registration skipped or failed:", err);
    });
  }

  // 2. Load Shell Components (Navbar, Sidebar, Footer, Modals, Toast)
  await loadShellComponents();

  // 3. Initialize Event Delegation for Modals, Nav items, Theme, and Sync
  initModalListeners();

  // 4. Bind Action Form Submit Handlers
  initForms(async () => {
    await loadViewData(State.currentView);
  });

  // 5. Saved Theme Preference
  const savedTheme = localStorage.getItem("rvks_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);

  // 6. Set Default Dates on Any Static Inputs
  const todayIso = new Date().toISOString().slice(0, 10);
  document.querySelectorAll("input[type='date']").forEach(input => {
    if (!input.value) input.value = todayIso;
  });

  // 7. Check Authentication State
  Auth.checkAuth(async (user) => {
    State.user = user;
    await populateDropdowns();
    await navigateTo("dashboard");
    // Pre-cache other view pages in background for instant responsiveness
    preloadAllViews().catch(e => console.warn("Preload views:", e));
  });
}

// Bootstrap on DOM load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp);
} else {
  initializeApp();
}
