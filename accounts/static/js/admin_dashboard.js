(() => {
  const sidebar = document.querySelector(".sidebar");
  const toggle = document.querySelector("[data-sidebar-toggle]");
  const navLinks = document.querySelectorAll("[data-section-target]");

  if (toggle && sidebar) {
    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", sidebar.classList.contains("is-open"));
    });
  }

  const setActiveSection = (targetId) => {
    document.querySelectorAll(".dashboard-section").forEach((section) => {
      section.classList.toggle("is-active", section.id === targetId);
    });
    navLinks.forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("data-section-target") === targetId);
    });
  };

  navLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const target = link.getAttribute("data-section-target");
      if (target) {
        setActiveSection(target);
      }
    });
  });

  document.querySelectorAll("[data-sort-table]").forEach((table) => {
    const headers = table.querySelectorAll("th[data-sort-key]");
    headers.forEach((header) => {
      header.addEventListener("click", () => {
        const key = header.getAttribute("data-sort-key");
        const rows = Array.from(table.querySelectorAll("tbody tr"));
        const sorted = rows.sort((a, b) => {
          const aVal = a.querySelector(`[data-cell='${key}']`)?.textContent.trim() || "";
          const bVal = b.querySelector(`[data-cell='${key}']`)?.textContent.trim() || "";
          return aVal.localeCompare(bVal, undefined, { numeric: true });
        });
        const body = table.querySelector("tbody");
        body.innerHTML = "";
        sorted.forEach((row) => body.appendChild(row));
      });
    });
  });
})();
