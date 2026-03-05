/* ==============================
   FeastOptimizer - Global JS
   ============================== */

// Theme switching
function changeTheme(themeName) {
    document.body.setAttribute('data-theme', themeName);
    localStorage.setItem('feast-theme', themeName);

    // Update active state on theme buttons
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === themeName);
    });

    // Persist to server (fire-and-forget)
    fetch('/settings/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: themeName })
    }).catch(() => {});
}

function loadSavedTheme() {
    const saved = localStorage.getItem('feast-theme');
    if (saved) {
        document.body.setAttribute('data-theme', saved);
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === saved);
        });
    }
}

// Mobile menu
function toggleMenu() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Active nav link
function setActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (path === href || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function(e) {
    const sidebar = document.getElementById('sidebar');
    const hamburger = document.querySelector('.hamburger');
    if (sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !hamburger.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});

// Auto-dismiss flash messages
function initFlashMessages() {
    document.querySelectorAll('.flash-message').forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transition = 'opacity 0.3s ease';
            setTimeout(() => msg.remove(), 300);
        }, 4000);
    });
}

// Init on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    loadSavedTheme();
    setActiveNav();
    initFlashMessages();
});
