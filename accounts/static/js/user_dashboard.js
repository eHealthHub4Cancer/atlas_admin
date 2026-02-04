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
})();
