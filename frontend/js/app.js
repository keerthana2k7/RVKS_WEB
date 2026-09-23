// RVKS WEB — Poultry Farm Management System Master Controller
import { Api } from "./api.js";
import { OfflineSync } from "./offline_sync.js";
import { renderDashboardCharts } from "./charts.js";

// Global State
const State = {
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

// Toast Notifications
export function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === "success" ? "✓" : type === "error" ? "⚠" : "ℹ"}</span>
    <div class="toast-msg">${message}</div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Dialog / Modal Helpers
export function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("open");
  }
}

export function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("open");
  }
}

// Router & View Switcher
export function navigateTo(viewId) {
  State.currentView = viewId;

  // Update nav items
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.dataset.view === viewId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Hide all view sections
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.style.display = "none";
  });

  // Show target section
  const targetSec = document.getElementById(`view-${viewId}`);
  if (targetSec) {
    targetSec.style.display = "block";
  }

  // Close mobile sidebar if open
  const sidebar = document.getElementById("appSidebar");
  if (sidebar && sidebar.classList.contains("open")) {
    sidebar.classList.remove("open");
  }

  // Load view data
  loadViewData(viewId);
}

// Data Loader Dispatcher
async function loadViewData(viewId) {
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
    }
  } catch (error) {
    console.error(`Error loading view ${viewId}:`, error);
    showToast(`Error: ${error.message}`, "error");
  }
}

