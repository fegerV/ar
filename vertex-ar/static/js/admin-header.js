(function() {
    const AdminHeader = window.AdminHeader || {};
    const headerState = {
        refreshTimer: null,
    };

    AdminHeader.refreshNotifications = AdminHeader.refreshNotifications || (async () => []);
    window.AdminHeader = AdminHeader;

    function safeToast(message, type = 'info') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            const logger = type === 'error' ? console.error : console.log;
            logger(message);
        }
    }

    function applySavedTheme() {
        let savedTheme = 'dark';
        try {
            savedTheme = localStorage.getItem('admin-theme') || 'dark';
        } catch (error) {
            console.warn('Unable to load theme preference', error);
        }
        document.documentElement.setAttribute('data-theme', savedTheme);
        return savedTheme;
    }

    function initThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');
        if (!themeToggle) {
            return;
        }

        function updateLabel(theme) {
            themeToggle.textContent = theme === 'light' ? '🌙' : '☀️';
        }

        const currentTheme = document.documentElement.getAttribute('data-theme') || applySavedTheme();
        updateLabel(currentTheme);

        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', next);
            try {
                localStorage.setItem('admin-theme', next);
            } catch (error) {
                console.warn('Unable to save theme preference', error);
            }
            updateLabel(next);
        });
    }

    function formatDateTime(value) {
        if (!value) {
            return '';
        }
        try {
            return new Date(value).toLocaleString('ru-RU');
        } catch (error) {
            return value;
        }
    }

    function initNotificationsDropdown() {
        const toggle = document.getElementById('notificationToggle');
        const dropdown = document.getElementById('notificationDropdown');
        const badge = document.getElementById('notificationBadge');
        const list = document.getElementById('notificationList');
        const markAllBtn = document.getElementById('markNotificationsRead');

        if (!toggle || !dropdown || !badge || !list) {
            AdminHeader.refreshNotifications = async () => [];
            return;
        }

        function renderNotifications(notifications) {
            if (!Array.isArray(notifications) || notifications.length === 0) {
                list.innerHTML = '<p class="notification-empty">Новых уведомлений нет</p>';
                badge.classList.add('hidden');
                badge.textContent = '0';
                return;
            }

            badge.textContent = String(notifications.length);
            badge.classList.remove('hidden');
            list.innerHTML = '';

            notifications.forEach((notification) => {
                const item = document.createElement('div');
                item.className = 'notification-item';

                const title = document.createElement('div');
                title.className = 'notification-title';
                title.textContent = notification.title || 'Уведомление';

                const message = document.createElement('div');
                message.className = 'notification-message';
                message.textContent = notification.message || '';

                const time = document.createElement('div');
                time.className = 'notification-time';
                time.textContent = formatDateTime(notification.created_at);

                item.appendChild(title);
                item.appendChild(message);
                item.appendChild(time);
                list.appendChild(item);
            });
        }

        async function loadNotifications(limit = 10) {
            try {
                const response = await fetch(`/notifications?limit=${limit}`, {
                    credentials: 'include',
                });

                if (!response.ok) {
                    throw new Error(`Failed with status ${response.status}`);
                }

                const notifications = await response.json();
                renderNotifications(notifications);
                return notifications;
            } catch (error) {
                console.error('Failed to load notifications', error);
                renderNotifications([]);
                safeToast('Не удалось загрузить уведомления', 'error');
                return [];
            }
        }

        toggle.addEventListener('click', (event) => {
            event.stopPropagation();
            dropdown.classList.toggle('active');
            if (dropdown.classList.contains('active')) {
                loadNotifications();
            }
        });

        document.addEventListener('click', (event) => {
            if (!dropdown.contains(event.target) && !toggle.contains(event.target)) {
                dropdown.classList.remove('active');
            }
        });

        if (markAllBtn) {
            markAllBtn.addEventListener('click', async () => {
                try {
                    const response = await fetch('/notifications/mark-all-read', {
                        method: 'PUT',
                        credentials: 'include',
                    });
                    if (!response.ok) {
                        throw new Error(`Failed with status ${response.status}`);
                    }
                    safeToast('Все уведомления помечены как прочитанные', 'success');
                } catch (error) {
                    console.error('Failed to mark notifications as read', error);
                    safeToast('Не удалось очистить уведомления', 'error');
                } finally {
                    loadNotifications();
                }
            });
        }

        loadNotifications();
        if (headerState.refreshTimer) {
            clearInterval(headerState.refreshTimer);
        }
        headerState.refreshTimer = setInterval(loadNotifications, 60000);

        AdminHeader.refreshNotifications = () => loadNotifications();
    }

    applySavedTheme();

    document.addEventListener('DOMContentLoaded', () => {
        initThemeToggle();
        initNotificationsDropdown();
    });

    window.addEventListener('beforeunload', () => {
        if (headerState.refreshTimer) {
            clearInterval(headerState.refreshTimer);
        }
    });
})();
