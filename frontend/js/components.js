// RVKS WEB - Reusable Components Controller & Form Handlers
import { Api } from "./api.js";
import { OfflineSync } from "./offline_sync.js";
import { openModal, closeModal, showToast } from "./utils.js";

// View to Page mapping
export const VIEW_PAGE_MAP = {
  "dashboard": "/pages/dashboard.html",
  "workers": "/pages/workers.html",
  "attendance": "/pages/attendance.html",
  "payments": "/pages/payments.html",
  "batches": "/pages/batches.html",
  "birds": "/pages/batches.html",
  "mortality": "/pages/mortality.html",
  "eggs": "/pages/eggs.html",
  "suppliers": "/pages/suppliers.html",
  "raw-materials": "/pages/raw_materials.html",
  "purchases": "/pages/purchases.html",
  "feed-recipes": "/pages/feed_recipes.html",
  "feed-production": "/pages/feed_production.html",
  "feed-stock": "/pages/feed_stock.html",
  "feed-usage": "/pages/feed_usage.html",
  "expenses": "/pages/expenses.html",
  "income": "/pages/income.html",
  "reports": "/pages/reports.html",
  "audit": "/pages/audit.html",
  "profile": "/pages/profile.html",
  "settings": "/pages/profile.html",
  "inventory": "/pages/feed_stock.html"
};

/**
 * Loads an external HTML component file and injects it into a container element
 * @param {string} url - Path to HTML component file
 * @param {string} mountId - Target container element ID
 */
export async function loadComponent(url, mountId) {
  const mountEl = document.getElementById(mountId);
  if (!mountEl) return false;

  try {
    const res = await fetch(url);
    if (res.ok) {
      mountEl.innerHTML = await res.text();
      return true;
    }
  } catch (err) {
    console.warn(`[Components] Could not fetch ${url} directly: ${err.message}`);
  }
  return false;
}

/**
 * Loads the core shell components: Navbar, Sidebar, Footer, Modals, Toast
 */
export async function loadShellComponents() {
  await Promise.all([
    loadComponent("/components/navbar.html", "navbarMount"),
    loadComponent("/components/sidebar.html", "sidebarMount"),
    loadComponent("/components/footer.html", "footerMount"),
    loadComponent("/components/modals.html", "modalsMount"),
    loadComponent("/components/toast.html", "toastMount")
  ]);
}

/**
 * Ensures a view section from /pages/*.html is loaded into #appContent
 * @param {string} viewId - ID of view (e.g. 'dashboard', 'workers')
 */
export async function ensureViewLoaded(viewId) {
  const targetSectionId = `view-${viewId === 'birds' ? 'batches' : viewId}`;
  if (document.getElementById(targetSectionId)) {
    return true; // Already loaded in DOM
  }

  const pageUrl = VIEW_PAGE_MAP[viewId];
  if (!pageUrl) return false;

  try {
    const res = await fetch(pageUrl);
    if (res.ok) {
      const html = await res.text();
      const container = document.getElementById("appContent");
      if (container) {
        const temp = document.createElement("div");
        temp.innerHTML = html.trim();
        const section = temp.querySelector(".view-section") || temp.firstElementChild;
        if (section) {
          container.appendChild(section);
          return true;
        }
      }
    }
  } catch (err) {
    console.warn(`[Views] Failed to load ${pageUrl}:`, err);
  }
  return false;
}

/**
 * Pre-fetches and mounts all views into DOM for instant tab switching
 */
export async function preloadAllViews() {
  const viewKeys = Object.keys(VIEW_PAGE_MAP);
  await Promise.all(viewKeys.map(k => ensureViewLoaded(k)));
}

/**
 * Global Event Delegation for modal openers, closers, and navigation items
 */
export function initModalListeners() {
  document.addEventListener("click", (e) => {
    // Quick Action / Modal Open Button Click
    const openBtn = e.target.closest("[data-open-modal]");
    if (openBtn) {
      e.preventDefault();
      const modalId = openBtn.dataset.openModal;
      if (modalId) {
        populateDropdowns();
        openModal(modalId);
      }
      return;
    }

    // Modal Close Button Click
    const closeBtn = e.target.closest(".modal-close-btn, [data-close-modal]");
    if (closeBtn) {
      e.preventDefault();
      const backdrop = closeBtn.closest(".modal-backdrop");
      if (backdrop) backdrop.classList.remove("open");
      return;
    }

    // Backdrop Click outside Modal Dialog
    if (e.target.classList.contains("modal-backdrop")) {
      e.target.classList.remove("open");
      return;
    }

    // Sidebar navigation click
    const navItem = e.target.closest(".nav-item");
    if (navItem) {
      e.preventDefault();
      const view = navItem.dataset.view;
      if (view && window.navigateTo) {
        window.navigateTo(view);
      }
      return;
    }

    // Mobile Menu Toggle
    const mobileMenuBtn = e.target.closest("#mobileMenuBtn");
    if (mobileMenuBtn) {
      e.preventDefault();
      document.getElementById("appSidebar")?.classList.toggle("open");
      return;
    }

    // Theme Toggle
    const themeBtn = e.target.closest("#themeToggleBtn");
    if (themeBtn) {
      e.preventDefault();
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("rvks_theme", next);
      if (window.loadDashboard) {
        window.loadDashboard();
      }
      return;
    }

    // Offline Sync Button
    const syncBtn = e.target.closest("#syncIndicator");
    if (syncBtn) {
      e.preventDefault();
      OfflineSync.syncNow();
      return;
    }
  });
}