// ----------------- DASHBOARD VIEW ----------------- //
async function loadDashboard() {
  const [summary, alertsData, chartsData, activitiesData] = await Promise.all([
    Api.get("/api/dashboard/summary"),
    Api.get("/api/dashboard/alerts"),
    Api.get("/api/dashboard/charts"),
    Api.get("/api/dashboard/recent-activities?limit=10")
  ]);

  State.dashboardData = summary;

  // 1. Birds KPI
  document.getElementById("kpiTotalBirds").innerText = Number(summary.birds.total_birds).toLocaleString();
  document.getElementById("kpiChickBirds").innerText = Number(summary.birds.chick_birds).toLocaleString();
  document.getElementById("kpiLayerBirds").innerText = Number(summary.birds.layer_birds).toLocaleString();
  document.getElementById("kpiEddBirds").innerText = Number(summary.birds.edd_birds).toLocaleString();
  document.getElementById("kpiEddBatch1").innerText = Number(summary.birds.edd_batch_1).toLocaleString();
  document.getElementById("kpiEddBatch2").innerText = Number(summary.birds.edd_batch_2).toLocaleString();
  document.getElementById("kpiEddBatch3").innerText = Number(summary.birds.edd_batch_3).toLocaleString();

  // 2. Worker KPI
  document.getElementById("kpiTotalWorkers").innerText = summary.workers.total_workers;
  document.getElementById("kpiActiveWorkers").innerText = summary.workers.active_workers;
  document.getElementById("kpiPresentToday").innerText = summary.workers.present_today;
  document.getElementById("kpiAbsentToday").innerText = summary.workers.absent_today;
  document.getElementById("kpiLeaveToday").innerText = summary.workers.leave_today;
  document.getElementById("kpiPendingPayments").innerText = `₹${Number(summary.workers.pending_payments_amount).toLocaleString()}`;

  // 3. Feed KPI
  document.getElementById("kpiFeedStock").innerText = `${Number(summary.feed.current_feed_stock).toLocaleString()} kg`;
  document.getElementById("kpiTodayFeedUsage").innerText = `${Number(summary.feed.today_feed_usage).toLocaleString()} kg`;
  document.getElementById("kpiMonthFeedProd").innerText = `${Number(summary.feed.month_feed_production).toLocaleString()} kg`;

  // 4. Raw Materials KPI
  document.getElementById("kpiRawMaterialStock").innerText = `${Number(summary.raw_materials.current_stock).toLocaleString()} kg`;
  document.getElementById("kpiTodayPurchases").innerText = `${Number(summary.raw_materials.today_purchases_qty).toLocaleString()} kg`;
  document.getElementById("kpiMonthPurchaseCost").innerText = `₹${Number(summary.raw_materials.month_purchase_cost).toLocaleString()}`;

  // 5. Egg KPI
  document.getElementById("kpiTodayEggs").innerText = Number(summary.eggs.today_eggs).toLocaleString();
  document.getElementById("kpiWeekEggs").innerText = Number(summary.eggs.this_week_eggs).toLocaleString();
  document.getElementById("kpiMonthEggs").innerText = Number(summary.eggs.this_month_eggs).toLocaleString();
  document.getElementById("kpiMonthEggIncome").innerText = `₹${Number(summary.eggs.month_egg_income).toLocaleString()}`;

  // 6. Expense & Net KPI
  document.getElementById("kpiTodayExpenses").innerText = `₹${Number(summary.expenses.today_expenses).toLocaleString()}`;
  document.getElementById("kpiMonthExpenses").innerText = `₹${Number(summary.expenses.this_month_expenses).toLocaleString()}`;
  document.getElementById("kpiMonthWorkerPayments").innerText = `₹${Number(summary.expenses.worker_payments).toLocaleString()}`;
  document.getElementById("kpiMonthNetBalance").innerText = `₹${Number(summary.finances.net_balance).toLocaleString()}`;
  const netEl = document.getElementById("kpiMonthNetBalance");
  if (summary.finances.net_balance >= 0) {
    netEl.style.color = "var(--primary-400)";
  } else {
    netEl.style.color = "var(--danger-500)";
  }

  // 7. Render Alert Banners
  const alertContainer = document.getElementById("dashboardAlerts");
  if (alertContainer) {
    if (alertsData.alerts && alertsData.alerts.length > 0) {
      alertContainer.innerHTML = alertsData.alerts.map(a => `
        <div class="alert-banner ${a.type}">
          <div class="alert-icon">${a.type === 'danger' ? '🚨' : a.type === 'warning' ? '⚠️' : 'ℹ️'}</div>
          <div class="alert-content">
            <strong>${a.title}</strong>
            ${a.message}
          </div>
        </div>
      `).join("");
    } else {
      alertContainer.innerHTML = "";
    }
  }

  // 8. Recent Activities Feed
  const actContainer = document.getElementById("recentActivitiesList");
  if (actContainer && activitiesData.activities) {
    actContainer.innerHTML = activitiesData.activities.map(act => `
      <div style="padding: 0.75rem 0; border-bottom: 1px solid var(--border-light); display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;">
        <div>
          <strong style="color: var(--primary-300); font-size: 0.9rem;">${act.action}</strong>
          <span style="font-size: 0.75rem; color: var(--text-dim); margin-left: 0.5rem;">[${act.module}]</span>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.15rem;">${act.details || ''}</p>
        </div>
        <span style="font-size: 0.75rem; color: var(--text-dim); white-space: nowrap;">${formatDateTime(act.timestamp)}</span>
      </div>
    `).join("");
  }

  // 9. Charts
  renderDashboardCharts(chartsData);
}

// ----------------- WORKERS VIEW ----------------- //
async function loadWorkers() {
  const data = await Api.get("/api/workers");
  State.cachedDropdowns.workers = data.workers;

  const tbody = document.querySelector("#tableWorkers tbody");
  if (!tbody) return;

  tbody.innerHTML = data.workers.map(w => `
    <tr>
      <td><strong>${w.worker_code}</strong></td>
      <td><strong>${w.name}</strong></td>
      <td>${w.job_role}</td>
      <td>${w.phone || '-'}</td>
      <td>${w.salary_type} (₹${Number(w.salary_amount).toLocaleString()})</td>
      <td>${w.payment_method}</td>
      <td>
        <span class="badge ${w.status === 'Active' ? 'success' : 'danger'}">${w.status}</span>
      </td>
      <td>
        ${State.user?.role === 'owner_admin' ? `
          <button class="btn btn-secondary btn-sm" onclick="window.toggleWorkerStatus(${w.id}, '${w.status === 'Active' ? 'Inactive' : 'Active'}')">
            ${w.status === 'Active' ? 'Deactivate' : 'Activate'}
          </button>
        ` : '-'}
      </td>
    </tr>
  `).join("");
}

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

