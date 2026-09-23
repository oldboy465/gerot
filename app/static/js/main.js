/* ==========================================================================
   TRANSUL GEROT v1 - SCRIPTS DE INTERATIVIDADE, HIGIENIZAÇÃO E MÁSCARAS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss de alertas flash após 5 segundos
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

    // 2. Toggle da Sidebar em dispositivos móveis
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar-menu');
    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('-translate-x-full');
        });
    }

    // 3. Autocompletar dinâmico do domínio corporativo @transultransporte.com.br
    const emailInputs = document.querySelectorAll('input[name="email"]');
    emailInputs.forEach(function (input) {
        input.addEventListener('blur', function () {
            let val = this.value.trim().toLowerCase();
            if (val.length > 0) {
                if (!val.includes('@')) {
                    this.value = val + '@transultransporte.com.br';
                } else {
                    let partes = val.split('@');
                    if (partes[0].length > 0) {
                        this.value = partes[0] + '@transultransporte.com.br';
                    }
                }
            }
        });
    });

    // 4. Sanitização e formatação flexível de número de Telefone / WhatsApp
    const phoneInputs = document.querySelectorAll('input[name="telefone_principal"], input[name="telefone"]');
    phoneInputs.forEach(function (input) {
        input.addEventListener('blur', function () {
            let digits = this.value.replace(/\D/g, '');
            if (digits.length === 11) {
                this.value = '(' + digits.substring(0, 2) + ') ' + digits.substring(2, 7) + '-' + digits.substring(7);
            } else if (digits.length === 10) {
                this.value = '(' + digits.substring(0, 2) + ') ' + digits.substring(2, 6) + '-' + digits.substring(6);
            }
        });
    });

    // 5. Handlers de Modais Genéricos
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