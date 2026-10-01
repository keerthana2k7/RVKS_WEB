// RVKS WEB - Utility Functions & Helpers

/**
 * Displays a toast notification on the screen with title, description, and auto-dismiss
 * @param {string|object} titleOrMessage - Main toast title or message
 * @param {'success'|'error'|'warning'|'info'} [type='success'] - Notification category
 * @param {string} [description=null] - Optional detailed description line
 * @param {number} [duration=null] - Optional custom duration in ms
 */
export function showToast(titleOrMessage, type = "success", description = null, duration = null) {
  // Ensure toast container exists
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    container.id = "toastContainer";
    container.setAttribute("aria-live", "polite");
    container.setAttribute("aria-atomic", "true");
    document.body.appendChild(container);
  }

  // Parse parameters
  let title = titleOrMessage;
  let desc = description;
  let toastType = type || "success";

  if (typeof titleOrMessage === "object" && titleOrMessage !== null) {
    title = titleOrMessage.title || titleOrMessage.message || "";
    desc = titleOrMessage.description || titleOrMessage.desc || null;
    toastType = titleOrMessage.type || "success";
    duration = titleOrMessage.duration || null;
  }

  // Determine Icon symbol
  let iconSymbol = "✓";
  if (toastType === "error") iconSymbol = "✕";
  else if (toastType === "warning") iconSymbol = "⚠";
  else if (toastType === "info") iconSymbol = "ℹ";

  // Create toast element
  const toast = document.createElement("div");
  toast.className = `toast ${toastType} toast-${toastType}`;
  toast.setAttribute("role", "alert");
  toast.innerHTML = `
    <div class="toast-icon">${iconSymbol}</div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${desc ? `<div class="toast-desc">${desc}</div>` : ""}
    </div>
    <button type="button" class="toast-close-btn" aria-label="Dismiss">&times;</button>
  `;

  // Bind manual close button
  const closeBtn = toast.querySelector(".toast-close-btn");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => dismissToast(toast));
  }

  container.appendChild(toast);

  // Auto Dismiss: 3s for success, 4.5s for error/warning (Sections 7)
  const dismissTime = duration || (toastType === "success" ? 3000 : 4500);
  const timeoutId = setTimeout(() => {
    dismissToast(toast);
  }, dismissTime);

  function dismissToast(el) {
    clearTimeout(timeoutId);
    el.style.opacity = "0";
    el.style.transform = "translateY(12px) scale(0.96)";
    setTimeout(() => {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 300);
  }
}

/**
 * Opens a modal dialog by ID
 * @param {string} modalId - ID of modal container
 */
export function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("open");
  }
}

/**
 * Closes a modal dialog by ID
 * @param {string} modalId - ID of modal container
 */
export function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("open");
  }
}

/**
 * Formats a Date string into DD-MM-YYYY (Asia/Kolkata localized standard)
 * @param {string} dateStr - Date string
 * @returns {string} Formatted date
 */
export function formatDate(dateStr) {
  if (!dateStr) return "-";
  try {
    const parts = dateStr.slice(0, 10).split("-");
    if (parts.length === 3) {
      return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  } catch {
    return dateStr;
  }
}

/**
 * Formats a DateTime string into DD-MM-YYYY HH:mm
 * @param {string} dtStr - DateTime string
 * @returns {string} Formatted datetime
 */
export function formatDateTime(dtStr) {
  if (!dtStr) return "-";
  try {
    const d = new Date(dtStr);
    if (isNaN(d.getTime())) return dtStr;
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, "0");
    const mins = String(d.getMinutes()).padStart(2, "0");
    return `${day}-${month}-${year} ${hours}:${mins}`;
  } catch {
    return dtStr;
  }
}

/**
 * Formats a number to localized INR Currency string (₹)
 * @param {number|string} amount
 * @returns {string}
 */
export function formatCurrency(amount) {
  return `₹${Number(amount || 0).toLocaleString("en-IN")}`;
}

/**
 * Formats a number with comma separators
 * @param {number|string} val
 * @returns {string}
 */
export function formatNumber(val) {
  return Number(val || 0).toLocaleString("en-IN");
}

// Expose on window for convenience and backward compatibility
window.showToast = showToast;
window.openModal = openModal;
window.closeModal = closeModal;
window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
window.formatCurrency = formatCurrency;
window.formatNumber = formatNumber;
