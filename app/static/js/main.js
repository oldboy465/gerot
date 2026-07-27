/* ==========================================================================
   TRANSUL GEROT v1 - TAILWIND & INTERACTIVITY SCRIPTS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alert notifications after 5 seconds
    const alerts = document.querySelectorAll('.flash-alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(function () {
                alert.remove();
            }, 500);
        }, 5000);
    });

    // Mobile sidebar toggle handler
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar-menu');

    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('-translate-x-full');
        });
    }

    // Modal open and close handlers
    window.openModal = function (modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }
    };

    window.closeModal = function (modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('flex');
            modal.classList.add('hidden');
        }
    };
});