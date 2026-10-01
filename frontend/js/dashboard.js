// RVKS WEB - Farm Operational Dashboard Controller
import { Api } from "./api.js";
import { renderDashboardCharts } from "./charts.js";
import { formatDateTime } from "./utils.js";

export async function loadDashboard() {
  const [summary, alertsData, chartsData, activitiesData] = await Promise.all([
    Api.get("/api/dashboard/summary"),
    Api.get("/api/dashboard/alerts"),
    Api.get("/api/dashboard/charts"),
    Api.get("/api/dashboard/recent-activities?limit=10")
  ]);

  // 1. Birds KPI
  setElemText("kpiTotalBirds", Number(summary.birds.total_birds).toLocaleString());
  setElemText("kpiChickBirds", Number(summary.birds.chick_birds).toLocaleString());
  setElemText("kpiLayerBirds", Number(summary.birds.layer_birds).toLocaleString());
  setElemText("kpiEddBirds", Number(summary.birds.edd_birds).toLocaleString());
  setElemText("kpiEddBatch1", Number(summary.birds.edd_batch_1).toLocaleString());
  setElemText("kpiEddBatch2", Number(summary.birds.edd_batch_2).toLocaleString());
  setElemText("kpiEddBatch3", Number(summary.birds.edd_batch_3).toLocaleString());

  // 2. Worker KPI
  setElemText("kpiTotalWorkers", summary.workers.total_workers);
  setElemText("kpiActiveWorkers", summary.workers.active_workers);
  setElemText("kpiPresentToday", summary.workers.present_today);
  setElemText("kpiAbsentToday", summary.workers.absent_today);
  setElemText("kpiLeaveToday", summary.workers.leave_today);
  setElemText("kpiPendingPayments", `₹${Number(summary.workers.pending_payments_amount).toLocaleString()}`);

  // 3. Feed KPI
  setElemText("kpiFeedStock", `${Number(summary.feed.current_feed_stock).toLocaleString()} kg`);
  setElemText("kpiTodayFeedUsage", `${Number(summary.feed.today_feed_usage).toLocaleString()} kg`);
  setElemText("kpiMonthFeedProd", `${Number(summary.feed.month_feed_production).toLocaleString()} kg`);

  // 4. Raw Materials KPI
  setElemText("kpiRawMaterialStock", `${Number(summary.raw_materials.current_stock).toLocaleString()} kg`);
  setElemText("kpiTodayPurchases", `${Number(summary.raw_materials.today_purchases_qty).toLocaleString()} kg`);
  setElemText("kpiMonthPurchaseCost", `₹${Number(summary.raw_materials.month_purchase_cost).toLocaleString()}`);

  // 5. Egg KPI
  setElemText("kpiTodayEggs", Number(summary.eggs.today_eggs).toLocaleString());
  setElemText("kpiWeekEggs", Number(summary.eggs.this_week_eggs).toLocaleString());
  setElemText("kpiMonthEggs", Number(summary.eggs.this_month_eggs).toLocaleString());
  setElemText("kpiMonthEggIncome", `₹${Number(summary.eggs.month_egg_income).toLocaleString()}`);

  // 6. Expense & Net KPI
  setElemText("kpiTodayExpenses", `₹${Number(summary.expenses.today_expenses).toLocaleString()}`);
  setElemText("kpiMonthExpenses", `₹${Number(summary.expenses.this_month_expenses).toLocaleString()}`);
  setElemText("kpiMonthWorkerPayments", `₹${Number(summary.expenses.worker_payments).toLocaleString()}`);
  setElemText("kpiMonthNetBalance", `₹${Number(summary.finances.net_balance).toLocaleString()}`);
  const netEl = document.getElementById("kpiMonthNetBalance");
  if (netEl) {
    netEl.style.color = summary.finances.net_balance >= 0 ? "var(--primary-400)" : "var(--danger-500)";
  }

  // 7. Render Alert Banners
  const alertContainer = document.getElementById("dashboardAlerts");
  if (alertContainer) {
    if (alertsData.alerts && alertsData.alerts.length > 0) {
      alertContainer.innerHTML = alertsData.alerts.map(a => {
        let iconHtml = 'ℹ️';
        if (a.type === 'danger') {
          iconHtml = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
        } else if (a.type === 'warning') {
          iconHtml = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
        }
        return `
          <div class="alert-banner ${a.type}">
            <div class="alert-icon">${iconHtml}</div>
            <div class="alert-content">
              <strong class="alert-title">${a.title}</strong>
              <div class="alert-desc">${a.message}</div>
            </div>
          </div>
        `;
      }).join("");
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

  return summary;
}

function setElemText(id, text) {
  const el = document.getElementById(id);
  if (el) el.innerText = text;
}
