/**
 * Admin Users Page JavaScript
 * User management functionality with state management
 */

// User management state
const UserManager = {
    state: {
        users: [],
        currentPage: 1,
        recordsPerPage: 25,
        selectedUsers: new Set(),
        searchTerm: '',
        roleFilter: 'all',
        statusFilter: 'all',
        sortBy: 'created_at',
        sortOrder: 'desc',
        isLoading: false
    },
    
    // State persistence
    saveState() {
        try {
            const stateToSave = {
                currentPage: this.state.currentPage,
                recordsPerPage: this.state.recordsPerPage,
                roleFilter: this.state.roleFilter,
                statusFilter: this.state.statusFilter,
                sortBy: this.state.sortBy,
                sortOrder: this.state.sortOrder
            };
            localStorage.setItem('admin-users-state', JSON.stringify(stateToSave));
        } catch (error) {
            console.warn('Failed to save users state:', error);
        }
    },
    
    loadState() {
        try {
            const savedState = localStorage.getItem('admin-users-state');
            if (savedState) {
                const parsedState = JSON.parse(savedState);
                this.state = { ...this.state, ...parsedState };
            }
        } catch (error) {
            console.warn('Failed to load users state:', error);
        }
    },
    
    setState(updates) {
        this.state = { ...this.state, ...updates };
        this.saveState();
    }
};

// Initialize users page
function initializeUsersPage() {
    UserManager.loadState();
    
    // Apply saved filters
    applyFilters();
    
    // Load initial data
    loadUsers();
    loadUserStats();
    
    // Initialize event listeners
    initializeEventListeners();
    
    addLog('Страница управления пользователями загружена', 'info');
}

// Event listeners
function initializeEventListeners() {
    // Search
    const searchInput = document.getElementById('userSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(e) {
            UserManager.setState({ 
                searchTerm: e.target.value.trim(),
                currentPage: 1 
            });
            loadUsers();
        }, 300));
    }
    
    // Filters
    const roleFilter = document.getElementById('roleFilter');
    if (roleFilter) {
        roleFilter.addEventListener('change', function(e) {
            UserManager.setState({ 
                roleFilter: e.target.value,
                currentPage: 1 
            });
            loadUsers();
        });
    }
    
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function(e) {
            UserManager.setState({ 
                statusFilter: e.target.value,
                currentPage: 1 
            });
            loadUsers();
        });
    }
    
    // Sort
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', function(e) {
            const [sortBy, sortOrder] = e.target.value.split('-');
            UserManager.setState({ 
                sortBy,
                sortOrder,
                currentPage: 1 
            });
            loadUsers();
        });
    }
    
    // User form
    const userForm = document.getElementById('userForm');
    if (userForm) {
        userForm.addEventListener('submit', handleUserSubmit);
    }
}