// ----------------- ATTENDANCE VIEW ----------------- //
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
        <div style="display: flex; gap: 0.5rem;">
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

// ----------------- WORKER PAYMENTS VIEW ----------------- //
async function loadPayments() {
  const data = await Api.get("/api/workers/payments");
  const tbody = document.querySelector("#tablePayments tbody");
  if (!tbody) return;

  document.getElementById("paymentsTotalPaid").innerText = `₹${Number(data.summary.total_paid).toLocaleString()}`;
  document.getElementById("paymentsTotalPending").innerText = `₹${Number(data.summary.total_pending).toLocaleString()}`;
  document.getElementById("paymentsLastDate").innerText = data.summary.last_payment_date ? formatDate(data.summary.last_payment_date) : '-';

  tbody.innerHTML = data.payments.map(p => `
    <tr>
      <td><strong>${p.payment_code}</strong></td>
      <td><strong>${p.worker_name}</strong> (${p.worker_code})</td>
      <td>${p.salary_period}</td>
      <td>${formatDate(p.payment_date)}</td>
      <td><strong>₹${Number(p.amount).toLocaleString()}</strong></td>
      <td>${p.payment_method}</td>
      <td><span class="badge ${p.status === 'Paid' ? 'success' : p.status === 'Pending' ? 'warning' : 'info'}">${p.status}</span></td>
      <td>${p.notes || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- BIRDS & BATCHES VIEW ----------------- //
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

// ----------------- MORTALITY VIEW ----------------- //
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

// ----------------- EGG PRODUCTION VIEW ----------------- //
async function loadEggs() {
  const [recordsData, statsData] = await Promise.all([
    Api.get("/api/eggs"),
    Api.get("/api/eggs/stats")
  ]);

  document.getElementById("eggTodayCount").innerText = Number(statsData.today.total).toLocaleString();
  document.getElementById("eggWeekCount").innerText = Number(statsData.week.total).toLocaleString();
  document.getElementById("eggMonthCount").innerText = Number(statsData.month.total).toLocaleString();
  document.getElementById("eggMonthIncome").innerText = `₹${Number(statsData.month.income).toLocaleString()}`;

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

// ----------------- SUPPLIERS VIEW ----------------- //
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
    matDiv.innerHTML = data.materials_breakdown.map(m => `
      <div style="background: var(--bg-surface-elevated); padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        <strong style="color: var(--primary-300);">${m.material_name}</strong>: 
        <span>${Number(m.total_qty).toLocaleString()} ${m.unit}</span> (₹${Number(m.total_spent).toLocaleString()})
      </div>
    `).join("");

    // Purchases table
    const tbody = document.querySelector("#tableSupplierPurchases tbody");
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

    openModal("modalSupplierHistory");
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ----------------- RAW MATERIALS VIEW ----------------- //
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

// ----------------- PURCHASES VIEW ----------------- //
async function loadPurchases() {
  const data = await Api.get("/api/raw-materials/purchases");
  const tbody = document.querySelector("#tablePurchases tbody");
  if (!tbody) return;

  tbody.innerHTML = data.purchases.map(p => `
    <tr>
      <td><strong>${p.purchase_code}</strong></td>
      <td>${formatDate(p.purchase_date)}</td>
      <td><strong>${p.supplier_name}</strong></td>
      <td>${p.material_name}</td>
      <td>${Number(p.quantity).toLocaleString()} ${p.unit}</td>
      <td>₹${p.rate_per_unit}</td>
      <td>₹${Number(p.material_cost).toLocaleString()}</td>
      <td>₹${Number(p.transport_cost).toLocaleString()}</td>
      <td><strong style="color: var(--primary-400); font-size: 1.05rem;">₹${Number(p.total_cost).toLocaleString()}</strong></td>
      <td><span class="badge ${p.payment_status === 'Paid' ? 'success' : 'warning'}">${p.payment_status}</span></td>
      <td>${p.invoice_number || '-'}</td>
    </tr>
  `).join("");
}

// ----------------- FEED RECIPES VIEW ----------------- //
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
  document.getElementById("feedProdRecipeSelect").value = recipeId;
  document.getElementById("feedProdTypeSelect").value = feedType;
  openModal("modalProduceFeed");
};

// ----------------- FEED PRODUCTION VIEW ----------------- //
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

// ----------------- FEED STOCK VIEW ----------------- //
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

// ----------------- FEED USAGE VIEW ----------------- //
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

// ----------------- EXPENSES VIEW ----------------- //
async function loadExpenses() {
  const data = await Api.get("/api/finance/expenses");
  const tbody = document.querySelector("#tableExpenses tbody");
  if (!tbody) return;

  document.getElementById("expensesTotalAmount").innerText = `₹${Number(data.total).toLocaleString()}`;

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

// ----------------- INCOME VIEW ----------------- //
async function loadIncome() {
  const data = await Api.get("/api/finance/income");
  const tbody = document.querySelector("#tableIncome tbody");
  if (!tbody) return;

  document.getElementById("incomeTotalAmount").innerText = `₹${Number(data.total).toLocaleString()}`;

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

// ----------------- REPORTS VIEW ----------------- //
async function loadReportsView() {
  const reportType = document.getElementById("reportTypeSelect")?.value || "complete";
  const fromDate = document.getElementById("reportFromDate")?.value || "";
  const toDate = document.getElementById("reportToDate")?.value || "";

  const params = {};
  if (fromDate) params.from_date = fromDate;
  if (toDate) params.to_date = toDate;

  const res = await Api.get(`/api/reports/${reportType}`, params);

  document.getElementById("reportTitleDisplay").innerText = res.title;
  document.getElementById("reportDateRangeDisplay").innerText = `${res.date_range.from || 'All Time'} to ${res.date_range.to || 'All Time'}`;
  document.getElementById("reportGeneratedAt").innerText = res.generated_at;

  // Render Table Columns
  const thead = document.querySelector("#tableReport thead");
  thead.innerHTML = `<tr>${res.columns.map(c => `<th>${c}</th>`).join("")}</tr>`;

  // Render Table Body
  const tbody = document.querySelector("#tableReport tbody");
  tbody.innerHTML = res.data.map(row => {
    const values = Object.values(row);
    return `<tr>${values.map(v => `<td>${typeof v === 'number' ? Number(v).toLocaleString() : (v || '-')}</td>`).join("")}</tr>`;
  }).join("");

  // Render Totals
  const totalsDiv = document.getElementById("reportTotalsDisplay");
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

// ----------------- AUDIT LOGS VIEW ----------------- //
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

// ----------------- MODAL FORMS INITIALIZATION & SUBMIT ----------------- //

export function initForms() {
  // 1. Record Mortality Form
  const formMortality = document.getElementById("formRecordMortality");
  if (formMortality) {
    formMortality.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        date: document.getElementById("mortDate").value,
        batch_id: parseInt(document.getElementById("mortBatchSelect").value),
        number_of_birds: parseInt(document.getElementById("mortBirdCount").value),
        reason: document.getElementById("mortReasonSelect").value,
        notes: document.getElementById("mortNotes").value
      };

      try {
        if (!navigator.onLine) {
          await OfflineSync.enqueue("mortality", payload);
          showToast("Saved offline as Pending Sync.", "info");
        } else {
          const res = await Api.post("/api/birds/mortality", payload);
          showToast(res.message);
          if (res.high_mortality_alert) {
            showToast("ALERT: High mortality recorded today in this batch!", "error");
          }
        }
        closeModal("modalRecordMortality");
        formMortality.reset();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 2. Record Egg Production Form
  const formEggs = document.getElementById("formRecordEggs");
  if (formEggs) {
    formEggs.addEventListener("submit", async (e) => {
      e.preventDefault();
      const tot = parseInt(document.getElementById("eggTotal").value);
      const broken = parseInt(document.getElementById("eggBroken").value || 0);
      const damaged = parseInt(document.getElementById("eggDamaged").value || 0);
      const sold = parseInt(document.getElementById("eggSold").value || 0);
      const price = parseFloat(document.getElementById("eggPrice").value || 5.50);

      const payload = {
        date: document.getElementById("eggDate").value,
        batch_id: parseInt(document.getElementById("eggBatchSelect").value),
        total_eggs: tot,
        good_eggs: tot - (broken + damaged),
        broken_eggs: broken,
        damaged_eggs: damaged,
        sold_eggs: sold,
        selling_price: price,
        notes: document.getElementById("eggNotes").value
      };

      try {
        if (!navigator.onLine) {
          await OfflineSync.enqueue("egg_production", payload);
          showToast("Saved offline as Pending Sync.", "info");
        } else {
          const res = await Api.post("/api/eggs", payload);
          showToast(res.message);
        }
        closeModal("modalRecordEggs");
        formEggs.reset();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 3. Produce Feed Form
  const formProduceFeed = document.getElementById("formProduceFeed");
  if (formProduceFeed) {
    formProduceFeed.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        date: document.getElementById("feedProdDate").value,
        feed_type: document.getElementById("feedProdTypeSelect").value,
        recipe_id: parseInt(document.getElementById("feedProdRecipeSelect").value),
        quantity_produced: parseFloat(document.getElementById("feedProdQty").value),
        labour_cost: parseFloat(document.getElementById("feedProdLabour").value || 0),
        electricity_cost: parseFloat(document.getElementById("feedProdElectricity").value || 0),
        notes: document.getElementById("feedProdNotes").value
      };

      try {
        const res = await Api.post("/api/feed/produce", payload);
        showToast(res.message);
        closeModal("modalProduceFeed");
        formProduceFeed.reset();
        await loadDashboard();
      } catch (err) {
        alert(err.message); // Show complete shortage breakdown clearly to user
      }
    });
  }

  // 4. Record Feed Usage Form
  const formFeedUsage = document.getElementById("formRecordFeedUsage");
  if (formFeedUsage) {
    formFeedUsage.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        date: document.getElementById("feedUsageDate").value,
        batch_id: parseInt(document.getElementById("feedUsageBatchSelect").value),
        feed_type: document.getElementById("feedUsageTypeSelect").value,
        quantity: parseFloat(document.getElementById("feedUsageQty").value),
        notes: document.getElementById("feedUsageNotes").value
      };

      try {
        if (!navigator.onLine) {
          await OfflineSync.enqueue("feed_usage", payload);
          showToast("Saved offline as Pending Sync.", "info");
        } else {
          const res = await Api.post("/api/feed/usage", payload);
          showToast(res.message);
        }
        closeModal("modalRecordFeedUsage");
        formFeedUsage.reset();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 5. Raw Material Purchase Form
  const formPurchase = document.getElementById("formRecordPurchase");
  if (formPurchase) {
    formPurchase.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        purchase_date: document.getElementById("purDate").value,
        supplier_id: parseInt(document.getElementById("purSupplierSelect").value),
        material_id: parseInt(document.getElementById("purMaterialSelect").value),
        quantity: parseFloat(document.getElementById("purQty").value),
        rate_per_unit: parseFloat(document.getElementById("purRate").value),
        transport_cost: parseFloat(document.getElementById("purTransport").value || 0),
        other_cost: parseFloat(document.getElementById("purOther").value || 0),
        payment_status: document.getElementById("purStatusSelect").value,
        invoice_number: document.getElementById("purInvoice").value,
        notes: document.getElementById("purNotes").value
      };

      try {
        const res = await Api.post("/api/raw-materials/purchases", payload);
        showToast(res.message);
        closeModal("modalRecordPurchase");
        formPurchase.reset();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 6. Record Worker Payment Form
  const formPayment = document.getElementById("formRecordPayment");
  if (formPayment) {
    formPayment.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        worker_id: parseInt(document.getElementById("payWorkerSelect").value),
        salary_period: document.getElementById("payPeriod").value,
        payment_date: document.getElementById("payDate").value,
        amount: parseFloat(document.getElementById("payAmount").value),
        payment_method: document.getElementById("payMethodSelect").value,
        status: document.getElementById("payStatusSelect").value,
        notes: document.getElementById("payNotes").value
      };

      try {
        const res = await Api.post("/api/workers/payments", payload);
        showToast(res.message);
        closeModal("modalRecordPayment");
        formPayment.reset();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 7. Add Expense Form
  const formExpense = document.getElementById("formAddExpense");
  if (formExpense) {
    formExpense.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        date: document.getElementById("expDate").value,
        category: document.getElementById("expCategorySelect").value,
        description: document.getElementById("expDescription").value,
        amount: parseFloat(document.getElementById("expAmount").value),
        payment_method: document.getElementById("expMethodSelect").value,
        paid_by: document.getElementById("expPaidBy").value,
        notes: document.getElementById("expNotes").value
      };

      try {
        const res = await Api.post("/api/finance/expenses", payload);
        showToast(res.message);
        closeModal("modalAddExpense");
        formExpense.reset();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 8. Add Worker Form
  const formAddWorker = document.getElementById("formAddWorker");
  if (formAddWorker) {
    formAddWorker.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById("workerName").value,
        job_role: document.getElementById("workerRole").value,
        phone: document.getElementById("workerPhone").value,
        address: document.getElementById("workerAddress").value,
        date_of_joining: document.getElementById("workerDoj").value,
        salary_type: document.getElementById("workerSalaryType").value,
        salary_amount: parseFloat(document.getElementById("workerSalaryAmount").value || 0),
        payment_method: document.getElementById("workerPayMethod").value,
        notes: document.getElementById("workerNotes").value
      };

      try {
        const res = await Api.post("/api/workers", payload);
        showToast(res.message);
        closeModal("modalAddWorker");
        formAddWorker.reset();
        await loadWorkers();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 9. Add Bird Batch Form
  const formAddBatch = document.getElementById("formAddBatch");
  if (formAddBatch) {
    formAddBatch.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        batch_name: document.getElementById("batchName").value,
        bird_type: document.getElementById("batchBirdType").value,
        arrival_date: document.getElementById("batchDate").value,
        initial_quantity: parseInt(document.getElementById("batchQty").value),
        source_supplier: document.getElementById("batchSupplier").value,
        shed_location: document.getElementById("batchShed").value,
        age_weeks: parseInt(document.getElementById("batchAge").value || 0),
        notes: document.getElementById("batchNotes").value
      };

      try {
        const res = await Api.post("/api/birds/batches", payload);
        showToast(res.message);
        closeModal("modalAddBatch");
        formAddBatch.reset();
        await loadDashboard();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 10. Add Supplier Form
  const formAddSupplier = document.getElementById("formAddSupplier");
  if (formAddSupplier) {
    formAddSupplier.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        supplier_name: document.getElementById("supName").value,
        phone: document.getElementById("supPhone").value,
        address: document.getElementById("supAddress").value,
        materials_supplied: document.getElementById("supMaterials").value,
        notes: document.getElementById("supNotes").value
      };

      try {
        const res = await Api.post("/api/raw-materials/suppliers", payload);
        showToast(res.message);
        closeModal("modalAddSupplier");
        formAddSupplier.reset();
        await loadSuppliers();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
}

// ----------------- POPULATE MODAL DROPDOWNS ----------------- //
export async function populateDropdowns() {
  const [batchesRes, workersRes, suppliersRes, materialsRes, recipesRes] = await Promise.all([
    Api.get("/api/birds/batches?status=Active"),
    Api.get("/api/workers?status=Active"),
    Api.get("/api/raw-materials/suppliers"),
    Api.get("/api/raw-materials"),
    Api.get("/api/feed/recipes")
  ]);

  // Batch Dropdowns
  const batchSelects = [
    document.getElementById("mortBatchSelect"),
    document.getElementById("eggBatchSelect"),
    document.getElementById("feedUsageBatchSelect")
  ];
  batchSelects.forEach(sel => {
    if (!sel) return;
    sel.innerHTML = batchesRes.batches.map(b => `
      <option value="${b.id}">${b.batch_name} (${b.bird_type} - ${b.current_quantity} birds)</option>
    `).join("");
  });

  // Worker Dropdowns
  const workerSelects = [document.getElementById("payWorkerSelect")];
  workerSelects.forEach(sel => {
    if (!sel) return;
    sel.innerHTML = workersRes.workers.map(w => `
      <option value="${w.id}">${w.name} (${w.worker_code} - ${w.job_role})</option>
    `).join("");
  });

  // Supplier Dropdowns
  const supSelects = [document.getElementById("purSupplierSelect")];
  supSelects.forEach(sel => {
    if (!sel) return;
    sel.innerHTML = suppliersRes.suppliers.map(s => `
      <option value="${s.id}">${s.supplier_name} (${s.supplier_code})</option>
    `).join("");
  });

  // Material Dropdowns
  const matSelects = [document.getElementById("purMaterialSelect")];
  matSelects.forEach(sel => {
    if (!sel) return;
    sel.innerHTML = materialsRes.materials.map(m => `
      <option value="${m.id}">${m.material_name} (Stock: ${m.current_stock} ${m.unit})</option>
    `).join("");
  });

  // Recipe Dropdowns
  const recipeSelects = [document.getElementById("feedProdRecipeSelect")];
  recipeSelects.forEach(sel => {
    if (!sel) return;
    sel.innerHTML = recipesRes.recipes.map(r => `
      <option value="${r.id}">${r.recipe_name} (${r.feed_type})</option>
    `).join("");
  });
}

// ----------------- EXPORT ACTIONS ----------------- //
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

// ----------------- DATE & FORMATTING HELPERS ----------------- //
function formatDate(dateStr) {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${day}-${month}-${year}`; // DD-MM-YYYY format
}

function formatDateTime(dtStr) {
  if (!dtStr) return "-";
  const d = new Date(dtStr);
  if (isNaN(d.getTime())) return dtStr;
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  return `${day}-${month}-${year} ${hours}:${mins}`;
}

// ----------------- LOGIN / LOGOUT ----------------- //
window.handleLogin = async function(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const usernameInput = document.getElementById("loginUsername");
  const passwordInput = document.getElementById("loginPassword");
  const username = usernameInput ? usernameInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";

  if (!username || !password) {
    showToast("Please enter username and password", "error");
    return false;
  }

  const submitBtn = document.getElementById("btnLoginSubmit") || document.querySelector("#formLogin button[type='submit']");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = "Signing in...";
  }

  try {
    const res = await Api.post("/api/auth/login", { username, password });
    Api.setToken(res.token);
    Api.setUser(res.user);
    showToast("Welcome to RVKS WEB Poultry Management System!");
    checkAuth();
  } catch (err) {
    console.error("[RVKS] Login error:", err);
    showToast(err.message || "Login failed. Check server or credentials.", "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = "Sign In to Farm Dashboard";
    }
  }
  return false;
};

