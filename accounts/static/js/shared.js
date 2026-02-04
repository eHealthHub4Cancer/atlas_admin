(() => {
  const root = document.documentElement;
  const storageKey = "atlas_theme";

  const getPreferredTheme = () => {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      return stored;
    }
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  };

  const applyTheme = (theme) => {
    root.setAttribute("data-theme", theme);
    root.style.colorScheme = theme;
  };

  const currentTheme = getPreferredTheme();
  applyTheme(currentTheme);

  window.requestAnimationFrame(() => {
    document.body.classList.add("is-ready");
  });

  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      localStorage.setItem(storageKey, nextTheme);
      applyTheme(nextTheme);
      button.setAttribute("aria-pressed", String(nextTheme === "light"));
    });
  });

  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.getAttribute("data-target");
      const input = document.getElementById(targetId);
      if (!input) {
        return;
      }
      const isPassword = input.getAttribute("type") === "password";
      input.setAttribute("type", isPassword ? "text" : "password");
      button.classList.toggle("is-active", isPassword);
      button.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
      const icon = button.querySelector("[data-password-icon]");
      if (icon) {
        icon.innerHTML = isPassword
          ? "<path d=\"M2.1 12c1.6-4.4 5.8-7.5 10.4-7.5 4.6 0 8.8 3.1 10.4 7.5-1.6 4.4-5.8 7.5-10.4 7.5-4.6 0-8.8-3.1-10.4-7.5z\" stroke=\"currentColor\" stroke-width=\"1.5\" fill=\"none\"/><circle cx=\"12.5\" cy=\"12\" r=\"3.2\" stroke=\"currentColor\" stroke-width=\"1.5\" fill=\"none\"/>"
          : "<path d=\"M4 4l17 17\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><path d=\"M9.7 9.7a3.2 3.2 0 0 0 4.5 4.5\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M2.1 12c1.1-3 3.5-5.4 6.5-6.7M22.9 12c-0.8 2.3-2.3 4.2-4.4 5.6\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" fill=\"none\"/>";
      }
    });
  });

  document.querySelectorAll("[data-modal-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.getAttribute("data-modal-open");
      const modal = document.getElementById(target);
      if (modal) {
        modal.classList.add("is-open");
      }
    });
  });

  document.querySelectorAll("[data-modal-close]").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = button.closest(".modal");
      if (modal) {
        modal.classList.remove("is-open");
      }
    });
  });

  const alerts = Array.from(document.querySelectorAll(".alert"));
  if (alerts.length) {
    let toastStack = document.querySelector(".toast-stack");
    if (!toastStack) {
      toastStack = document.createElement("div");
      toastStack.classList.add("toast-stack");
      document.body.appendChild(toastStack);
    }

    const dismissToast = (toast) => {
      if (toast.classList.contains("is-hiding")) {
        return;
      }
      toast.classList.add("is-hiding");
      toast.addEventListener(
        "animationend",
        () => {
          toast.remove();
        },
        { once: true }
      );
    };

    alerts.forEach((alert) => {
      alert.classList.add("toast");
      toastStack.appendChild(alert);

      let dismissTimer = null;
      const scheduleDismiss = (delay) => {
        if (dismissTimer) {
          window.clearTimeout(dismissTimer);
        }
        dismissTimer = window.setTimeout(() => dismissToast(alert), delay);
      };

      scheduleDismiss(4500);

      alert.addEventListener("mouseenter", () => {
        if (dismissTimer) {
          window.clearTimeout(dismissTimer);
          dismissTimer = null;
        }
      });

      alert.addEventListener("mouseleave", () => {
        scheduleDismiss(1000);
      });
    });
  }
})();
