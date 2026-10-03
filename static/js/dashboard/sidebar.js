// static/js/dashboard/sidebar.js
document.addEventListener("DOMContentLoaded", () => {
  const layout = document.getElementById("dashboardLayout");
  const toggleBtn = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");

  if (!layout || !toggleBtn) return;

  // Create overlay for mobile
  const overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  layout.appendChild(overlay);

  // Check LocalStorage for desktop state
  const isCollapsed = localStorage.getItem("dashboardSidebarCollapsed") === "true";
  
  if (isCollapsed && window.innerWidth >= 992) {
    layout.classList.add("collapsed");
  }

  // Toggle Function
  toggleBtn.addEventListener("click", () => {
    if (window.innerWidth >= 992) {
      layout.classList.toggle("collapsed");
      const collapsedNow = layout.classList.contains("collapsed");
      localStorage.setItem("dashboardSidebarCollapsed", collapsedNow);
    } else {
      layout.classList.add("mobile-open");
      document.body.classList.add("sidebar-open");
    }
  });

  // Close mobile drawer when clicking overlay
  overlay.addEventListener("click", () => {
    layout.classList.remove("mobile-open");
    document.body.classList.remove("sidebar-open");
  });

  // Close mobile drawer when clicking a menu item
  const menuLinks = sidebar.querySelectorAll(".sidebar-menu a");
  menuLinks.forEach(link => {
    link.addEventListener("click", () => {
      if (window.innerWidth < 992) {
        layout.classList.remove("mobile-open");
        document.body.classList.remove("sidebar-open");
      }
    });
  });

  // Handle resize edge cases
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 992) {
      layout.classList.remove("mobile-open");
      document.body.classList.remove("sidebar-open");
    }
  });
});