export function checkAuth() {
  const user = Api.getUser();
  if (user && Api.isLoggedIn()) {
    State.user = user;
    const userNameEl = document.getElementById("currentUserName");
    if (userNameEl) userNameEl.innerText = user.full_name || user.username;
    
    const userRoleEl = document.getElementById("currentUserRole");
    if (userRoleEl) userRoleEl.innerText = user.role === "owner_admin" ? "Owner" : "Worker";

    const loginView = document.getElementById("loginView");
    if (loginView) loginView.style.display = "none";

    const appView = document.getElementById("appView");
    if (appView) appView.style.display = "flex";

    // Role-based visibility
    if (user.role !== "owner_admin") {
      document.querySelectorAll(".admin-only").forEach(el => el.style.display = "none");
    } else {
      document.querySelectorAll(".admin-only").forEach(el => el.style.display = "");
    }

    try {
      populateDropdowns();
    } catch (err) {
      console.warn("[RVKS] Error populating dropdowns:", err);
    }
    navigateTo("dashboard");
  } else {
    const loginView = document.getElementById("loginView");
    if (loginView) loginView.style.display = "flex";

    const appView = document.getElementById("appView");
    if (appView) appView.style.display = "none";
  }
}

window.logout = function() {
  Api.clearAuth();
  checkAuth();
};