/**
 * Populates all select dropdowns across modal dialogs
 */
export async function populateDropdowns() {
  try {
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
  } catch (err) {
    console.warn("[Components] Error populating select dropdowns:", err);
  }
}

/**
 * Initializes all modal action form submissions
 * @param {Function} refreshCallback - Optional callback to refresh current view after form submission
 */
export function initForms(refreshCallback) {
  const onSubmitted = async () => {
    if (typeof refreshCallback === "function") {
      await refreshCallback();
    }
  };

  // 1. Record Mortality Form
  const formMortality = document.getElementById("formRecordMortality");
  if (formMortality && !formMortality.dataset.bound) {
    formMortality.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 2. Record Egg Production Form
  const formEggs = document.getElementById("formRecordEggs");
  if (formEggs && !formEggs.dataset.bound) {
    formEggs.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 3. Produce Feed Form
  const formProduceFeed = document.getElementById("formProduceFeed");
  if (formProduceFeed && !formProduceFeed.dataset.bound) {
    formProduceFeed.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        alert(err.message); // Show complete shortage breakdown clearly to user
      }
    });
  }

  // 4. Record Feed Usage Form
  const formFeedUsage = document.getElementById("formRecordFeedUsage");
  if (formFeedUsage && !formFeedUsage.dataset.bound) {
    formFeedUsage.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 5. Raw Material Purchase Form
  const formPurchase = document.getElementById("formRecordPurchase");
  if (formPurchase && !formPurchase.dataset.bound) {
    formPurchase.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 6. Record Worker Payment Form
  const formPayment = document.getElementById("formRecordPayment");
  if (formPayment && !formPayment.dataset.bound) {
    formPayment.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 7. Add Expense Form
  const formExpense = document.getElementById("formAddExpense");
  if (formExpense && !formExpense.dataset.bound) {
    formExpense.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 8. Add Worker Form
  const formAddWorker = document.getElementById("formAddWorker");
  if (formAddWorker && !formAddWorker.dataset.bound) {
    formAddWorker.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 8b. Edit Worker Form
  const formEditWorker = document.getElementById("formEditWorker");
  if (formEditWorker && !formEditWorker.dataset.bound) {
    formEditWorker.dataset.bound = "true";
    formEditWorker.addEventListener("submit", async (e) => {
      e.preventDefault();
      const workerId = document.getElementById("editWorkerId").value;
      const payload = {
        name: document.getElementById("editWorkerName").value,
        job_role: document.getElementById("editWorkerRole").value,
        phone: document.getElementById("editWorkerPhone").value,
        address: document.getElementById("editWorkerAddress").value,
        date_of_joining: document.getElementById("editWorkerDoj").value,
        salary_type: document.getElementById("editWorkerSalaryType").value,
        salary_amount: parseFloat(document.getElementById("editWorkerSalaryAmount").value || 0),
        payment_status: document.getElementById("editWorkerPaymentStatus").value,
        payment_date: document.getElementById("editWorkerPaymentDate").value || null,
        payment_method: document.getElementById("editWorkerPayMethod").value,
        status: document.getElementById("editWorkerStatus").value,
        notes: document.getElementById("editWorkerNotes").value
      };

      try {
        const res = await Api.put(`/api/workers/${workerId}`, payload);
        showToast(res.message);
        closeModal("modalEditWorker");
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 9. Add Bird Batch Form
  const formAddBatch = document.getElementById("formAddBatch");
  if (formAddBatch && !formAddBatch.dataset.bound) {
    formAddBatch.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // 10. Add Supplier Form
  const formAddSupplier = document.getElementById("formAddSupplier");
  if (formAddSupplier && !formAddSupplier.dataset.bound) {
    formAddSupplier.dataset.bound = "true";
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
        await onSubmitted();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }
}

// Global binding
window.populateDropdowns = populateDropdowns;