// Load users from server
async function loadUsers() {
    try {
        UserManager.setState({ isLoading: true });
        showLoading();
        
        const params = new URLSearchParams({
            page: UserManager.state.currentPage,
            limit: UserManager.state.recordsPerPage,
            search: UserManager.state.searchTerm,
            role: UserManager.state.roleFilter,
            status: UserManager.state.statusFilter,
            sort_by: UserManager.state.sortBy,
            sort_order: UserManager.state.sortOrder
        });
        
        const response = await fetch(`/users?${params}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            UserManager.setState({ 
                users: data.users || [],
                totalCount: data.total_count || 0
            });
            displayUsers();
            updatePagination();
        } else {
            throw new Error('Failed to load users');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Ошибка загрузки пользователей', 'error');
        addLog('Ошибка загрузки пользователей: ' + error.message, 'error');
    } finally {
        UserManager.setState({ isLoading: false });
        hideLoading();
    }
}

// Load user statistics
async function loadUserStats() {
    try {
        const response = await fetch('/users/stats', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateUserStats(data);
        }
    } catch (error) {
        console.error('Error loading user stats:', error);
        addLog('Ошибка загрузки статистики пользователей: ' + error.message, 'error');
    }
}

// Update user statistics display
function updateUserStats(stats) {
    const elements = {
        'totalUsers': stats.total_users || 0,
        'activeUsers': stats.active_users || 0,
        'adminUsers': stats.admin_users || 0,
        'newUsers': stats.new_users || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

// Display users in table
function displayUsers() {
    const tbody = document.querySelector('.users-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (UserManager.state.users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Пользователи не найдены</td></tr>';
        return;
    }
    
    UserManager.state.users.forEach(user => {
        const row = createUserRow(user);
        tbody.appendChild(row);
    });
}

// Create user row
function createUserRow(user) {
    const row = document.createElement('tr');
    
    row.innerHTML = `
        <td>
            <img src="${user.avatar || '/static/default-avatar.png'}" 
                 alt="${user.username}" 
                 class="user-avatar"
                 onerror="this.src='/static/default-avatar.png'">
        </td>
        <td>
            <strong>${user.username || ''}</strong>
            ${user.email ? `<br><small style="color: var(--secondary-color)">${user.email}</small>` : ''}
        </td>
        <td>
            <span class="role-badge ${user.role || 'user'}">
                ${getRoleText(user.role)}
            </span>
        </td>
        <td>
            <span class="status-badge ${user.status || 'active'}">
                ${getStatusText(user.status)}
            </span>
        </td>
        <td>${formatDate(user.last_login)}</td>
        <td>${formatDate(user.created_at)}</td>
        <td>
            <div class="user-actions">
                <button class="action-btn view-btn" onclick="viewUser('${user.id}')" title="Просмотр">👁️</button>
                <button class="action-btn edit-btn" onclick="editUser('${user.id}')" title="Редактировать">✏️</button>
                <button class="action-btn delete-btn" onclick="deleteUser('${user.id}')" title="Удалить">🗑️</button>
            </div>
        </td>
    `;
    
    return row;
}

// Handle user form submission
async function handleUserSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const submitBtn = e.target.querySelector('button[type="submit"]');
    
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Сохранение...';
    }
    
    try {
        const response = await fetch('/users', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast('Пользователь успешно создан', 'success');
            addLog(`Создан новый пользователь: ${result.user.username}`, 'success');
            
            e.target.reset();
            loadUsers();
            loadUserStats();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось создать пользователя'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при создании пользователя: ${error.message}`, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Создать пользователя';
        }
    }
}

// View user details
async function viewUser(userId) {
    try {
        showLoading();
        
        const response = await fetch(`/users/${userId}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const user = await response.json();
            showUserModal(user);
        } else {
            throw new Error('User not found');
        }
    } catch (error) {
        console.error('Error loading user:', error);
        showToast('Ошибка загрузки данных пользователя', 'error');
    } finally {
        hideLoading();
    }
}

// Show user details modal
function showUserModal(user) {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Детали пользователя</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <div class="user-details">
                    <div class="detail-row">
                        <span class="detail-label">ID:</span>
                        <span class="detail-value">${user.id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Имя пользователя:</span>
                        <span class="detail-value">${user.username}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Email:</span>
                        <span class="detail-value">${user.email || 'Не указан'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Роль:</span>
                        <span class="detail-value">
                            <span class="role-badge ${user.role}">${getRoleText(user.role)}</span>
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Статус:</span>
                        <span class="detail-value">
                            <span class="status-badge ${user.status}">${getStatusText(user.status)}</span>
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Последний вход:</span>
                        <span class="detail-value">${formatDate(user.last_login)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Создан:</span>
                        <span class="detail-value">${formatDate(user.created_at)}</span>
                    </div>
                </div>
                
                <div class="password-reset">
                    <h4>Сброс пароля</h4>
                    <button class="btn btn-secondary" onclick="resetUserPassword('${user.id}')">
                        🔄 Сбросить пароль
                    </button>
                </div>
                
                <div class="activity-log">
                    <h4>Последняя активность</h4>
                    <div id="userActivityLog">
                        <!-- Activity log will be populated here -->
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="modal-btn cancel" onclick="this.closest('.modal').remove()">Закрыть</button>
                <button class="modal-btn confirm" onclick="editUser('${user.id}')">Редактировать</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Event listeners
    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
    
    // Load activity log
    loadUserActivity(user.id);
}

// Load user activity
async function loadUserActivity(userId) {
    try {
        const response = await fetch(`/users/${userId}/activity`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const activities = await response.json();
            displayUserActivity(activities);
        }
    } catch (error) {
        console.error('Error loading user activity:', error);
    }
}

// Display user activity
function displayUserActivity(activities) {
    const container = document.getElementById('userActivityLog');
    if (!container) return;
    
    if (activities.length === 0) {
        container.innerHTML = '<div class="log-entry">Активность не найдена</div>';
        return;
    }
    
    container.innerHTML = activities.map(activity => `
        <div class="log-entry">
            <span class="log-time">${formatDate(activity.timestamp)}</span>
            <span class="log-action">${activity.action}</span>
        </div>
    `).join('');
}

// Reset user password
async function resetUserPassword(userId) {
    if (!confirm('Вы уверены, что хотите сбросить пароль этого пользователя?')) {
        return;
    }
    
    try {
        const response = await fetch(`/users/${userId}/reset-password`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast(`Пароль сброшен. Новый пароль: ${result.new_password}`, 'success');
            addLog(`Сброшен пароль пользователя: ${userId}`, 'success');
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось сбросить пароль'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при сбросе пароля: ${error.message}`, 'error');
    }
}