// ----------------- INITIALIZE APP ON DOM READY ----------------- //
function initializeApp() {
  console.log("[RVKS] Initializing application...");

  // Check Service Worker registration
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(err => {
      console.log("ServiceWorker registration skipped or failed:", err);
    });
  }

  // Theme Toggle
  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("rvks_theme", next);
      if (State.currentView === "dashboard" && State.dashboardData) {
        loadDashboard(); // Redraw charts with theme colors
      }
    });
  }
  const savedTheme = localStorage.getItem("rvks_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);

  // Sync button click
  const syncBtn = document.getElementById("syncIndicator");
  if (syncBtn) {
    syncBtn.addEventListener("click", () => {
      OfflineSync.syncNow();
    });
  }

  // Sidebar navigation click
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const view = item.dataset.view;
      if (view) navigateTo(view);
    });
  });

  // Mobile Menu Toggle
  const menuBtn = document.getElementById("mobileMenuBtn");
  if (menuBtn) {
    menuBtn.addEventListener("click", () => {
      document.getElementById("appSidebar")?.classList.toggle("open");
    });
  }

  // Quick Action Buttons
  document.querySelectorAll("[data-open-modal]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modalId = btn.dataset.openModal;
      if (modalId) {
        populateDropdowns();
        openModal(modalId);
      }
    });
  });

  // Modal Close Buttons & Backdrop click
  document.querySelectorAll(".modal-close-btn, [data-close-modal]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const backdrop = btn.closest(".modal-backdrop");
      if (backdrop) backdrop.classList.remove("open");
    });
  });

  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove("open");
      }
    });
  });

  // Bind Login Form
  const formLogin = document.getElementById("formLogin");
  if (formLogin) {
    formLogin.onsubmit = window.handleLogin;
  }
  const btnLoginSubmit = document.getElementById("btnLoginSubmit");
  if (btnLoginSubmit) {
    btnLoginSubmit.onclick = window.handleLogin;
  }

  // Auto set default dates on inputs
  const todayIso = new Date().toISOString().slice(0, 10);
  document.querySelectorAll("input[type='date']").forEach(input => {
    if (!input.value) input.value = todayIso;
  });

  // Initialize all form submit handlers
  initForms();

  // Check Auth & Start
  checkAuth();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp);
} else {
  initializeApp();
}
