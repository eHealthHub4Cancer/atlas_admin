(() => {
  const debounce = (callback, delay = 400) => {
    let timer = null;
    return (...args) => {
      if (timer) {
        window.clearTimeout(timer);
      }
      timer = window.setTimeout(() => {
        callback(...args);
      }, delay);
    };
  };

  const formatDate = (value) => {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const updateChips = (chipGroup, value) => {
    if (!chipGroup) return;
    chipGroup.querySelectorAll(".chip").forEach((chip) => {
      chip.classList.toggle("is-active", chip.getAttribute("data-filter-value") === value);
    });
  };

  const renderRows = (tableType, rows) => {
    if (tableType === "roles" || tableType === "permissions") {
      return rows
        .map(
          (row) => `
            <tr>
              <td>${row.name}</td>
              <td>${row.external_id ?? "-"}</td>
              <td>${row.description || "-"}</td>
            </tr>
          `
        )
        .join("");
    }

    if (tableType === "activity") {
      return rows
        .map(
          (row) => `
            <tr>
              <td>${row.summary}</td>
              <td>${formatDate(row.created_at)}</td>
              <td><span class="tag">${row.status}</span></td>
            </tr>
          `
        )
        .join("");
    }

    return rows
      .map((row) => `<tr><td colspan="3">${JSON.stringify(row)}</td></tr>`)
      .join("");
  };

  const renderPagination = (container, page, pageSize, count) => {
    const totalPages = Math.max(1, Math.ceil(count / pageSize));
    const currentPage = clamp(page, 1, totalPages);
    const maxButtons = 5;
    const startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    const endPage = Math.min(totalPages, startPage + maxButtons - 1);

    container.innerHTML = "";

    const prevButton = document.createElement("button");
    prevButton.type = "button";
    prevButton.className = "btn btn-ghost btn-sm";
    prevButton.textContent = "Previous";
    prevButton.disabled = currentPage === 1;
    prevButton.setAttribute("data-page", String(currentPage - 1));
    container.appendChild(prevButton);

    const pagesWrap = document.createElement("div");
    pagesWrap.className = "pagination__pages";

    for (let pageNum = startPage; pageNum <= endPage; pageNum += 1) {
      const pageButton = document.createElement("button");
      pageButton.type = "button";
      pageButton.className = `page-number${pageNum === currentPage ? " is-active" : ""}`;
      pageButton.textContent = String(pageNum);
      pageButton.setAttribute("data-page", String(pageNum));
      pagesWrap.appendChild(pageButton);
    }

    container.appendChild(pagesWrap);

    const nextButton = document.createElement("button");
    nextButton.type = "button";
    nextButton.className = "btn btn-ghost btn-sm";
    nextButton.textContent = "Next";
    nextButton.disabled = currentPage === totalPages;
    nextButton.setAttribute("data-page", String(currentPage + 1));
    container.appendChild(nextButton);
  };

  const updateUrlParams = (prefix, state) => {
    const url = new URL(window.location.href);
    const params = url.searchParams;
    const mapping = {
      search: `${prefix}_search`,
      filter: `${prefix}_filter`,
      page: `${prefix}_page`,
      page_size: `${prefix}_page_size`,
      ordering: `${prefix}_ordering`,
      status: `${prefix}_status`,
      start_date: `${prefix}_start`,
      end_date: `${prefix}_end`,
    };

    Object.entries(mapping).forEach(([key, param]) => {
      const value = state[key];
      if (value && value !== "all") {
        params.set(param, value);
      } else {
        params.delete(param);
      }
    });

    window.history.replaceState({}, "", url.toString());
  };

  const readUrlParams = (prefix, state) => {
    const params = new URLSearchParams(window.location.search);
    const mapping = {
      search: `${prefix}_search`,
      filter: `${prefix}_filter`,
      page: `${prefix}_page`,
      page_size: `${prefix}_page_size`,
      ordering: `${prefix}_ordering`,
      status: `${prefix}_status`,
      start_date: `${prefix}_start`,
      end_date: `${prefix}_end`,
    };

    Object.entries(mapping).forEach(([key, param]) => {
      const value = params.get(param);
      if (value) {
        state[key] = value;
      }
    });
  };

  const bindTable = (table) => {
    const api = table.getAttribute("data-table-api");
    if (!api) return;
    const prefix = table.getAttribute("data-table-prefix") || "table";
    const pageSizeDefault = parseInt(table.getAttribute("data-table-page-size") || "10", 10);
    const tableType = prefix;

    const state = {
      page: 1,
      page_size: pageSizeDefault,
      search: "",
      filter: "all",
      ordering: "",
      status: "all",
      start_date: "",
      end_date: "",
    };

    readUrlParams(prefix, state);

    const body = table.querySelector("[data-table-body]");
    const pagination = table.querySelector("[data-table-pagination]");
    const stateEl = table.querySelector("[data-table-state]");

    const searchInput = table.querySelector("[data-filter='search']");
    const filterSelect = table.querySelector("[data-filter='filter']");
    const statusSelect = table.querySelector("[data-filter='status']");
    const startDate = table.querySelector("[data-filter='start_date']");
    const endDate = table.querySelector("[data-filter='end_date']");
    const pageSizeSelect = table.querySelector("[data-filter='page_size']");
    const chipGroups = table.querySelectorAll("[data-filter-chips]");

    if (searchInput) searchInput.value = state.search || "";
    if (filterSelect) filterSelect.value = state.filter || "all";
    if (statusSelect) statusSelect.value = state.status || "all";
    if (startDate) startDate.value = state.start_date || "";
    if (endDate) endDate.value = state.end_date || "";
    if (pageSizeSelect) pageSizeSelect.value = String(state.page_size || pageSizeDefault);

    chipGroups.forEach((group) => {
      const filterName = group.getAttribute("data-filter-chips");
      updateChips(group, state[filterName] || "all");
    });

    let controller = null;

    const setLoading = () => {
      if (body) {
        body.innerHTML = `
          <tr class="table-skeleton">
            <td colspan="3">
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
            </td>
          </tr>
        `;
      }
      if (stateEl) {
        stateEl.textContent = "Loading data...";
        stateEl.classList.remove("is-error", "is-empty");
      }
    };

    const fetchData = () => {
      if (controller) {
        controller.abort();
      }
      controller = new AbortController();

      const params = new URLSearchParams();
      params.set("page", state.page);
      params.set("page_size", state.page_size);
      if (state.search) params.set("search", state.search);
      if (state.filter && state.filter !== "all") params.set("filter", state.filter);
      if (state.ordering) params.set("ordering", state.ordering);
      if (state.status && state.status !== "all") params.set("status", state.status);
      if (state.start_date) params.set("start_date", state.start_date);
      if (state.end_date) params.set("end_date", state.end_date);

      updateUrlParams(prefix, state);
      setLoading();

      fetch(`${api}?${params.toString()}`, { signal: controller.signal })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          const rows = data.results || [];
          if (body) {
            if (rows.length) {
              body.innerHTML = renderRows(tableType, rows);
            } else {
              body.innerHTML = `
                <tr>
                  <td colspan="3" class="muted">No results found.</td>
                </tr>
              `;
            }
          }
          if (stateEl) {
            if (!rows.length) {
              stateEl.textContent = "No results match your filters.";
              stateEl.classList.add("is-empty");
              stateEl.classList.remove("is-error");
            } else {
              stateEl.textContent = "";
              stateEl.classList.remove("is-empty", "is-error");
            }
          }
          if (pagination) {
            renderPagination(pagination, data.page, data.page_size, data.count);
          }
        })
        .catch((error) => {
          if (error.name === "AbortError") {
            return;
          }
          if (body) {
            body.innerHTML = `
              <tr>
                <td colspan="3" class="muted">Unable to load data. Please try again.</td>
              </tr>
            `;
          }
          if (stateEl) {
            stateEl.textContent = "Something went wrong while loading data.";
            stateEl.classList.add("is-error");
            stateEl.classList.remove("is-empty");
          }
        });
    };

    const debouncedFetch = debounce(() => {
      state.page = 1;
      fetchData();
    }, 450);

    if (searchInput) {
      searchInput.addEventListener("input", (event) => {
        state.search = event.target.value.trim();
        debouncedFetch();
      });
    }

    if (filterSelect) {
      filterSelect.addEventListener("change", (event) => {
        state.filter = event.target.value;
        state.page = 1;
        chipGroups.forEach((group) => updateChips(group, state.filter));
        fetchData();
      });
    }

    if (statusSelect) {
      statusSelect.addEventListener("change", (event) => {
        state.status = event.target.value;
        state.page = 1;
        chipGroups.forEach((group) => updateChips(group, state.status));
        fetchData();
      });
    }

    chipGroups.forEach((group) => {
      group.querySelectorAll(".chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          const filterName = group.getAttribute("data-filter-chips");
          const value = chip.getAttribute("data-filter-value") || "all";
          state[filterName] = value;
          if (filterName === "filter" && filterSelect) {
            filterSelect.value = value;
          }
          if (filterName === "status" && statusSelect) {
            statusSelect.value = value;
          }
          state.page = 1;
          updateChips(group, value);
          fetchData();
        });
      });
    });

    if (startDate) {
      startDate.addEventListener("change", (event) => {
        state.start_date = event.target.value;
        state.page = 1;
        fetchData();
      });
    }

    if (endDate) {
      endDate.addEventListener("change", (event) => {
        state.end_date = event.target.value;
        state.page = 1;
        fetchData();
      });
    }

    if (pageSizeSelect) {
      pageSizeSelect.addEventListener("change", (event) => {
        state.page_size = parseInt(event.target.value, 10);
        state.page = 1;
        fetchData();
      });
    }

    table.querySelectorAll("th[data-ordering]").forEach((header) => {
      header.addEventListener("click", () => {
        const key = header.getAttribute("data-ordering");
        if (!key) return;
        if (state.ordering === key) {
          state.ordering = `-${key}`;
        } else if (state.ordering === `-${key}`) {
          state.ordering = "";
        } else {
          state.ordering = key;
        }
        state.page = 1;
        fetchData();
      });
    });

    if (pagination) {
      pagination.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const page = target.getAttribute("data-page");
        if (!page) return;
        state.page = parseInt(page, 10);
        fetchData();
      });
    }

    fetchData();
  };

  document.querySelectorAll("[data-table-api]").forEach((table) => {
    bindTable(table);
  });
})();
