/**
 * Atlas Config - Main JavaScript
 * Modern Bootstrap 5 Admin Dashboard
 */

(function() {
    'use strict';

    // ==========================================================================
    // DOM Ready
    // ==========================================================================
    document.addEventListener('DOMContentLoaded', function() {
        initDataTables();
        initConfirmModals();
        initTooltips();
        initAlertDismiss();
    });

    // ==========================================================================
    // DataTables Initialization
    // ==========================================================================
    function initDataTables() {
        const tables = document.querySelectorAll('.data-table');

        tables.forEach(function(table) {
            if ($.fn.DataTable.isDataTable(table)) {
                return;
            }

            $(table).DataTable({
                responsive: true,
                pageLength: 10,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search...",
                    lengthMenu: "Show _MENU_ entries",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                    infoEmpty: "No entries available",
                    infoFiltered: "(filtered from _MAX_ total entries)",
                    paginate: {
                        first: '<i class="bi bi-chevron-double-left"></i>',
                        last: '<i class="bi bi-chevron-double-right"></i>',
                        previous: '<i class="bi bi-chevron-left"></i>',
                        next: '<i class="bi bi-chevron-right"></i>'
                    },
                    emptyTable: "No data available"
                },
                dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                     '<"row"<"col-sm-12"tr>>' +
                     '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
                order: [[0, 'asc']],
                columnDefs: [
                    {
                        targets: 'no-sort',
                        orderable: false
                    }
                ]
            });
        });
    }

    // ==========================================================================
    // Confirmation Modals
    // ==========================================================================
    function initConfirmModals() {
        const confirmModal = document.getElementById('confirmModal');
        if (!confirmModal) return;

        const modal = new bootstrap.Modal(confirmModal);
        const modalTitle = confirmModal.querySelector('.modal-title');
        const modalBody = confirmModal.querySelector('.modal-body');
        const modalAction = confirmModal.querySelector('#confirmModalAction');

        let pendingForm = null;

        // Handle forms with data-confirm attribute
        document.addEventListener('submit', function(e) {
            const form = e.target;
            const confirmMessage = form.dataset.confirm;

            if (confirmMessage && !form.dataset.confirmed) {
                e.preventDefault();
                pendingForm = form;

                // Update modal content
                modalTitle.textContent = form.dataset.confirmTitle || 'Confirm Action';
                modalBody.innerHTML = confirmMessage;

                // Update button style
                const btnClass = form.dataset.confirmBtnClass || 'btn-primary';
                modalAction.className = 'btn ' + btnClass;
                modalAction.textContent = form.dataset.confirmBtn || 'Confirm';

                modal.show();
            }
        });

        // Handle confirm button click
        modalAction.addEventListener('click', function() {
            if (pendingForm) {
                pendingForm.dataset.confirmed = 'true';
                pendingForm.submit();
            }
            modal.hide();
        });

        // Reset when modal is hidden
        confirmModal.addEventListener('hidden.bs.modal', function() {
            pendingForm = null;
        });
    }

    // ==========================================================================
    // Bootstrap Tooltips
    // ==========================================================================
    function initTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(function(tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // ==========================================================================
    // Auto-dismiss Alerts
    // ==========================================================================
    function initAlertDismiss() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');

        alerts.forEach(function(alert) {
            // Auto-dismiss success alerts after 5 seconds
            if (alert.classList.contains('alert-success')) {
                setTimeout(function() {
                    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                    bsAlert.close();
                }, 5000);
            }
        });
    }

    // ==========================================================================
    // HTMX Events
    // ==========================================================================
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        // Re-initialize components after HTMX swap
        initDataTables();
        initTooltips();
    });

    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        // Add loading state
        const target = evt.detail.elt;
        if (target.tagName === 'BUTTON') {
            target.disabled = true;
            const originalText = target.innerHTML;
            target.dataset.originalText = originalText;
            target.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Loading...';
        }
    });

    document.body.addEventListener('htmx:afterRequest', function(evt) {
        // Remove loading state
        const target = evt.detail.elt;
        if (target.tagName === 'BUTTON' && target.dataset.originalText) {
            target.disabled = false;
            target.innerHTML = target.dataset.originalText;
            delete target.dataset.originalText;
        }
    });

    // ==========================================================================
    // Utility Functions
    // ==========================================================================
    window.AtlasConfig = {
        // Show toast notification
        showToast: function(message, type) {
            type = type || 'info';
            const toastContainer = document.getElementById('toastContainer') ||
                createToastContainer();

            const toastEl = document.createElement('div');
            toastEl.className = 'toast align-items-center text-white bg-' + type + ' border-0';
            toastEl.setAttribute('role', 'alert');
            toastEl.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto"
                            data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;

            toastContainer.appendChild(toastEl);
            const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
            toast.show();

            toastEl.addEventListener('hidden.bs.toast', function() {
                toastEl.remove();
            });
        },

        // Confirm dialog
        confirm: function(message, callback, options) {
            options = options || {};
            const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
            const modalTitle = document.querySelector('#confirmModal .modal-title');
            const modalBody = document.querySelector('#confirmModal .modal-body');
            const modalAction = document.querySelector('#confirmModalAction');

            modalTitle.textContent = options.title || 'Confirm Action';
            modalBody.innerHTML = message;
            modalAction.className = 'btn ' + (options.btnClass || 'btn-primary');
            modalAction.textContent = options.btnText || 'Confirm';

            const handler = function() {
                callback();
                modal.hide();
                modalAction.removeEventListener('click', handler);
            };

            modalAction.addEventListener('click', handler);
            modal.show();
        }
    };

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1100';
        document.body.appendChild(container);
        return container;
    }

})();
