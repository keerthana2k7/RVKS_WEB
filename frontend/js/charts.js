// RVKS WEB: Chart.js Dashboard Visualizations

let chartInstances = {};

export function destroyCharts() {
  Object.values(chartInstances).forEach(chart => {
    if (chart && typeof chart.destroy === "function") {
      chart.destroy();
    }
  });
  chartInstances = {};
}

export function renderDashboardCharts(data) {
  if (typeof Chart === "undefined") {
    console.warn("[Charts] Chart.js library not loaded yet.");
    return;
  }

  destroyCharts();

  const isDarkMode = document.documentElement.getAttribute("data-theme") !== "light";
  const textColor = isDarkMode ? "#94a3b8" : "#475569";
  const gridColor = isDarkMode ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.06)";

  Chart.defaults.color = textColor;
  Chart.defaults.font.family = "'Inter', sans-serif";

  // 1. Birds by Type (Doughnut)
  const birdsTypeCtx = document.getElementById("chartBirdsByType");
  if (birdsTypeCtx && data.birds_by_type) {
    chartInstances["birdsByType"] = new Chart(birdsTypeCtx, {
      type: "doughnut",
      data: {
        labels: data.birds_by_type.map(b => b.bird_type),
        datasets: [{
          data: data.birds_by_type.map(b => b.count),
          backgroundColor: ["#10b981", "#f59e0b", "#3b82f6", "#8b5cf6"],
          borderColor: isDarkMode ? "#111a24" : "#ffffff",
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" }
        }
      }
    });
  }

  // 2. Birds by Batch (Bar)
  const birdsBatchCtx = document.getElementById("chartBirdsByBatch");
  if (birdsBatchCtx && data.birds_by_batch) {
    chartInstances["birdsByBatch"] = new Chart(birdsBatchCtx, {
      type: "bar",
      data: {
        labels: data.birds_by_batch.map(b => b.batch_name),
        datasets: [{
          label: "Active Birds",
          data: data.birds_by_batch.map(b => b.current_quantity),
          backgroundColor: "#10b981",
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: gridColor }, beginAtZero: true }
        }
      }
    });
  }

  // 3. Mortality Trend (Line)
  const mortCtx = document.getElementById("chartMortalityTrend");
  if (mortCtx && data.mortality_trend) {
    chartInstances["mortalityTrend"] = new Chart(mortCtx, {
      type: "line",
      data: {
        labels: data.mortality_trend.map(m => m.date.slice(5)), // MM-DD
        datasets: [{
          label: "Bird Mortality",
          data: data.mortality_trend.map(m => m.count),
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.15)",
          fill: true,
          tension: 0.35,
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "top" } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: gridColor }, beginAtZero: true }
        }
      }
    });
  }

  // 4. Egg Production Trend (Line)
  const eggCtx = document.getElementById("chartEggTrend");
  if (eggCtx && data.egg_trend) {
    chartInstances["eggTrend"] = new Chart(eggCtx, {
      type: "line",
      data: {
        labels: data.egg_trend.map(e => e.date.slice(5)),
        datasets: [
          {
            label: "Good Eggs Collected",
            data: data.egg_trend.map(e => e.good),
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            fill: true,
            tension: 0.35,
          },
          {
            label: "Eggs Sold",
            data: data.egg_trend.map(e => e.sold),
            borderColor: "#f59e0b",
            borderDash: [5, 5],
            tension: 0.35,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "top" } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: gridColor }, beginAtZero: true }
        }
      }
    });
  }

  // 5. Feed Production vs Consumption (Bar)
  const feedCtx = document.getElementById("chartFeedComparison");
  if (feedCtx && data.feed_comparison) {
    chartInstances["feedComparison"] = new Chart(feedCtx, {
      type: "bar",
      data: {
        labels: data.feed_comparison.map(f => f.date.slice(5)),
        datasets: [
          {
            label: "Produced (Kg)",
            data: data.feed_comparison.map(f => f.produced),
            backgroundColor: "#3b82f6",
            borderRadius: 4,
          },
          {
            label: "Consumed (Kg)",
            data: data.feed_comparison.map(f => f.consumed),
            backgroundColor: "#f59e0b",
            borderRadius: 4,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "top" } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: gridColor }, beginAtZero: true }
        }
      }
    });
  }

  // 6. Monthly Expenses by Category (Doughnut / Polar)
  const expCtx = document.getElementById("chartExpensesByCat");
  if (expCtx && data.expenses_by_cat) {
    chartInstances["expensesByCat"] = new Chart(expCtx, {
      type: "doughnut",
      data: {
        labels: data.expenses_by_cat.map(e => e.category),
        datasets: [{
          data: data.expenses_by_cat.map(e => e.total),
          backgroundColor: ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#6366f1"],
          borderColor: isDarkMode ? "#111a24" : "#ffffff",
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } }
      }
    });
  }

  // 7. Income vs Expenses (Bar)
  const incExpCtx = document.getElementById("chartIncomeVsExpense");
  if (incExpCtx && data.income_vs_expense) {
    chartInstances["incomeVsExpense"] = new Chart(incExpCtx, {
      type: "bar",
      data: {
        labels: data.income_vs_expense.map(m => m.month),
        datasets: [
          {
            label: "Total Income (₹)",
            data: data.income_vs_expense.map(m => m.income),
            backgroundColor: "#10b981",
            borderRadius: 4,
          },
          {
            label: "Total Expenses (₹)",
            data: data.income_vs_expense.map(m => m.expenses),
            backgroundColor: "#ef4444",
            borderRadius: 4,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "top" } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: gridColor }, beginAtZero: true }
        }
      }
    });
  }
}