// Edit user
function editUser(userId) {
    // Close modal if open
    const modal = document.querySelector('.modal.active');
    if (modal) modal.remove();
    
    showToast(`Редактирование пользователя ${userId}`, 'info');
    addLog(`Начато редактирование пользователя: ${userId}`, 'info');
}

// Delete user
async function deleteUser(userId) {
    if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) {
        return;
    }
    
    try {
        const response = await fetch(`/users/${userId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            showToast('Пользователь удален', 'success');
            addLog(`Удален пользователь: ${userId}`, 'success');
            
            loadUsers();
            loadUserStats();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось удалить пользователя'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при удалении пользователя: ${error.message}`, 'error');
    }
}

// Update pagination
function updatePagination() {
    const { currentPage, recordsPerPage, totalCount } = UserManager.state;
    const totalPages = Math.ceil(totalCount / recordsPerPage);
    
    const pagination = document.querySelector('.pagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    // Previous button
    const prevBtn = createPaginationButton('←', currentPage - 1, currentPage === 1);
    pagination.appendChild(prevBtn);
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        const btn = createPaginationButton(i, i, i === currentPage);
        pagination.appendChild(btn);
    }
    
    // Next button
    const nextBtn = createPaginationButton('→', currentPage + 1, currentPage === totalPages);
    pagination.appendChild(nextBtn);
    
    // Info
    const info = document.createElement('div');
    info.style.marginLeft = '1rem';
    info.style.color = 'var(--secondary-color)';
    info.textContent = `Страница ${currentPage} из ${totalPages} (${totalCount} записей)`;
    pagination.appendChild(info);
}

// Create pagination button
function createPaginationButton(text, page, isDisabled) {
    const button = document.createElement('button');
    button.textContent = text;
    button.className = 'pagination-btn';
    button.disabled = isDisabled;
!    
    if (!isDisabled) {
        button.addEventListener('click', () => {
            UserManager.setState({ currentPage: page });
            loadUsers();
        });
    }
    
    return button;
}

// Apply saved filters
function applyFilters() {
    const roleFilter = document.getElementById('roleFilter');
    const statusFilter = document.getElementById('statusFilter');
    const sortSelect = document.getElementById('sortSelect');
    
    if (roleFilter) roleFilter.value = UserManager.state.roleFilter;
    if (statusFilter) statusFilter.value = UserManager.state.statusFilter;
    if (sortSelect) sortSelect.value = `${UserManager.state.sortBy}-${UserManager.state.sortOrder}`;
}

// Utility functions
function getRoleText(role) {
    const roleMap = {
        'admin': 'Администратор',
        'moderator': 'Модератор',
        'user': 'Пользователь'
    };
    return roleMap[role] || role;
}

function getStatusText(status) {
    const statusMap = {
        'active': 'Активен',
        'inactive': 'Неактивен',
        'suspended': 'Приостановлен'
    };
    return statusMap[status] || status;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('ru-RU');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeUsersPage();
    
    // Performance monitoring
    if (window.performance) {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log(`Users page load time: ${loadTime}ms`);
        addLog(`Страница пользователей загружена за ${loadTime}ms`, 'info');
    }
});